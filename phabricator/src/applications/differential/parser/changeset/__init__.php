<?php
/**
 * This file is automatically generated. Lint this module to rebuild it.
 * @generated
 */



phutil_require_module('arcanist', 'difference');

phutil_require_module('phabricator', 'aphront/writeguard');
phutil_require_module('phabricator', 'applications/differential/constants/changetype');
phutil_require_module('phabricator', 'applications/differential/storage/changeset');
phutil_require_module('phabricator', 'applications/differential/view/inlinecomment');
phutil_require_module('phabricator', 'applications/files/storage/file');
phutil_require_module('phabricator', 'applications/markup/syntax');
phutil_require_module('phabricator', 'infrastructure/diff/engine');
phutil_require_module('phabricator', 'infrastructure/env');
phutil_require_module('phabricator', 'infrastructure/events/constant/type');
phutil_require_module('phabricator', 'infrastructure/events/event');
phutil_require_module('phabricator', 'infrastructure/javelin/markup');
phutil_require_module('phabricator', 'storage/queryfx');

phutil_require_module('phutil', 'error');
phutil_require_module('phutil', 'events/engine');
phutil_require_module('phutil', 'future');
phutil_require_module('phutil', 'markup');
phutil_require_module('phutil', 'markup/syntax/highlighter/default');
phutil_require_module('phutil', 'utils');


phutil_require_source('DifferentialChangesetParser.php');