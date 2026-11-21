"""Stanza types.

Each stanza is scored against every entry of stanza_patterns.json (rhyme
pattern, meter, rhyme type, verse types). The best entry wins in a first
round; in a second round, each candidate's result is averaged with how often
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

SCORE_TIE_TOLERANCE = 1e-12
SUBTYPE_MIN_SCORE = 0.8
POEM_SCORE_DEFAULTS_KEY = "__defaults_by_length__"


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
            result
            for result in (
                pattern_score,
                meter_score,
                rhyme_score,
                verse_type_score,
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
        if best is None or result["score"] > best["score"]:
            best = result

    return best


def tied_max(items, key):
    keyed_items = [(item, key(item)) for item in items]
    best_value = max(value for _, value in keyed_items)
    return [
        item
        for item, value in keyed_items
        if abs(value - best_value) <= SCORE_TIE_TOLERANCE
    ]


def subtype_selection_component(result):
    return result["entry"].get("subtype_selection_component") or "score"


def subtype_selection_value(result):
    return result.get(subtype_selection_component(result))


def subtype_selection_threshold(result):
    return result["entry"].get(
        "subtype_selection_threshold",
        SUBTYPE_MIN_SCORE,
    )


def subtype_is_selected(result):
    value = subtype_selection_value(result)
    return value is not None and value >= subtype_selection_threshold(result)


def choose_subtype(parent_type, results):
    candidates = [
        result
        for result in results
        if result["entry"].get("parent_type") == parent_type
        and subtype_is_selected(result)
    ]
    if not candidates:
        return None
    return max(candidates, key=subtype_selection_value)


def choose_refinement(stanza_type, results, poem_scores=None):
    poem_scores = poem_scores or {}

    def refinement_score(result):
        refined_type = result["entry"]["stanza_type"]
        return adjusted_score(
            result["score"],
            refined_type,
            poem_scores,
            score_stanza_length(result),
        )

    candidates = [
        result
        for result in results
        if relation_matches(result["entry"], "refines_type", stanza_type)
    ]
    if not candidates:
        return None
    best = max(candidates, key=refinement_score)
    if refinement_score(best) >= SUBTYPE_MIN_SCORE:
        return best
    return None


def score_for_stanza_type(stanza_type, results):
    candidates = [
        result
        for result in results
        if result["entry"].get("stanza_type") == stanza_type
        and not result["entry"].get("parent_type")
        and not result["entry"].get("refines_type")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda result: result["score"])


def stanza_candidate_key(result):
    entry = result["entry"]
    return entry["stanza_type"]


def score_stanza_length(result):
    return len(result["observed_meter"])


def poem_score_for(key, poem_scores, stanza_length=None):
    if key is None or not poem_scores:
        return None
    if key in poem_scores:
        return poem_scores[key]
    defaults = poem_scores.get(POEM_SCORE_DEFAULTS_KEY, {})
    if stanza_length is not None:
        return defaults.get(stanza_length)
    return None


def adjusted_score(score, key, poem_scores, stanza_length=None):
    poem_score = poem_score_for(key, poem_scores, stanza_length)
    if poem_score is not None:
        return average_available(score, poem_score)
    return score


def resolve_stanza_output(results, winner, poem_scores=None, adjust=False):
    poem_scores = poem_scores or {}
    entry = winner["entry"]
    stanza_length = score_stanza_length(winner)
    stanza_type = entry["stanza_type"]
    stanza_score = winner["score"]
    stanza_type_score_poem = poem_score_for(
        stanza_type,
        poem_scores,
        stanza_length,
    )
    stanza_subtype = None
    stanza_subtype_score = None
    stanza_subtype_score_poem = None

    if entry.get("parent_type"):
        parent_score = score_for_stanza_type(entry["parent_type"], results)
        stanza_type = entry["parent_type"]
        stanza_score = (
            parent_score["score"]
            if parent_score
            else winner["score"]
        )
        stanza_type_score_poem = poem_score_for(
            stanza_type,
            poem_scores,
            stanza_length,
        )
        stanza_subtype = entry["stanza_type"]
        stanza_subtype_score = winner["score"]
        stanza_subtype_score_poem = poem_score_for(
            stanza_subtype,
            poem_scores,
            stanza_length,
        )
    else:
        subtype = choose_subtype(stanza_type, results)
        if subtype:
            stanza_subtype = subtype["entry"]["stanza_type"]
            stanza_subtype_score = subtype["score"]
            stanza_subtype_score_poem = poem_score_for(
                stanza_subtype,
                poem_scores,
                stanza_length,
            )

    refinement = choose_refinement(
        stanza_type,
        results,
        poem_scores if adjust else None,
    )
    if refinement:
        winner = refinement
        entry = winner["entry"]
        stanza_length = score_stanza_length(winner)
        stanza_type = entry["stanza_type"]
        stanza_score = winner["score"]
        stanza_type_score_poem = poem_score_for(
            stanza_type,
            poem_scores,
            stanza_length,
        )
        stanza_subtype = None
        stanza_subtype_score = None
        stanza_subtype_score_poem = None
        subtype = choose_subtype(stanza_type, results)
        if subtype:
            stanza_subtype = subtype["entry"]["stanza_type"]
            stanza_subtype_score = subtype["score"]
            stanza_subtype_score_poem = poem_score_for(
                stanza_subtype,
                poem_scores,
                stanza_length,
            )

    if adjust:
        stanza_score = adjusted_score(
            stanza_score,
            stanza_type,
            poem_scores,
            stanza_length,
        )
        if stanza_subtype:
            stanza_subtype_score = adjusted_score(
                stanza_subtype_score,
                stanza_subtype,
                poem_scores,
                stanza_length,
            )

    return {
        "winner": winner,
        "stanza_type": stanza_type,
        "stanza_type_score": stanza_score,
        "stanza_type_score_poem": stanza_type_score_poem,
        "stanza_subtype": stanza_subtype,
        "stanza_subtype_score": stanza_subtype_score,
        "stanza_subtype_score_poem": stanza_subtype_score_poem,
    }


def output_score_keys(output):
    keys = [output["stanza_type"]]
    if output["stanza_subtype"]:
        keys.append(output["stanza_subtype"])
    return [key for key in keys if key is not None]


def score_score_keys(result):
    entry = result["entry"]
    keys = {
        entry.get("stanza_type"),
        entry.get("parent_type"),
    }
    keys.update(relation_targets(entry, "refines_type"))
    return {key for key in keys if key is not None}


def poem_score_defaults(scores_by_stanza, stanza_count):
    labels_by_length = {}
    for results in scores_by_stanza:
        if not results:
            continue
        stanza_length = score_stanza_length(results[0])
        labels = labels_by_length.setdefault(stanza_length, set())
        for result in results:
            labels.update(score_score_keys(result))
    return {
        stanza_length: 1 / (stanza_count + len(labels))
        for stanza_length, labels in labels_by_length.items()
    }


def poem_stanza_scores(outputs_by_stanza, scores_by_stanza, stanza_count):
    totals = {}
    for outputs in outputs_by_stanza:
        stanza_keys = set()
        for output in outputs:
            stanza_keys.update(output_score_keys(output))
        for key in stanza_keys:
            totals[key] = totals.get(key, 0) + 1
    scores = {
        key: total / stanza_count
        for key, total in totals.items()
    }
    scores[POEM_SCORE_DEFAULTS_KEY] = poem_score_defaults(
        scores_by_stanza,
        stanza_count,
    )
    return scores


def second_round_score(result, poem_scores):
    poem_score = poem_score_for(
        stanza_candidate_key(result),
        poem_scores,
        score_stanza_length(result),
    )
    return average_available(result["score"], poem_score)


def annotate_stanza_types(poem_data, stanza_patterns):
    stanza_score_rows = []
    if not stanza_patterns:
        return stanza_score_rows

    stanza_scores = []
    for stanza_n, stanza in get_stanzas(poem_data).items():
        results = [
            score_stanza_entry(stanza, entry)
            for entry in stanza_patterns
        ]
        results = [result for result in results if result is not None]
        if not results:
            continue
        stanza_scores.append((stanza_n, stanza, results))

    if not stanza_scores:
        return stanza_score_rows

    first_round_winners_by_stanza = [
        tied_max(
            results,
            key=lambda result: result["score"],
        )
        for _, _, results in stanza_scores
    ]
    first_round_outputs_by_stanza = [
        [
            resolve_stanza_output(results, winner)
            for winner in winners
        ]
        for (_, _, results), winners in zip(stanza_scores, first_round_winners_by_stanza)
    ]
    poem_scores = poem_stanza_scores(
        first_round_outputs_by_stanza,
        [results for _, _, results in stanza_scores],
        len(stanza_scores),
    )

    for stanza_n, stanza, results in stanza_scores:
        winner = max(
            results,
            key=lambda result: second_round_score(result, poem_scores),
        )
        output = resolve_stanza_output(
            results,
            winner,
            poem_scores,
            adjust=True,
        )
        winner = output["winner"]

        for result in results:
            entry = result["entry"]
            stanza_type = entry["stanza_type"]
            poem_score = poem_score_for(
                stanza_type,
                poem_scores,
                len(stanza),
            )
            stanza_score_rows.append(
                {
                    "stanza_n": stanza_n,
                    "verse_count": len(stanza),
                    "stanza_type": stanza_type,
                    "parent_type": entry.get("parent_type"),
                    "refines_type": entry.get("refines_type"),
                    "score": result["score"],
                    "score_poem": poem_score,
                    "score_with_poem": adjusted_score(
                        result["score"],
                        stanza_type,
                        poem_scores,
                        len(stanza),
                    ),
                    "pattern_similarity": result["pattern_similarity"],
                    "meter_similarity": result["meter_similarity"],
                    "rhyme_type_similarity": result["rhyme_type_similarity"],
                    "verse_type_similarity": result.get("verse_type_similarity"),
                    "subtype_selection_component": (
                        subtype_selection_component(result)
                        if entry.get("parent_type")
                        else None
                    ),
                    "subtype_selection_value": (
                        subtype_selection_value(result)
                        if entry.get("parent_type")
                        else None
                    ),
                    "subtype_selection_threshold": (
                        subtype_selection_threshold(result)
                        if entry.get("parent_type")
                        else None
                    ),
                    "observed_pattern": result["observed_pattern"],
                    "expected_pattern": result["expected_pattern"],
                    "observed_meter": result["observed_meter"],
                    "expected_meter": result["expected_meter"],
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
            data["stanza_type_score"] = output["stanza_type_score"]
            data["stanza_type_score_poem"] = output["stanza_type_score_poem"]
            data["stanza_subtype"] = output["stanza_subtype"]
            data["stanza_subtype_score"] = output["stanza_subtype_score"]
            data["stanza_subtype_score_poem"] = output["stanza_subtype_score_poem"]

    return stanza_score_rows
