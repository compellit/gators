"""Rhyme, stanza-type and poem-type annotation of a table of verses."""

import json

import pandas as pd

from .patterns import load_patterns
from .poem import annotate_poem_type, detect_retrouso, normalize_refrain_text
from .rhyme import assign_rhymes, rhyme_ending
from .stanza import annotate_stanza_types
from .verse import classify_verse_type, enforce_short_gaita_pairs, parse_rhythm_value, parse_syllable_value

# Columns annotate() adds, and the poem_data key each one comes from.
OUTPUT_COLUMNS = {
    "rhyme": "letter",
    "rhyme_ending": "rhyme_tail",
    "rhyme_vowels": "vowels",
    "refrain": "retrouso",
    "verse_type": "verse_type",
    "stanza_rhyme_pattern": "observed_pattern",
    "stanza_expected_pattern": "expected_pattern",
    "stanza_type": "stanza_type",
    "stanza_type_probability": "stanza_type_probability",
    "stanza_subtype": "stanza_subtype",
    "stanza_subtype_probability": "stanza_subtype_probability",
    "poem_type": "poem_type",
    "poem_type_probability": "poem_type_probability",
    "poem_subtype": "poem_subtype",
    "poem_subtype_probability": "poem_subtype_probability",
}
# Rhyme letters are uppercase for lines of arte maior (9 syllables or more),
# as is usual in metrics and in the GAMA interface (which uppercases lines
# whose last stress falls on syllable 8 or later: the same lines, since the
# last stress falls on the second-to-last syllable).
ARTE_MAIOR_MIN_SYLLABLES = 9


def clean_output_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def make_poem_data(poem, stanza_column, text_column, transcription_column, syllable_column, stress_column):
    """Build poem_data (see patterns.py) for one poem's rows.

    A stanza is a run of consecutive rows with the same stanza number; stanzas
    are numbered 1, 2... in reading order.
    """
    poem_data = {}
    stanza_n = 0
    previous_stanza = None
    for verse_number, (_, row) in enumerate(poem.iterrows(), start=1):
        if verse_number == 1 or row[stanza_column] != previous_stanza:
            stanza_n += 1
            previous_stanza = row[stanza_column]
        transcription = row[transcription_column]
        rhyme_tail, vowels = rhyme_ending(transcription if isinstance(transcription, str) else "")
        meter = parse_syllable_value(row[syllable_column]) if syllable_column else None
        rhythm = parse_rhythm_value(row[stress_column]) if stress_column else []
        poem_data[verse_number] = {
            "row": row.name,
            "stanza": stanza_n,
            "rhyme_tail": rhyme_tail,
            "vowels": vowels,
            "meter": meter,
            **classify_verse_type(meter, rhythm),
            "_normalized_verse_text": normalize_refrain_text(row[text_column]),
            "asonante": None,
            "consonante": None,
            "_asonante_key": None,
            "_consonante_key": None,
            "final": None,
            "chosen_source": None,
            "letter": None,
            "retrouso": None,
            "observed_pattern": None,
            "expected_pattern": None,
            "stanza_type": None,
            "stanza_type_probability": None,
            "stanza_subtype": None,
            "stanza_subtype_probability": None,
            "poem_type": None,
            "poem_type_probability": None,
            "poem_subtype": None,
            "poem_subtype_probability": None,
        }
    return poem_data


def annotate(
    df,
    *,
    poem_column="poem_id",
    stanza_column="stanza_n",
    text_column="text",
    transcription_column="transcription",
    syllable_column="metrical_syllables",
    stress_column="stressed_syllables",
):
    """Annotate verses with rhyme letters, verse, stanza and poem types.

    ``df`` has one row per verse, in reading order, with the poem and stanza
    each belongs to, its text and its trasgo transcription. Meter (syllable
    count and stressed syllables, e.g. ``8`` and ``3 7``) is optional, but
    without it stanza and poem types are far less accurate. Meter columns
    missing from ``df`` are ignored.

    Returns a copy of ``df`` with the OUTPUT_COLUMNS added, and two tables
    with the score of every stanza and poem pattern considered. Rhyme letters
    are uppercase for lines of 9 syllables or more, when the meter is known.
    """
    for column in (poem_column, stanza_column, text_column, transcription_column):
        if column not in df.columns:
            raise ValueError(f"Column {column!r} not found. Available columns: {list(df.columns)}")
    clashes = [column for column in OUTPUT_COLUMNS if column in df.columns]
    if clashes:
        raise ValueError(f"The input already has output column(s) {clashes}; rename them first.")
    if syllable_column not in df.columns:
        syllable_column = None
    if stress_column not in df.columns:
        stress_column = None

    stanza_patterns = load_patterns("stanza_patterns.json")
    poem_patterns = load_patterns("poem_patterns.json")
    df = df.reset_index(drop=True)
    output_rows = {}
    stanza_score_rows = []
    poem_score_rows = []
    for poem_id, poem in df.groupby(poem_column, sort=False):
        poem_data = make_poem_data(
            poem, stanza_column, text_column, transcription_column, syllable_column, stress_column
        )
        enforce_short_gaita_pairs(poem_data)
        assign_rhymes(poem_data, stanza_patterns)
        stanza_rows = annotate_stanza_types(poem_data, stanza_patterns)
        detect_retrouso(poem_data)
        poem_rows = annotate_poem_type(poem_data, poem_patterns)
        stanza_score_rows += [{"poem_id": poem_id, **row} for row in stanza_rows]
        poem_score_rows += [{"poem_id": poem_id, **row} for row in poem_rows]
        for data in poem_data.values():
            if data["meter"] is not None and data["meter"] >= ARTE_MAIOR_MIN_SYLLABLES:
                data["letter"] = data["letter"].upper()
            data["vowels"] = ",".join(data["vowels"])
            data["retrouso"] = bool(data["retrouso"])
            output_rows[data["row"]] = {column: data[key] for column, key in OUTPUT_COLUMNS.items()}

    output = pd.DataFrame.from_dict(output_rows, orient="index").reindex(df.index)
    results = pd.concat([df, output], axis=1).map(clean_output_value)
    stanza_scores = pd.DataFrame(stanza_score_rows).map(clean_output_value)
    poem_scores = pd.DataFrame(poem_score_rows).map(clean_output_value)
    return results, stanza_scores, poem_scores
