from tools.brief import inside_quotes, quoted_spans, sentences


def test_quoted_spans_are_detected():
    text = 'The Court said x. The trial court reasoned: “this is quoted” and then continued.'
    spans = quoted_spans(text)
    assert len(spans) == 1


def test_a_position_inside_a_quote_is_flagged():
    text = 'Court speaks. “Someone else speaks here”. Court again.'
    spans = quoted_spans(text)
    quoted_pos = text.index("Someone else")
    court_pos = text.index("Court again")
    assert inside_quotes(quoted_pos, spans)
    assert not inside_quotes(court_pos, spans)


def test_text_with_no_quotes_has_no_spans():
    assert quoted_spans("Nothing is quoted here at all.") == []


def test_sentences_carry_their_offsets():
    text = "First sentence. Second sentence. Third sentence."
    out = sentences(text)
    assert len(out) == 3
    assert out[1][1].startswith("Second")
    assert text[out[1][0]:].startswith("Second")


def test_unclosed_quote_does_not_swallow_the_document():
    text = 'Court speaks. “An unclosed quote runs on and on with no terminator'
    assert quoted_spans(text) == []
