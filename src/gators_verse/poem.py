"""Poem types and refrains.

The whole poem is scored against every entry of poem_patterns.json (rhyme
pattern, meter, rhyme type, stanza types, refrain, stanza lengths, verse and
stanza counts). Without a type scoring at least POEM_TYPE_MIN_SCORE,
a poem whose stanzas all share a type is labelled after it ("Serie de
cuarteto"). See docs/STANZA_AND_POEM_TYPES.md.
"""

import pandas as pd
import regex as re

from .patterns import (
    expand_pattern,
    expected_pair_data,
    get_stanzas,
    make_pattern,
    observed_pair_data,
    relation_matches,
    rhyme_type_similarity,
    stanza_meter_similarity,
    stanza_pattern_similarity,
)

POEM_TYPE_MIN_SCORE = 0.8


def normalize_refrain_text(value):
    if pd.isna(value):
        return ""

    value = str(value).lower()
    value = re.sub(r"\p{P}+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def detect_retrouso(poem_data):
    by_text = {}
    for verse, data in poem_data.items():
        text = data["_normalized_verse_text"]
        if text:
            by_text.setdefault(text, []).append(verse)

    for verses in by_text.values():
        if len(verses) > 1:
            for verse in verses:
                poem_data[verse]["retrouso"] = True

    pair_positions = {}
    verses = sorted(poem_data)
    for left, right in zip(verses, verses[1:]):
        left_text = poem_data[left]["_normalized_verse_text"]
        right_text = poem_data[right]["_normalized_verse_text"]
        if not left_text or not right_text:
            continue
        pair_positions.setdefault((left_text, right_text), []).append((left, right))

    for pairs in pair_positions.values():
        if len(pairs) > 1:
            for left, right in pairs:
                poem_data[left]["retrouso"] = True
                poem_data[right]["retrouso"] = True


def poem_entry_allowed_for_length(entry, observed_length):
    if observed_length < entry.get("min_verses", 0):
        return False
    if entry.get("length_multiple") and observed_length % entry["length_multiple"] != 0:
        return False
    return True


def poem_observed_pairs(poem_lines, observed_pattern):
    return observed_pair_data(poem_lines, observed_pattern)


def count_similarity(observed, expected):
    if expected is None:
        return None
    if observed == expected:
        return 1
    if observed <= 0 or expected <= 0:
        return 0
    return min(observed, expected) / max(observed, expected)


def stanza_labels(data):
    labels = set()
    if data.get("stanza_type") not in (None, ""):
        labels.add(data["stanza_type"])
    if data.get("stanza_subtype") not in (None, ""):
        labels.add(data["stanza_subtype"])
    return labels


def poem_stanza_type_similarity(stanzas, entry):
    observed = [stanza[0][1] for stanza in stanzas.values()]

    if entry.get("stanza_type"):
        matches = sum(
            1
            for data in observed
            if entry["stanza_type"] in stanza_labels(data)
        )
        return matches / len(observed) if observed else None

    expected_sequence = entry.get("stanza_types")
    if not expected_sequence:
        return None

    compared = max(len(observed), len(expected_sequence))
    if entry.get("extra_stanza_type") and len(observed) > len(expected_sequence):
        compared = len(observed)

    if compared == 0:
        return None

    matches = 0
    for index, data in enumerate(observed):
        if index < len(expected_sequence):
            expected = set(expected_sequence[index])
        elif entry.get("extra_stanza_type"):
            expected = {entry["extra_stanza_type"]}
        else:
            expected = set()

        if stanza_labels(data) & expected:
            matches += 1

    return matches / compared


def poem_stanza_length_similarity(stanzas, entry):
    expected_lengths = entry.get("stanza_lengths")
    if not expected_lengths:
        return None

    observed_lengths = [len(stanza) for stanza in stanzas.values()]
    if len(observed_lengths) < len(expected_lengths):
        return 0

    compared = max(len(observed_lengths), len(expected_lengths))
    matches = 0
    for index, observed_length in enumerate(observed_lengths):
        if index < len(expected_lengths):
            expected_length = expected_lengths[index]
        elif entry.get("extra_stanza_length") is not None:
            expected_length = entry["extra_stanza_length"]
        else:
            expected_length = None

        if expected_length is not None and observed_length == expected_length:
            matches += 1

    return matches / compared if compared else None


def refrain_units(poem_lines, entry):
    stanzas = get_stanzas({verse: data for verse, data in poem_lines})
    if len(stanzas) > 1:
        return [stanza for stanza in stanzas.values()]

    multiple = entry.get("length_multiple")
    if multiple:
        return [
            poem_lines[index:index + multiple]
            for index in range(0, len(poem_lines), multiple)
            if len(poem_lines[index:index + multiple]) == multiple
        ]

    return [poem_lines]


def poem_refrain_similarity(poem_lines, entry):
    refrain = entry.get("refrain")
    if not refrain:
        return None

    positions = refrain.get("positions") or []
    units = refrain_units(poem_lines, entry)
    if not positions or not units:
        return None

    compared = 0
    matches = 0
    texts_by_position = {position: [] for position in positions}

    for unit in units:
        for position in positions:
            compared += 1
            index = position - 1
            if index >= len(unit):
                continue
            _, data = unit[index]
            if data.get("retrouso"):
                matches += 1
            texts_by_position[position].append(data["_normalized_verse_text"])

    if compared == 0:
        return None

    result = matches / compared
    if refrain.get("repeat_across_stanzas"):
        repeated_scores = []
        for texts in texts_by_position.values():
            texts = [text for text in texts if text]
            if len(texts) < 2:
                repeated_scores.append(0)
            else:
                most_common = max(texts.count(text) for text in set(texts))
                repeated_scores.append(most_common / len(texts))
        result = min(result, sum(repeated_scores) / len(repeated_scores))

    return result


def score_poem_entry(poem_data, entry):
    poem_lines = sorted(poem_data.items())
    observed_length = len(poem_lines)
    if not poem_entry_allowed_for_length(entry, observed_length):
        return None

    finals = [data["final"] for _, data in poem_lines]
    observed_pattern = make_pattern(finals)
    observed_meter = [data["meter"] for _, data in poem_lines]
    observed_pairs = poem_observed_pairs(poem_lines, observed_pattern)
    stanzas = get_stanzas(poem_data)

    meter_score = stanza_meter_similarity(observed_meter, entry)
    stanza_type_score = poem_stanza_type_similarity(stanzas, entry)
    stanza_length_score = poem_stanza_length_similarity(stanzas, entry)
    refrain_score = poem_refrain_similarity(poem_lines, entry)
    verse_count_score = count_similarity(observed_length, entry.get("verse_count"))
    stanza_count_score = count_similarity(len(stanzas), entry.get("stanza_count"))

    if entry.get("min_stanza_count") is not None:
        stanza_count_score = (
            1
            if len(stanzas) >= entry["min_stanza_count"]
            else len(stanzas) / entry["min_stanza_count"]
        )

    best = None
    for pattern in entry.get("patterns", ["*"]):
        expected_pattern = expand_pattern(pattern, observed_length)
        if expected_pattern != "*" and len(expected_pattern) != observed_length:
            continue
        pattern_score = stanza_pattern_similarity(observed_pattern, expected_pattern)
        expected_pairs = expected_pair_data(
            expected_pattern,
            entry.get("rhymes"),
            entry.get("rhyme_kind"),
        )
        rhyme_score = rhyme_type_similarity(
            observed_pairs,
            expected_pairs,
            entry.get("rhyme_kind"),
        )

        component_scores = {
            "pattern": pattern_score,
            "meter": meter_score,
            "rhyme_type": rhyme_score,
            "stanza_type": stanza_type_score,
        }
        if entry.get("refrain", {}).get("required") and refrain_score != 1:
            score = 0
        elif entry.get("stanza_lengths") and stanza_length_score != 1:
            score = 0
        elif any(
            component_scores.get(name) != 1
            for name in entry.get("required_components", ())
        ):
            # Hard requirement: a missing (None) or partial result
            # rules the type out, so that perfect counts cannot
            # outweigh e.g. a wrong meter (8-8-8 tercets as haiku).
            score = 0
        else:
            components = [
                result
                for result in (
                    pattern_score,
                    meter_score,
                    rhyme_score,
                    stanza_type_score,
                    refrain_score,
                    stanza_length_score,
                    verse_count_score,
                    stanza_count_score,
                )
                if result is not None
            ]
            score = sum(components) / len(components) if components else 1

        result = {
            "entry": entry,
            "score": score,
            "observed_pattern": observed_pattern,
            "expected_pattern": expected_pattern,
            "observed_meter": observed_meter,
            "expected_meter": entry.get("meter"),
            "pattern_similarity": pattern_score,
            "meter_similarity": meter_score,
            "rhyme_type_similarity": rhyme_score,
            "stanza_type_similarity": stanza_type_score,
            "refrain_similarity": refrain_score,
            "stanza_length_similarity": stanza_length_score,
            "verse_count_similarity": verse_count_score,
            "stanza_count_similarity": stanza_count_score,
        }
        if best is None or result["score"] > best["score"]:
            best = result

    return best


def annotate_poem_type(poem_data, poem_patterns):
    poem_score_rows = []

    def record_poem_scores(results, selected_labels=()):
        selected_labels = set(selected_labels)
        stanza_count = len(get_stanzas(poem_data))
        for result in results:
            entry = result["entry"]
            poem_score_rows.append(
                {
                    "verse_count": len(poem_data),
                    "stanza_count": stanza_count,
                    "poem_type": entry["poem_type"],
                    "parent_type": entry.get("parent_type"),
                    "refines_type": entry.get("refines_type"),
                    "score": result["score"],
                    "selection_threshold": POEM_TYPE_MIN_SCORE,
                    "pattern_similarity": result["pattern_similarity"],
                    "meter_similarity": result["meter_similarity"],
                    "rhyme_type_similarity": result["rhyme_type_similarity"],
                    "stanza_type_similarity": result["stanza_type_similarity"],
                    "refrain_similarity": result["refrain_similarity"],
                    "stanza_length_similarity": result["stanza_length_similarity"],
                    "verse_count_similarity": result["verse_count_similarity"],
                    "stanza_count_similarity": result["stanza_count_similarity"],
                    "observed_pattern": result["observed_pattern"],
                    "expected_pattern": result["expected_pattern"],
                    "observed_meter": result["observed_meter"],
                    "expected_meter": result["expected_meter"],
                    "selected": entry["poem_type"] in selected_labels,
                }
            )

    def annotate_fallback_type():
        stanza_types = []
        for stanza in get_stanzas(poem_data).values():
            stanza_type = next(
                (
                    data.get("stanza_type")
                    for _, data in stanza
                    if data.get("stanza_type") not in (None, "")
                ),
                None,
            )
            stanza_types.append(stanza_type)

        if len(stanza_types) == 1 and stanza_types[0]:
            poem_type = stanza_types[0]
        elif (
            len(stanza_types) > 1
            and stanza_types[0]
            and all(value == stanza_types[0] for value in stanza_types)
        ):
            poem_type = f"Serie de {stanza_types[0]}"
        else:
            poem_type = "-"

        for data in poem_data.values():
            data["poem_type"] = poem_type

    if not poem_patterns:
        annotate_fallback_type()
        return poem_score_rows

    results = [
        score_poem_entry(poem_data, entry)
        for entry in poem_patterns
    ]
    results = [result for result in results if result is not None]
    if not results:
        annotate_fallback_type()
        return poem_score_rows

    def best_poem_entry(poem_type):
        candidates = [
            result
            for result in results
            if result["entry"].get("poem_type") == poem_type
            and not result["entry"].get("parent_type")
            and not result["entry"].get("refines_type")
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda result: result["score"])

    def best_child(parent_type, relation_key):
        candidates = [
            result
            for result in results
            if relation_matches(result["entry"], relation_key, parent_type)
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda result: result["score"])
        if best["score"] >= POEM_TYPE_MIN_SCORE:
            return best
        return None

    winner = max(results, key=lambda result: result["score"])
    entry = winner["entry"]
    poem_type = entry["poem_type"]
    score = winner["score"]
    selected_score = winner["score"]
    poem_subtype = None
    poem_subtype_score = None

    if entry.get("parent_type"):
        parent_score = best_poem_entry(entry["parent_type"])
        poem_type = entry["parent_type"]
        score = (
            parent_score["score"]
            if parent_score
            else winner["score"]
        )
        poem_subtype = entry["poem_type"]
        poem_subtype_score = winner["score"]
    else:
        subtype = best_child(poem_type, "parent_type")
        if subtype:
            poem_subtype = subtype["entry"]["poem_type"]
            poem_subtype_score = subtype["score"]

    refinement = best_child(poem_type, "refines_type")
    if refinement:
        winner = refinement
        entry = winner["entry"]
        poem_type = entry["poem_type"]
        score = winner["score"]
        selected_score = winner["score"]
        poem_subtype = None
        poem_subtype_score = None
        subtype = best_child(poem_type, "parent_type")
        if subtype:
            poem_subtype = subtype["entry"]["poem_type"]
            poem_subtype_score = subtype["score"]
    elif entry.get("refines_type"):
        poem_type = entry["poem_type"]
        score = winner["score"]
        selected_score = winner["score"]
        poem_subtype = None
        poem_subtype_score = None

    if selected_score < POEM_TYPE_MIN_SCORE:
        record_poem_scores(results)
        annotate_fallback_type()
        return poem_score_rows

    record_poem_scores(
        results,
        [
            label
            for label in (poem_type, poem_subtype)
            if label is not None
        ],
    )
    forced_stanza_type = entry.get("set_stanza_type")
    for data in poem_data.values():
        data["poem_type"] = poem_type
        data["poem_type_score"] = score
        data["poem_subtype"] = poem_subtype
        data["poem_subtype_score"] = poem_subtype_score
        data["poem_expected_pattern"] = winner["expected_pattern"]
        data["poem_observed_pattern"] = winner["observed_pattern"]
        data["poem_pattern_similarity"] = winner["pattern_similarity"]
        data["poem_meter_similarity"] = winner["meter_similarity"]
        data["poem_rhyme_type_similarity"] = winner["rhyme_type_similarity"]
        data["poem_stanza_type_similarity"] = winner["stanza_type_similarity"]
        data["poem_refrain_similarity"] = winner["refrain_similarity"]
        data["poem_stanza_length_similarity"] = winner["stanza_length_similarity"]
        data["poem_verse_count_similarity"] = winner["verse_count_similarity"]
        data["poem_stanza_count_similarity"] = winner["stanza_count_similarity"]
        if forced_stanza_type:
            data["stanza_type"] = forced_stanza_type
            data["stanza_type_score"] = score
            data["stanza_type_score_poem"] = score
            data["stanza_subtype"] = None
            data["stanza_subtype_score"] = None
            data["stanza_subtype_score_poem"] = None

    return poem_score_rows
