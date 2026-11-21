"""Stanza types.

Each stanza is scored against every entry of stanza_patterns.json (rhyme
pattern, meter, rhyme type, verse types). The best entry wins in a first
round; in a second round, each candidate's score is averaged with how often
its type won in the poem's other stanzas. See docs/STANZA_AND_POEM_TYPES.md.
"""

from .patterns import (
    average_available,
    entry_allowed_for_length,
    expand_pattern,
    expected_pair_data,
    format_pairs,
    get_stanzas,
    make_pattern,
    meets_min_meter_similarity,
    meets_min_pattern_similarity,
    observed_pair_data,
    relation_matches,
    relation_targets,
    rhyme_type_similarity,
    stanza_meter_similarity,
    stanza_pattern_similarity,
)

PROBABILITY_TIE_TOLERANCE = 1e-12
SUBTYPE_MIN_PROBABILITY = 0.8
POEM_PROBABILITY_DEFAULTS_KEY = "__defaults_by_length__"


def stanza_verse_type_similarity(stanza, entry):
    expected = entry.get("verse_types")
    if not expected:
        return None

    observed = [data["verse_type"] for _, data in stanza]
    return int(observed == expected)


def score_stanza_entry(stanza, entry):
    observed_length = len(stanza)
    if not entry_allowed_for_length(entry, observed_length):
        return None

    finals = [data["final"] for _, data in stanza]
    observed_pattern = make_pattern(finals)
    observed_meter = [data["meter"] for _, data in stanza]
    observed_pairs = observed_pair_data(stanza, observed_pattern)
    meter_score = stanza_meter_similarity(observed_meter, entry)
    if not meets_min_meter_similarity(entry, meter_score):
        return None
    verse_type_score = stanza_verse_type_similarity(stanza, entry)

    best = None
    for pattern in entry["patterns"]:
        expected_pattern = expand_pattern(pattern, observed_length)
        pattern_score = stanza_pattern_similarity(observed_pattern, expected_pattern)
        if not meets_min_pattern_similarity(entry, pattern_score):
            continue
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
        components = [
            score
            for score in (
                pattern_score,
                meter_score,
                rhyme_score,
                verse_type_score,
            )
            if score is not None
        ]
        probability = sum(components) / len(components) if components else 1
        result = {
            "entry": entry,
            "probability": probability,
            "observed_pattern": observed_pattern,
            "expected_pattern": expected_pattern,
            "observed_meter": observed_meter,
            "expected_meter": entry.get("meter"),
            "observed_verse_types": [
                data["verse_type"] for _, data in stanza
            ],
            "expected_verse_types": entry.get("verse_types"),
            "expected_rhymes": entry.get("rhymes") or entry.get("rhyme_kind"),
            "observed_rhyme_pairs": format_pairs(observed_pairs),
            "expected_rhyme_pairs": format_pairs(expected_pairs),
            "pattern_similarity": pattern_score,
            "meter_similarity": meter_score,
            "rhyme_type_similarity": rhyme_score,
            "verse_type_similarity": verse_type_score,
        }
        if best is None or result["probability"] > best["probability"]:
            best = result

    return best


def tied_max(items, key):
    keyed_items = [(item, key(item)) for item in items]
    best_value = max(value for _, value in keyed_items)
    return [
        item
        for item, value in keyed_items
        if abs(value - best_value) <= PROBABILITY_TIE_TOLERANCE
    ]


def subtype_selection_component(score):
    return score["entry"].get("subtype_selection_component") or "probability"


def subtype_selection_value(score):
    return score.get(subtype_selection_component(score))


def subtype_selection_threshold(score):
    return score["entry"].get(
        "subtype_selection_threshold",
        SUBTYPE_MIN_PROBABILITY,
    )


def subtype_is_selected(score):
    value = subtype_selection_value(score)
    return value is not None and value >= subtype_selection_threshold(score)


def choose_subtype(parent_type, scores):
    candidates = [
        score
        for score in scores
        if score["entry"].get("parent_type") == parent_type
        and subtype_is_selected(score)
    ]
    if not candidates:
        return None
    return max(candidates, key=subtype_selection_value)


def choose_refinement(stanza_type, scores, poem_probabilities=None):
    poem_probabilities = poem_probabilities or {}

    def refinement_score(score):
        refined_type = score["entry"]["stanza_type"]
        return adjusted_probability(
            score["probability"],
            refined_type,
            poem_probabilities,
            score_stanza_length(score),
        )

    candidates = [
        score
        for score in scores
        if relation_matches(score["entry"], "refines_type", stanza_type)
    ]
    if not candidates:
        return None
    best = max(candidates, key=refinement_score)
    if refinement_score(best) >= SUBTYPE_MIN_PROBABILITY:
        return best
    return None


def score_for_stanza_type(stanza_type, scores):
    candidates = [
        score
        for score in scores
        if score["entry"].get("stanza_type") == stanza_type
        and not score["entry"].get("parent_type")
        and not score["entry"].get("refines_type")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda score: score["probability"])


