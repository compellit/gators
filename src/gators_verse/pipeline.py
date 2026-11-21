"""The whole analysis, from text: what the gators-verse command runs.

:func:`analyze` takes poems as plain text or as a table, normalizes the
spelling and scans the lines with gama-verse (when installed), transcribes
them with trasgo, and calls :func:`~gators_verse.annotation.annotate`.
"""

import importlib.util
import warnings

import pandas as pd

from .annotation import annotate
from .transcription import transcribe


def read_poem_text(text):
    """Turn a plain-text poem into a table: one row per verse.

    Blank lines separate stanzas.
    """
    rows = []
    stanza_n = 1
    for line in text.splitlines():
        if line.strip():
            rows.append({"poem_id": 1, "stanza_n": stanza_n, "text": line.strip()})
        elif rows and rows[-1]["stanza_n"] == stanza_n:
            stanza_n += 1
    return pd.DataFrame(rows, columns=["poem_id", "stanza_n", "text"])


def gama_available():
    return importlib.util.find_spec("gama_verse") is not None


def scansion_stresses(result):
    """Stresses taken from GAMA's scansion of one line.

    The stresses of the line's regular pattern, without extra-rhythmic
    stresses, as in the GAMA web app; GAMA has no regular pattern for lines
    over 11 syllables ("-"), and those get all the stresses GAMA detects.
    They are only used for the experimental verse types (verse.py), which
    require no stress outside the type's pattern; rhyme takes the stress from
    trasgo.
    """
    if result["regular_pattern"] != "-":
        return result["regular_pattern"]
    return result["stressed_syllables"]


def add_gama_columns(df, poem_column, text_column, syllable_column, stress_column, need_meter):
    """Normalize the spelling (and scan, if meter is needed) with gama-verse, poem by poem."""
    import gama_verse

    normalized = pd.Series(index=df.index, dtype=object)
    syllables = pd.Series(index=df.index, dtype=object)
    stresses = pd.Series(index=df.index, dtype=object)
    for _, poem in df.groupby(poem_column, sort=False):
        lines = [str(text) for text in poem[text_column]]
        if need_meter:
            results = gama_verse.scan("\n".join(lines))
            normalized_lines = [result["preprocessing"] for result in results]
            syllables[poem.index] = [result["metrical_syllables"] for result in results]
            stresses[poem.index] = [scansion_stresses(result) for result in results]
        else:
            normalized_lines = gama_verse.preprocess("\n".join(lines)).splitlines()
        if len(normalized_lines) != len(lines):
            raise RuntimeError("gama-verse returned a different number of lines")
        normalized[poem.index] = normalized_lines
    df["normalized_text"] = normalized
    if need_meter:
        df[syllable_column] = syllables
        df[stress_column] = stresses


def analyze(
    poems,
    *,
    use_gama=True,
    poem_column="poem_id",
    stanza_column="stanza_n",
    text_column="text",
    syllable_column="metrical_syllables",
    stress_column="stressed_syllables",
):
    """Annotate rhyme, verse, stanza and poem types, starting from the text.

    ``poems`` is a plain-text poem (one verse per line, a blank line between
    stanzas) or a DataFrame with one row per verse, with poem, stanza and text
    columns and, optionally, a syllable column and a stress column. The
    stresses are only used for the experimental verse types, which are not
    computed without them. Rows without text are dropped.

    With gama-verse installed (and ``use_gama``), the spelling is normalized
    and, if the input has no syllable column, the lines are scanned, which
    gives both syllables and stresses. The output adds
    ``normalized_text`` (with gama-verse) and ``transcription`` to the input
    columns, plus those of :func:`~gators_verse.annotation.annotate`, which
    gives the return value: ``(results, stanza_scores, poem_scores)``.
    """
    df = read_poem_text(poems) if isinstance(poems, str) else poems.copy()
    for column in (poem_column, stanza_column, text_column):
        if column not in df.columns:
            raise ValueError(f"column {column!r} not found in the input; available: {list(df.columns)}")
    df = df.dropna(subset=[text_column]).reset_index(drop=True)
    has_meter = syllable_column in df.columns

    normalized_lines = None
    if use_gama and gama_available():
        add_gama_columns(df, poem_column, text_column, syllable_column, stress_column, need_meter=not has_meter)
        normalized_lines = df["normalized_text"].tolist()
    elif not has_meter:
        warnings.warn(
            "no syllable column and gama-verse not used; stanza and poem types "
            "will be unreliable. Install gators-verse[gama] to get them."
        )
    df["transcription"] = transcribe(df[text_column].astype(str).tolist(), normalized_lines)

    return annotate(
        df,
        poem_column=poem_column,
        stanza_column=stanza_column,
        text_column=text_column,
        syllable_column=syllable_column,
        stress_column=stress_column,
    )
