"""Text repair shared by every parser.

Both sources serve UTF-8 that has already been decoded once as Latin-1, so
curly quotes arrive as mojibake: a left double quote becomes three characters.
Left unrepaired it shows up in the app as garbage and, worse, makes it
impossible to tell where a decision is quoting somebody else.
"""

# The tell-tale sequences produced by decoding UTF-8 as Latin-1.
MOJIBAKE_MARKERS = ("â\x80\x9c", "â\x80\x9d", "â\x80\x99", "â\x80\x98", "â\x80\x93")


def repair_mojibake(text: str) -> str:
    """Undo one round of UTF-8-decoded-as-Latin-1, when that is what happened.

    Returns the text unchanged if it is not mojibake, so this is safe to run
    over anything.
    """
    if not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Mixed encodings: repair what we can, leave the rest intact.
        return text.encode("latin-1", "ignore").decode("utf-8", "ignore") or text
