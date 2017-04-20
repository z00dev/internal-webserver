#!/usr/bin/env python

"""Send blast data from Sailthru to bigquery

This script exports the campaign and blasts data from Sailthru to bigquery.
This is set-up to run daily in the aws-config repo using a cron job that will
fetch the campaigns table from forever (assume January 1, 2010) to now. Also,
it gets the list of blast IDs of the blasts that were fired in the past 7 days
and generates tables for each of those blasts. The tables are generated in
bigquery in the 'sailthru_blasts' dataset. The overall summary of all
campaigns is the 'campaigns' table the the individual blasts' tables are called
'blast_<blast iD>'.

To run this script, use the following (example):
Get data for individual blast:
    python gae_dashboard/sailthru_to_bigquery.py blast --blast_id 8260012
Get the overall campaign data:
    python gae_dashboard/sailthru_to_bigquery.py campaigns --status 'sent'
    --start_date 'January 1 2017' --end_date 'January 13 2017'
To directly run the script that runs on cron use:
    ./sailthru_to_bigquery.py export

If you want verbose to be true, you can select that as well.

Since the campaign data is not in the same format at all times,
use the below scripts to get the unique keys at different levels
from the json file of the data:
To get the top level: `cat ~/Downloads/file.json | while read -r line;
                    do echo "$line" | jq -r 'keys | .[]'; done | sort -u`
To get the 3rd level (below 'stats' and 'total'):
                `cat ~/Downloads/file.json | while read -r line;
                do echo "$line" | jq -r '.stats.total | keys | .[]';
                done | sort -u`

TODO(Ragini): Create a script to get the schema of the table that'll get
created in bigquery. There might be a possible problem in the future due to
the fact that the schema of data generated by sailthru is not always the same.
"""

import argparse
import contextlib
import datetime
import json
import os
import tempfile
import time
import shutil
import urllib

from sailthru import sailthru_client
import sailthru_secrets

import bq_util


def _get_client():
    """Retrieve the Sailthru API Client.

    Arguments:
        timeout: How many seconds the client should wait for an API
            call to return before aborting the request.
    """
    return sailthru_client.SailthruClient(sailthru_secrets.sailthru_key,
                                          sailthru_secrets.sailthru_secret)


class SailthruAPIException(Exception):
    """Exception for logging problems connecting to the Sailthru API."""
    def __init__(self, response):
        self.response = response
        super(SailthruAPIException, self).__init__(self.log_message())

    def log_message(self):
        stapi_error = self.response.get_error()
        return u"Sailthru API returned {}, error code {}: {}".format(
            self.response.get_status_code(),
            stapi_error.get_error_code(),
            stapi_error.get_message())


def _post(arg, **kwargs):
    if kwargs.get('verbose'):
        print "Calling sailthru's blast_query for blast_id = %s" % kwargs.get(
            'blast_id')
    client = _get_client()
    response = client.api_post(arg, kwargs)
    if not response.is_ok():
        raise SailthruAPIException(response)
    return response


def _get(arg, **kwargs):
    client = _get_client()
    response = client.api_get(arg, kwargs)
    if not response.is_ok():
        raise SailthruAPIException(response)
    return response


def _send_blast_details_to_bq(blast_id, temp_dir, verbose):
    """Export blast data to BigQuery.

    Arguments:
      blast_id: ID of the blast to fetch data for.
      temp_dir: A directory which contains temporary files.
      verbose: True if you want to show debug messages, else False.
    """
    response_1 = _post('job', job="blast_query", blast_id=blast_id,
                       verbose=verbose)

    job_id = response_1.get_body().get('job_id')

    if job_id is None:
        print "job_id returned from Sailthru's job=blast_query is None"
        return

    if verbose:
        print "Calling sailthru's job for job_id = %s" % job_id
    response_2 = _get('job', job_id=job_id)

    while response_2.get_body().get('status') != "completed":
        if verbose:
            print "Waiting for sailthru's job with job_id=%s" % job_id
            print "Retrying in 5 seconds..."
        time.sleep(5)
        response_2 = _get('job', job_id=job_id)
        if response_2.get_body().get('status') == "expired":
            raise SailthruAPIException(response_2)

    filename_url = response_2.get_body().get('export_url')

    if verbose:
        print "Creating a csv file from the sailthru data"

    file_name = "blast_export.csv"

    with open(os.path.join(temp_dir, file_name), "wb") as f:
        with contextlib.closing(urllib.urlopen(filename_url)) as csvdata:
            first_line = next(csvdata)
            f.write("blast_id,%s" % first_line)
            for line in csvdata:
                f.write("%s,%s" % (blast_id, line))

    table_name = "sailthru_blasts.blast_%s" % str(blast_id)

    # (TODO: Update schema to port dates in TIMESTAMP format in bq)

    if verbose:
        print "Write csv file to bigquery"
    bq_util.call_bq(['load', '--source_format=CSV', '--skip_leading_rows=1',
                     '--replace', table_name,
                     os.path.join(temp_dir, file_name),
                     os.path.join(
                         os.path.dirname(__file__),
                         'sailthru_blast_export_schema.json')
                     ],
                    project='khanacademy.org:deductive-jet-827',
                    return_output=False)