def stanza_candidate_key(score):
    entry = score["entry"]
    return entry["stanza_type"]


def score_stanza_length(score):
    return len(score["observed_meter"])


def poem_probability_for(key, poem_probabilities, stanza_length=None):
    if key is None or not poem_probabilities:
        return None
    if key in poem_probabilities:
        return poem_probabilities[key]
    defaults = poem_probabilities.get(POEM_PROBABILITY_DEFAULTS_KEY, {})
    if stanza_length is not None:
        return defaults.get(stanza_length)
    return None


def adjusted_probability(probability, key, poem_probabilities, stanza_length=None):
    poem_probability = poem_probability_for(key, poem_probabilities, stanza_length)
    if poem_probability is not None:
        return average_available(probability, poem_probability)
    return probability


def resolve_stanza_output(scores, winner, poem_probabilities=None, adjust=False):
    poem_probabilities = poem_probabilities or {}
    entry = winner["entry"]
    stanza_length = score_stanza_length(winner)
    stanza_type = entry["stanza_type"]
    stanza_probability = winner["probability"]
    stanza_type_probability_poem = poem_probability_for(
        stanza_type,
        poem_probabilities,
        stanza_length,
    )
    stanza_subtype = None
    stanza_subtype_probability = None
    stanza_subtype_probability_poem = None

    if entry.get("parent_type"):
        parent_score = score_for_stanza_type(entry["parent_type"], scores)
        stanza_type = entry["parent_type"]
        stanza_probability = (
            parent_score["probability"]
            if parent_score
            else winner["probability"]
        )
        stanza_type_probability_poem = poem_probability_for(
            stanza_type,
            poem_probabilities,
            stanza_length,
        )
        stanza_subtype = entry["stanza_type"]
        stanza_subtype_probability = winner["probability"]
        stanza_subtype_probability_poem = poem_probability_for(
            stanza_subtype,
            poem_probabilities,
            stanza_length,
        )
    else:
        subtype = choose_subtype(stanza_type, scores)
        if subtype:
            stanza_subtype = subtype["entry"]["stanza_type"]
            stanza_subtype_probability = subtype["probability"]
            stanza_subtype_probability_poem = poem_probability_for(
                stanza_subtype,
                poem_probabilities,
                stanza_length,
            )

    refinement = choose_refinement(
        stanza_type,
        scores,
        poem_probabilities if adjust else None,
    )
    if refinement:
        winner = refinement
        entry = winner["entry"]
        stanza_length = score_stanza_length(winner)
        stanza_type = entry["stanza_type"]
        stanza_probability = winner["probability"]
        stanza_type_probability_poem = poem_probability_for(
            stanza_type,
            poem_probabilities,
            stanza_length,
        )
        stanza_subtype = None
        stanza_subtype_probability = None
        stanza_subtype_probability_poem = None
        subtype = choose_subtype(stanza_type, scores)
        if subtype:
            stanza_subtype = subtype["entry"]["stanza_type"]
            stanza_subtype_probability = subtype["probability"]
            stanza_subtype_probability_poem = poem_probability_for(
                stanza_subtype,
                poem_probabilities,
                stanza_length,
            )

    if adjust:
        stanza_probability = adjusted_probability(
            stanza_probability,
            stanza_type,
            poem_probabilities,
            stanza_length,
        )
        if stanza_subtype:
            stanza_subtype_probability = adjusted_probability(
                stanza_subtype_probability,
                stanza_subtype,
                poem_probabilities,
                stanza_length,
            )

    return {
        "winner": winner,
        "stanza_type": stanza_type,
        "stanza_type_probability": stanza_probability,
        "stanza_type_probability_poem": stanza_type_probability_poem,
        "stanza_subtype": stanza_subtype,
        "stanza_subtype_probability": stanza_subtype_probability,
        "stanza_subtype_probability_poem": stanza_subtype_probability_poem,
    }


def output_probability_keys(output):
    keys = [output["stanza_type"]]
    if output["stanza_subtype"]:
        keys.append(output["stanza_subtype"])
    return [key for key in keys if key is not None]


def score_probability_keys(score):
    entry = score["entry"]
    keys = {
        entry.get("stanza_type"),
        entry.get("parent_type"),
    }
    keys.update(relation_targets(entry, "refines_type"))
    return {key for key in keys if key is not None}


def poem_probability_defaults(scores_by_stanza, stanza_count):
    labels_by_length = {}
    for scores in scores_by_stanza:
        if not scores:
            continue
        stanza_length = score_stanza_length(scores[0])
        labels = labels_by_length.setdefault(stanza_length, set())
        for score in scores:
            labels.update(score_probability_keys(score))
    return {
        stanza_length: 1 / (stanza_count + len(labels))
        for stanza_length, labels in labels_by_length.items()
    }


