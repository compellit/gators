"""Verse types that depend on stress positions (gaita galega, endecasílabo types).

Experimental: verse types are not evaluated (there is no gold for them) and
no stanza or poem type uses them at present; they only fill the verse_type
output column.

Each line gets a verse type when its syllable count and stressed syllables
match one of VERSE_TYPE_PATTERNS: all the required stresses, and no stress
outside the required and optional ones.
"""

import pandas as pd
import regex as re

VERSE_TYPE_PATTERNS = [
    {
        "verse_type": "gaita_galega",
        "syllables": 11,
        "required": [4, 10],
        "optional": [1, 7],
    },
    {
        "verse_type": "gaita_galega",
        "syllables": 10,
        "required": [3, 9],
        "optional": [1, 6],
    },
    {
        "verse_type": "gaita_galega",
        "syllables": 12,
        "required": [5, 11],
        "optional": [2, 8],
    },
    {
        "verse_type": "gaita_galega",
        "syllables": 5,
        "required": [4],
        "optional": [1],
    },
    {
        "verse_type": "gaita_galega",
        "syllables": 6,
        "required": [5],
        "optional": [2],
    },
    {
        "verse_type": "endecasílabo_enfático",
        "syllables": 11,
        "required": [1, 6, 10],
        "optional": [],
    },
    {
        "verse_type": "endecasílabo_italiano",
        "syllables": 11,
        "required": [4, 8, 10],
        "optional": [],
    },
    {
        "verse_type": "endecasílabo_heroico",
        "syllables": 11,
        "required": [2, 6, 10],
        "optional": [],
    },
    {
        "verse_type": "endecasílabo_melódico",
        "syllables": 11,
        "required": [3, 6, 10],
        "optional": [],
    },
    {
        "verse_type": "endecasílabo_sáfico",
        "syllables": 11,
        "required": [1, 4, 6, 8, 10],
        "optional": [],
    },
    {
        "verse_type": "pentasílabo_adónico",
        "syllables": 5,
        "required": [1, 4],
        "optional": [],
    },
]


def parse_syllable_value(value):
    if pd.isna(value):
        return None

    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def parse_rhythm_value(value):
    if pd.isna(value):
        return []

    return [int(match) for match in re.findall(r"\d+", str(value))]


def verse_type_matches(observed, required, optional):
    observed = set(observed)
    required = set(required)
    optional = set(optional)
    allowed = required | optional
    return required.issubset(observed) and observed.issubset(allowed)


def classify_verse_type(syllables, rhythm):
    if syllables is None or not rhythm:
        return {
            "verse_type": None,
            "observed_rhythm": rhythm,
            "expected_rhythm": None,
        }

    candidates = [
        pattern
        for pattern in VERSE_TYPE_PATTERNS
        if pattern["syllables"] == syllables
    ]
    if not candidates:
        return {
            "verse_type": None,
            "observed_rhythm": rhythm,
            "expected_rhythm": None,
        }

    for pattern in candidates:
        if not verse_type_matches(
            rhythm,
            pattern["required"],
            pattern["optional"],
        ):
            continue

        return {
            "verse_type": pattern["verse_type"],
            "observed_rhythm": rhythm,
            "expected_rhythm": {
                "required": pattern["required"],
                "optional": pattern["optional"],
            },
        }

    return {
        "verse_type": None,
        "observed_rhythm": rhythm,
        "expected_rhythm": None,
    }


def enforce_short_gaita_pairs(poem_data):
    def is_short_gaita(verse):
        data = poem_data.get(verse)
        return (
            data
            and data["verse_type"] == "gaita_galega"
            and data["meter"] is not None
            and data["meter"] < 10
        )

    keep = set()
    stanzas = {}
    for verse, data in poem_data.items():
        stanzas.setdefault(data["stanza"], []).append(verse)

    for verses in stanzas.values():
        verses = sorted(verses)
        index = 0
        while index < len(verses) - 1:
            left = verses[index]
            right = verses[index + 1]
            if is_short_gaita(left) and is_short_gaita(right):
                keep.update((left, right))
                index += 2
            else:
                index += 1

    for verse, data in poem_data.items():
        if is_short_gaita(verse) and verse not in keep:
            data["verse_type"] = None
            data["expected_rhythm"] = None