def _send_campaign_report(status, start_date, end_date, temp_dir, verbose):
    """Export data about all campaigns in a date range to Bigquery.
    This selects campaigns that started between start_date and end_date
    inclusive.

    Arguments:
      status: Export only the details of campaigns with this status.
              Options are 'sent', 'sending', 'scheduled' and 'draft'.
      start_date: Start date of blasts (format example: 'January 1 2017')
      end_date: End date of blasts (format example: 'January 1 2017')
      temp_dir: A directory which contains temporary files.
      verbose: True if you want to show debug messages, else False.

    Returns:
      Returns a python set of the blast IDs for the blasts that were
      started within 7 days before end_date inclusive both the end_date
      and seven days before end_date. The returned set has nothing to
      do with the start-date.
    """
    recent_blast_ids = set()
    response = _get('blast', status=status, start_date=start_date,
                    end_date=end_date)

    blasts_info_json = response.get_body().get('blasts')
    all_blasts_length = len(blasts_info_json)

    file_name = 'campaigns_export.json'

    with open(os.path.join(temp_dir, file_name), "wb"
              ) as json_file:
        for i in range(all_blasts_length):
            # Get the date a blast was started.
            date = datetime.datetime.strptime(
                blasts_info_json[i]['start_time'],
                '%a, %d %b %Y %H:%M:%S -%f')
            # Store a list of all blast IDs that started in the last 7 days of
            # end_date.
            if date >= datetime.datetime.strptime(
                    end_date, '%B %d %Y') - datetime.timedelta(days=7):
                recent_blast_ids.add(blasts_info_json[i]['blast_id'])
            json.dump(blasts_info_json[i], json_file)
            if i != len(blasts_info_json) - 1:
                json_file.write("\n")

    table_name = "sailthru_blasts.campaigns"

    if verbose:
        print ("Writing json file with %s lines to " % all_blasts_length +
               "bigquery table %s" % table_name)
    bq_util.call_bq(['load', '--source_format=NEWLINE_DELIMITED_JSON',
                     table_name,
                     os.path.join(temp_dir, file_name),
                     os.path.join(
                         os.path.dirname(__file__),
                         'sailthru_campaign_export_schema.json')
                     ],
                    project='khanacademy.org:deductive-jet-827',
                    return_output=False)

    return recent_blast_ids


if __name__ == "__main__":
    # Create a temp directory to hold temporary files
    temp_dir = tempfile.mkdtemp("temp_data_dir")

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="Show more information")

    subparsers = parser.add_subparsers(dest='subparser_name',
                                       help='sub-command help')
    parser_blast = subparsers.add_parser(
        'blast',
        help='export blast data to BigQuery')
    parser_blast.add_argument('--blast_id', required=True,
                              help='Blast to fetch data for')

    parser_campaign = subparsers.add_parser(
        'campaigns',
        help='export campaigns to BigQuery')
    parser_campaign.add_argument(
        '--status', required=True,
        choices=('sent', 'sending', 'scheduled', 'draft'),
        help="Export only campaigns with this status")
    parser_campaign.add_argument(
        '--start_date', required=True,
        help="Start date of blasts (format: 'January 1 2017')")
    parser_campaign.add_argument(
        '--end_date', required=True,
        help="End date of blasts (format: 'January 1 2017')")

    parser_export = subparsers.add_parser('export',
                                          help='export all as one script')

    args = parser.parse_args()

    # Log the path of temp directory for debugging
    print "temp_dir is %s" % temp_dir

    if args.subparser_name == 'blast':
        _send_blast_details_to_bq(args.blast_id, temp_dir, args.verbose)
    elif args.subparser_name == 'campaigns':
        _send_campaign_report(args.status, args.start_date, args.end_date,
                              temp_dir, args.verbose)
    else:
        # Call the script directly to generate the all campaigns table and
        # tables for blasts fired in the past 7 days.
        # TODO: If fetching the campaigns table from 2010 until now becomes
        # too expensive, get the old data from the previous campaigns table.
        recent_blasts = _send_campaign_report(
            "sent", "January 1 2010",
            "{:%B %d %Y}".format(datetime.date.today()),
            temp_dir, args.verbose)
        for id in recent_blasts:
            _send_blast_details_to_bq(id, temp_dir, args.verbose)

    shutil.rmtree(temp_dir)

