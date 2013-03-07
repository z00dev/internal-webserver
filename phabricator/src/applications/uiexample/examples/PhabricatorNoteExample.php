<?php

final class PhabricatorNoteExample extends PhabricatorUIExample {

  public function getName() {
    return "Notes";
  }

  public function getDescription() {
    return 'Show little scrollable boxes of text.';
  }

  public function renderExample() {
    $short_note = id(new AphrontNoteView())
      ->setTitle('Short note')
      ->appendChild('This is a short note');

    $longer_note = id(new AphrontNoteView())
      ->setTitle('Longer note')
      ->appendChild($this->buildParagraphs(2));

    $wide_url = 'protocol://www.'.str_repeat('x', 100).'.com/';

    $oversize_note = id(new AphrontNoteView())
      ->setTitle('Oversize note')
      ->appendChild(
          $this->buildParagraphs(2).
          $wide_url."\n\n".
          $this->buildParagraphs(5));

    $out = array();

    $out[] = id(new AphrontPanelView())
      ->setHeader('Unbounded Oversize Note')
      ->setCaption(
          'The rest of these examples are contrained by a table, but this one '.
          'is left free (it still constrains its max height though).')
      ->appendChild($oversize_note);

    $out[] = id(new AphrontPanelView())
      ->setHeader("Short notes")
      ->setCaption(
          'Two notes of equal size, spacing out an 80% wide table.')
      ->appendChild(
          $this->renderTable(
            array(array($short_note, $short_note))));

    $out[] = id(new AphrontPanelView())
      ->setHeader("Mixed notes")
      ->setCaption(
          'Two rows of notes with unequal height, spacing out their '.
          'rows vertically.')
      ->appendChild(
          $this->renderTable(
            array(
              array($longer_note, $short_note),
              array($short_note, $short_note)
            )));

    $out[] = id(new AphrontPanelView())
      ->setHeader("Oversize notes")
      ->setCaption(
          'Two rows each with a very large note, '.
          'showing scrolling behavior.')
      ->appendChild(
          $this->renderTable(
            array(
              array($oversize_note, $short_note),
              array($short_note, $oversize_note)
            )));

    return $out;
  }

  private function renderTable($rows) {
    static $td_style = '
      width: 50%;
      max-width: 1em;
    ';

    $trs = array();
    foreach ($rows as $index => $row) {
      $count = $index + 1;
      list($left, $right) = $row;
      $trs[] = phutil_tag(
        'tr',
        array(),
        array(
          phutil_tag(
            'th',
            array(),
            "Row {$count}"),
          phutil_tag('td')));

      $trs[] = phutil_tag(
        'tr',
        array(),
        array(
          phutil_tag(
            'td',
            array(
              'style' => $td_style,
            ),
            $left->render()),
          phutil_tag(
            'td',
            array(
              'style' => $td_style,
            ),
            $right->render())));
    }

    return phutil_tag(
      'table',
      array(
        'style' => 'width: 80%;'
      ),
      $trs);
  }

  private function buildParagraphs($num_paragraphs) {
    $body = '';
    for ($pp = 0; $pp < $num_paragraphs; $pp++) {
      $scale = 50 * ($pp / 2);
      $num_words = 30 + self::getRandom(0, $scale);
      for ($ii = 0; $ii < $num_words; $ii++) {
        $word = str_repeat('x', self::getRandom(3, 8));
        $body .= $word.' ';
      }
      $body .= "\n\n";
    }
    return $body;
  }

  private static function getRandom($lower, $upper) {
    // The ZX Spectrum's PRNG!
    static $nn = 65537;
    static $gg = 75;
    static $ii = 1;
    $ii = ($ii * $gg) % $nn;
    if ($lower == $upper) {
      return $lower;
    } else {
      return $lower + ($ii % ($upper - $lower));
    }
  }

}
