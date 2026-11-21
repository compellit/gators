"""Helpers shared by rhyme, stanza and poem analysis.

A poem is held as ``poem_data``: a dict from verse number (1, 2, ...) to a dict
with that verse's data (rhyme ending, metre, rhyme class, stanza number...).

Rhyme schemes are written as patterns: one character per line, the same letter
for lines that rhyme together, ``-`` for an unrhymed line. Expected patterns in
the pattern files may also use ``0`` (must not rhyme), ``1`` (must rhyme, with
any other line) and ``*`` (any pattern). See docs/STANZA_PATTERN_SCORING.md.
"""

import json
import string
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
MIXED_METRE_DOMINANCE_THRESHOLD = 0.8


def load_patterns(file_name):
    """Read a pattern file (a list of entries) from the package data."""
    with (DATA_DIR / file_name).open(encoding="utf-8") as handle:
        return json.load(handle)


def relation_targets(entry, relation_key):
    value = entry.get(relation_key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def relation_matches(entry, relation_key, target):
    return target in relation_targets(entry, relation_key)


def get_stanzas(poem_data):
    stanzas = {}

    for verse, data in poem_data.items():
        stanzas.setdefault(data["stanza"], []).append((verse, data))

    return {stanza_n: sorted(stanza) for stanza_n, stanza in stanzas.items()}


def make_pattern(values):
    labels = {}
    pattern = []
    alphabet = string.ascii_lowercase + string.ascii_uppercase + string.digits

    for value in values:
        if value is None:
            pattern.append("-")
        elif value not in labels:
            labels[value] = alphabet[len(labels) % len(alphabet)]
            pattern.append(labels[value])
        else:
            pattern.append(labels[value])

    return "".join(pattern)


def expand_pattern(pattern, observed_length):
    pattern = pattern.replace(" ", "")
    if pattern == "*":
        return pattern
    if len(pattern) == observed_length:
        return pattern
    repeats = (observed_length + len(pattern) - 1) // len(pattern)
    return (pattern * repeats)[:observed_length]


def entry_allowed_for_length(entry, observed_length):
    if entry.get("repeat_pattern"):
        pattern_length = len(entry["patterns"][0].replace(" ", ""))
        return observed_length >= entry.get("min_verses", pattern_length)

    return observed_length == entry.get("stanza_length")


def observed_line_rhymes(pattern, index):
    return pattern[index] != "-"


def expected_line_relation(pattern, left_index, right_index):
    left = pattern[left_index]
    right = pattern[right_index]

    if "-" in (left, right):
        return None
    if left == "0" or right == "0":
        return False
    if left == "1" and right == "1":
        return None
    if left == "1":
        return right not in ("-", "0")
    if right == "1":
        return left not in ("-", "0")
    return left == right


def meets_min_pattern_similarity(entry, pattern_score):
    # Hard constraint: an entry with "min_pattern_similarity" is not a
    # candidate when the observed rhyme pattern is too far from the
    # expected one (e.g. an unrhymed two-line stanza is not a pareado).
    # Wildcard patterns (score None) are not affected.
    threshold = entry.get("min_pattern_similarity")
    if threshold is None or pattern_score is None:
        return True
    return pattern_score >= threshold


def meets_min_metre_similarity(entry, metre_score):
    # Hard constraint, like min_pattern_similarity: forms defined by
    # their metre alone (rhyme pattern "----") are not candidates for
    # a stanza far from that metre, or they would take any quatrain
    # that no rhymed form fits. Stanzas without metre are not affected.
    threshold = entry.get("min_metre_similarity")
    if threshold is None or metre_score is None:
        return True
    return metre_score >= threshold


def stanza_pattern_similarity(observed_pattern, expected_pattern):
    if expected_pattern == "*":
        return None

    matches = 0
    compared = 0

    for index, expected in enumerate(expected_pattern):
        if expected == "0":
            compared += 1
            if not observed_line_rhymes(observed_pattern, index):
                matches += 1
        elif expected == "1":
            compared += 1
            if observed_line_rhymes(observed_pattern, index):
                matches += 1

    for left_index in range(len(expected_pattern)):
        for right_index in range(left_index + 1, len(expected_pattern)):
            expected_relation = expected_line_relation(
                expected_pattern,
                left_index,
                right_index,
            )
            if expected_relation is None:
                continue

            compared += 1
            observed_relation = (
                observed_pattern[left_index] != "-"
                and observed_pattern[left_index] == observed_pattern[right_index]
            )
            if observed_relation == expected_relation:
                matches += 1

    if compared == 0:
        return None

    return matches / compared


def line_metre_similarity(observed, expected):
    if observed is None or expected is None:
        return None
    if observed == expected:
        return 1
    if observed <= 0 or expected <= 0:
        return 0
    return min(observed, expected) / max(observed, expected)


def boundary_metre_similarity(observed, expected, kind):
    if observed is None:
        return None
    if kind == "min" and observed >= expected:
        return 1
    if kind == "max" and observed <= expected:
        return 1
    return line_metre_similarity(observed, expected)


def stanza_metre_similarity(observed_metre, entry):
    metre = entry.get("metre")
    if not metre or any(value is None for value in observed_metre):
        return None

    kind = entry.get("metre_kind")
    scores = []

    if kind == "mixed":
        closest_counts = {expected: 0 for expected in metre}
        for observed in observed_metre:
            closest_distance = min(abs(observed - expected) for expected in metre)
            closest_metres = [
                expected
                for expected in metre
                if abs(observed - expected) == closest_distance
            ]
            for expected in closest_metres:
                closest_counts[expected] += 1
            scores.append(
                max(
                    line_metre_similarity(observed, expected)
                    for expected in closest_metres
                )
            )
        support = sorted(
            (count / len(observed_metre) for count in closest_counts.values()),
            reverse=True,
        )
        if (
            support
            and support[0] > MIXED_METRE_DOMINANCE_THRESHOLD
            and (len(support) == 1 or support[1] <= 1 - MIXED_METRE_DOMINANCE_THRESHOLD)
        ):
            return 0
    elif kind in ("min", "max"):
        expected = metre[0]
        for observed in observed_metre:
            scores.append(boundary_metre_similarity(observed, expected, kind))
    elif kind == "range":
        low, high = metre
        for observed in observed_metre:
            if low <= observed <= high:
                scores.append(1)
            else:
                scores.append(
                    max(
                        line_metre_similarity(observed, low),
                        line_metre_similarity(observed, high),
                    )
                )
    elif entry.get("repeat_metre") and len(metre) == 1:
        expected = metre[0]
        for observed in observed_metre:
            scores.append(line_metre_similarity(observed, expected))
    else:
        if len(metre) != len(observed_metre):
            return None
        for observed, expected in zip(observed_metre, metre):
            scores.append(line_metre_similarity(observed, expected))

    scores = [score for score in scores if score is not None]
    return sum(scores) / len(scores) if scores else None


def pair_type(left, right):
    if left["chosen_source"] == right["chosen_source"] == "asonante":
        return "asonante"
    if left["rhyme_tail"] == right["rhyme_tail"] and left["rhyme_tail"] not in (None, False, ""):
        return "consonante"
    return "asonante"


def observed_pair_data(stanza, observed_pattern):
    pairs = {}

    for left_index in range(len(stanza)):
        for right_index in range(left_index + 1, len(stanza)):
            if observed_pattern[left_index] == "-":
                continue
            if observed_pattern[left_index] != observed_pattern[right_index]:
                continue

            left = stanza[left_index][1]
            right = stanza[right_index][1]
            pairs[(left_index, right_index)] = pair_type(left, right)

    return pairs


def expected_pair_data(expected_pattern, rhymes=None, rhyme_kind=None):
    pairs = {}

    if expected_pattern == "*":
        return pairs

    for left_index in range(len(expected_pattern)):
        left = expected_pattern[left_index]
        if left in ("-", "0", "1"):
            continue
        for right_index in range(left_index + 1, len(expected_pattern)):
            if expected_pattern[right_index] != left:
                continue
            expected_type = rhymes.get(left) if rhymes else rhyme_kind
            pairs[(left_index, right_index)] = {
                "letter": left,
                "type": expected_type,
            }

    return pairs


def rhyme_type_similarity(observed_pairs, expected_pairs, rhyme_kind=None):
    if not expected_pairs and rhyme_kind not in ("asonante", "consonante"):
        return None

    if not expected_pairs:
        if not observed_pairs:
            return None
        matches = sum(1 for observed_type in observed_pairs.values() if observed_type == rhyme_kind)
        return matches / len(observed_pairs)

    compared = 0
    matches = 0

    for pair, expected in expected_pairs.items():
        expected_type = expected["type"]
        if expected_type in (None, "both"):
            continue
        compared += 1
        if observed_pairs.get(pair) == expected_type:
            matches += 1

    if compared == 0:
        return None

    return matches / compared


def format_pairs(pairs, max_pairs=50):
    formatted = [
        f"{left + 1}-{right + 1}:{value if isinstance(value, str) else value.get('type')}"
        for (left, right), value in sorted(pairs.items())
    ]
    if len(formatted) <= max_pairs:
        return formatted

    return {
        "total": len(formatted),
        "shown": formatted[:max_pairs],
        "truncated": True,
    }


def average_available(*scores):
    scores = [score for score in scores if score is not None]
    return sum(scores) / len(scores) if scores else None