def poem_stanza_probabilities(outputs_by_stanza, scores_by_stanza, stanza_count):
    totals = {}
    for outputs in outputs_by_stanza:
        stanza_keys = set()
        for output in outputs:
            stanza_keys.update(output_probability_keys(output))
        for key in stanza_keys:
            totals[key] = totals.get(key, 0) + 1
    probabilities = {
        key: total / stanza_count
        for key, total in totals.items()
    }
    probabilities[POEM_PROBABILITY_DEFAULTS_KEY] = poem_probability_defaults(
        scores_by_stanza,
        stanza_count,
    )
    return probabilities


def second_round_score(score, poem_probabilities):
    poem_probability = poem_probability_for(
        stanza_candidate_key(score),
        poem_probabilities,
        score_stanza_length(score),
    )
    return average_available(score["probability"], poem_probability)


def annotate_stanza_types(poem_data, stanza_patterns):
    stanza_score_rows = []
    if not stanza_patterns:
        return stanza_score_rows

    stanza_scores = []
    for stanza_n, stanza in get_stanzas(poem_data).items():
        scores = [
            score_stanza_entry(stanza, entry)
            for entry in stanza_patterns
        ]
        scores = [score for score in scores if score is not None]
        if not scores:
            continue
        stanza_scores.append((stanza_n, stanza, scores))

    if not stanza_scores:
        return stanza_score_rows

    first_round_winners_by_stanza = [
        tied_max(
            scores,
            key=lambda score: score["probability"],
        )
        for _, _, scores in stanza_scores
    ]
    first_round_outputs_by_stanza = [
        [
            resolve_stanza_output(scores, winner)
            for winner in winners
        ]
        for (_, _, scores), winners in zip(stanza_scores, first_round_winners_by_stanza)
    ]
    poem_probabilities = poem_stanza_probabilities(
        first_round_outputs_by_stanza,
        [scores for _, _, scores in stanza_scores],
        len(stanza_scores),
    )

    for stanza_n, stanza, scores in stanza_scores:
        winner = max(
            scores,
            key=lambda score: second_round_score(score, poem_probabilities),
        )
        output = resolve_stanza_output(
            scores,
            winner,
            poem_probabilities,
            adjust=True,
        )
        winner = output["winner"]

        for score in scores:
            entry = score["entry"]
            stanza_type = entry["stanza_type"]
            poem_probability = poem_probability_for(
                stanza_type,
                poem_probabilities,
                len(stanza),
            )
            stanza_score_rows.append(
                {
                    "stanza_n": stanza_n,
                    "verse_count": len(stanza),
                    "stanza_type": stanza_type,
                    "parent_type": entry.get("parent_type"),
                    "refines_type": entry.get("refines_type"),
                    "probability": score["probability"],
                    "probability_poem": poem_probability,
                    "probability_with_poem": adjusted_probability(
                        score["probability"],
                        stanza_type,
                        poem_probabilities,
                        len(stanza),
                    ),
                    "pattern_similarity": score["pattern_similarity"],
                    "meter_similarity": score["meter_similarity"],
                    "rhyme_type_similarity": score["rhyme_type_similarity"],
                    "verse_type_similarity": score.get("verse_type_similarity"),
                    "subtype_selection_component": (
                        subtype_selection_component(score)
                        if entry.get("parent_type")
                        else None
                    ),
                    "subtype_selection_value": (
                        subtype_selection_value(score)
                        if entry.get("parent_type")
                        else None
                    ),
                    "subtype_selection_threshold": (
                        subtype_selection_threshold(score)
                        if entry.get("parent_type")
                        else None
                    ),
                    "observed_pattern": score["observed_pattern"],
                    "expected_pattern": score["expected_pattern"],
                    "observed_meter": score["observed_meter"],
                    "expected_meter": score["expected_meter"],
                    "selected": stanza_type in {
                        output["stanza_type"],
                        output["stanza_subtype"],
                    },
                }
            )

        for _, data in stanza:
            data["observed_pattern"] = winner["observed_pattern"]
            data["expected_pattern"] = winner["expected_pattern"]
            data["observed_meter"] = winner["observed_meter"]
            data["expected_meter"] = winner["expected_meter"]
            data["expected_rhymes"] = winner["expected_rhymes"]
            data["observed_rhyme_pairs"] = winner["observed_rhyme_pairs"]
            data["expected_rhyme_pairs"] = winner["expected_rhyme_pairs"]
            data["pattern_similarity"] = winner["pattern_similarity"]
            data["meter_similarity"] = winner["meter_similarity"]
            data["rhyme_type_similarity"] = winner["rhyme_type_similarity"]
            data["stanza_type"] = output["stanza_type"]
            data["stanza_type_probability"] = output["stanza_type_probability"]
            data["stanza_type_probability_poem"] = output["stanza_type_probability_poem"]
            data["stanza_subtype"] = output["stanza_subtype"]
            data["stanza_subtype_probability"] = output["stanza_subtype_probability"]
            data["stanza_subtype_probability_poem"] = output["stanza_subtype_probability_poem"]

    return stanza_score_rows
