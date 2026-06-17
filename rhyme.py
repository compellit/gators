import argparse
import csv
import json
import pandas as pd
import regex as re
import string
from pathlib import Path

TSV_QUOTECHAR = "\x07"
DEFAULT_INPUT_PATH = "/home/anxo/compellit/rhyme-gl-wk/data/gl-prepro-35k-silaba.tsv"
DEFAULT_RESULTS_PATH = "/home/anxo/compellit/rhyme-gl-wk/data/test_results_rhyme.tsv"
DEFAULT_STANZA_PATTERNS_PATH = "/home/anxo/compellit/rhyme-gl-wk/data/stanza_patterns.json"
MIXED_METRE_DOMINANCE_THRESHOLD = 0.7
PROBABILITY_TIE_TOLERANCE = 1e-12


parser = argparse.ArgumentParser()
parser.add_argument("--input-path", default=DEFAULT_INPUT_PATH)
parser.add_argument("--poem-column", default="poem_id")
parser.add_argument("--stanza-column", default="stanza_n")
parser.add_argument("--verse-column", default="verse_text")
parser.add_argument("--ph-column", default="phSilaba")
parser.add_argument("--rhyme-column", default="rhyme")
parser.add_argument("--syllable-column")
parser.add_argument("--stanza-patterns-path", default=DEFAULT_STANZA_PATTERNS_PATH)
parser.add_argument("--subtype-min-probability", type=float, default=0.8)
parser.add_argument("--results-path", default=DEFAULT_RESULTS_PATH)
parser.add_argument("--poem-ids")
args = parser.parse_args()


def id_key(value):
    value = str(value)
    return value[:-2] if value.endswith(".0") else value


def clean_output_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    if pd.isna(value):
        return ""

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def parse_syllable_value(value):
    if pd.isna(value):
        return None

    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def choose_syllable_column(df, requested):
    if requested:
        if requested not in df.columns:
            raise ValueError(
                f"Syllable column {requested!r} not found. "
                f"Available columns: {list(df.columns)}"
            )
        return requested

    for candidate in ("nbSyll", "nbSG", "syllables", "num_silabas"):
        if candidate in df.columns:
            return candidate

    return None


def load_stanza_patterns(path):
    if not path:
        return []

    pattern_path = Path(path)
    if not pattern_path.exists():
        return []

    with pattern_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        return data.get("entries", [])

    return data


poem_ids = set(id_key(value) for value in args.poem_ids.split(",")) if args.poem_ids else None

df = pd.read_csv(
    args.input_path,
    sep="\t",
    quotechar=TSV_QUOTECHAR,
    escapechar="\\",
)
df.columns = df.columns.str.strip()
syllable_column = choose_syllable_column(df, args.syllable_column)
stanza_patterns = load_stanza_patterns(args.stanza_patterns_path)
result_rows = []
for poem_id, poem in df.groupby(args.poem_column, sort=False):
    if poem_ids and id_key(poem_id) not in poem_ids:
        continue
    poem_data = {}
    verse_number = 0
    for stanza_n, stanza in poem.groupby(args.stanza_column, sort=False):
        for verse in stanza.itertuples():
            verse_number += 1
            accented_tail = getattr(verse, args.ph_column).split('"')[-1]
            match = re.search(r"(([aeiouEO].*[A-Za-z])|[aeiouEO])", accented_tail)
            rhyme_tail = match.group(0) if match else ""
            rhyme_tail = rhyme_tail.replace("E", "e").replace("O", "o")
            vowels = re.findall(r"[aeiouEO]", rhyme_tail)
            if len(vowels) > 2:
                vowels = [vowels[0], vowels[-1]]
            poem_data[verse_number] = {
                "rhyme_tail": rhyme_tail,
                "vowels": vowels,
                "stanza": stanza_n,
                "metre": (
                    parse_syllable_value(getattr(verse, syllable_column))
                    if syllable_column
                    else None
                ),
                "asonante": None,
                "consonante": None,
                "_asonante_key": None,
                "_consonante_key": None,
                "final": None,
                "final_probability": None,
                "asonante_pattern": None,
                "consonante_pattern": None,
                "asonante_probability_raw": None,
                "consonante_probability_raw": None,
                "asonante_predefined_probability": None,
                "consonante_predefined_probability": None,
                "asonante_probability": None,
                "consonante_probability": None,
                "chosen_source": None,
                "observed_pattern": None,
                "expected_pattern": None,
                "observed_metre": None,
                "expected_metre": None,
                "expected_rhymes": None,
                "observed_rhyme_pairs": None,
                "expected_rhyme_pairs": None,
                "pattern_similarity": None,
                "metre_similarity": None,
                "rhyme_type_similarity": None,
                "stanza_type": None,
                "stanza_type_probability": None,
                "stanza_type_probability_poem": None,
                "stanza_subtype": None,
                "stanza_subtype_probability": None,
                "stanza_subtype_probability_poem": None,
                "letter": None,
            }

    rhyme_pairs = {}
    for verse, data in poem_data.items():
        rhyme_tail = data["rhyme_tail"]
        vowels = data["vowels"]
        for offset in range(1, min(5, len(poem_data) - verse + 1)):
            comparison = poem_data[verse + offset]
            if comparison["vowels"] == vowels:
                pair_rhyme = (
                    comparison["rhyme_tail"]
                    if comparison["rhyme_tail"] == rhyme_tail
                    else False
                )
                rhyme_pairs[(verse, verse + offset)] = pair_rhyme

    def keep_rhyme(existing, new):
        if existing in (None, False, ""):
            return new
        if new in (None, False, ""):
            return existing
        return existing

    def make_subgroups(groups, max_gap=4):
        subgroups = []

        for group in groups:
            group_subgroups = []
            grouped_verses = set()

            by_rhyme = {}
            for verse, rhyme in group.items():
                if rhyme in (None, ""):
                    continue
                by_rhyme.setdefault(rhyme, []).append(verse)

            for rhyme, verses in by_rhyme.items():
                current = {}
                previous_verse = None

                for verse in sorted(verses):
                    if previous_verse is None or verse - previous_verse <= max_gap:
                        current[verse] = rhyme
                    else:
                        if len(current) > 1:
                            group_subgroups.append(current)
                            grouped_verses.update(current)
                        current = {verse: rhyme}

                    previous_verse = verse

                if len(current) > 1:
                    group_subgroups.append(current)
                    grouped_verses.update(current)

            if grouped_verses == set(group):
                subgroups.extend(group_subgroups)
            else:
                subgroups.append(group)

        return subgroups

    def label_groups(poem_data, groups, key, first_label):
        label = first_label
        for group in groups:
            for verse, value in group.items():
                poem_data[verse][key] = label
                poem_data[verse][f"_{key}_key"] = value
            label += 1
        return label

    def clear_asonante_when_same_as_consonante(poem_data, groups, consonante_groups):
        consonante_sets = {frozenset(group) for group in consonante_groups}
        for group in groups:
            if frozenset(group) in consonante_sets:
                for verse in group:
                    poem_data[verse]["asonante"] = False

    def set_final_from_consonante(poem_data):
        for data in poem_data.values():
            if data["asonante"] is False:
                data["final"] = data["consonante"]
            elif data["asonante"] is None and data["consonante"] is None:
                data["final"] = None
            else:
                data["final"] = False

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

    def count_stanza_patterns(poem_data):
        patterns = {}
        stanzas = get_stanzas(poem_data)
        total_patterns = 0

        for stanza in stanzas.values():
            finals = [data["final"] for _, data in stanza]
            final_windows = pattern_windows(finals)
            total_patterns += len(final_windows)

            for final_window in final_windows:
                if any(final is False for final in final_window):
                    continue

                pattern_window = make_pattern(final_window)
                patterns[pattern_window] = patterns.get(pattern_window, 0) + 1

        return patterns, total_patterns

    def candidate_pattern(stanza, source_key):
        values = []

        for _, data in stanza:
            if data["final"] is False:
                values.append(data[source_key])
            else:
                values.append(data["final"])

        return make_pattern(values)

    def pattern_similarity(candidate, reference):
        matches = 0
        compared = 0

        for left_index in range(len(candidate)):
            for right_index in range(left_index + 1, len(candidate)):
                if "-" in (reference[left_index], reference[right_index]):
                    continue

                compared += 1
                candidate_matches = candidate[left_index] == candidate[right_index]
                reference_matches = reference[left_index] == reference[right_index]
                if candidate_matches == reference_matches:
                    matches += 1

        if compared == 0:
            return 0
        return matches / compared

    def pattern_windows(pattern, max_stanza_size=8, window_size=6):
        if len(pattern) <= max_stanza_size:
            return [pattern]

        return [
            pattern[start:start + window_size]
            for start in range(0, len(pattern), window_size)
        ]

    def pattern_probability(candidate, patterns, total_patterns):
        if total_patterns == 0:
            return 0

        candidate_windows = pattern_windows(candidate)
        candidate_score = 0

        for candidate_window in candidate_windows:
            window_score = 0

            for reference, count in patterns.items():
                if len(candidate_window) != len(reference):
                    continue

                pattern_probability = count / total_patterns
                window_score += pattern_similarity(candidate_window, reference) * pattern_probability

            candidate_score += window_score

        return candidate_score / len(candidate_windows)

    def expand_pattern(pattern, observed_length):
        pattern = pattern.replace(" ", "")
        if pattern == "*":
            return pattern
        if len(pattern) == observed_length:
            return pattern
        repeats = observed_length // len(pattern)
        return pattern * repeats

    def entry_allowed_for_length(entry, observed_length):
        if entry.get("repeat_pattern"):
            pattern_length = len(entry["patterns"][0].replace(" ", ""))
            return (
                observed_length >= entry.get("min_verses", pattern_length)
                and observed_length % entry.get("length_multiple", pattern_length) == 0
            )

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

    def score_stanza_entry(stanza, entry):
        observed_length = len(stanza)
        if not entry_allowed_for_length(entry, observed_length):
            return None

        finals = [data["final"] for _, data in stanza]
        observed_pattern = make_pattern(finals)
        observed_metre = [data["metre"] for _, data in stanza]
        observed_pairs = observed_pair_data(stanza, observed_pattern)
        metre_score = stanza_metre_similarity(observed_metre, entry)

        best = None
        for pattern in entry["patterns"]:
            expected_pattern = expand_pattern(pattern, observed_length)
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
            components = [
                score
                for score in (pattern_score, metre_score, rhyme_score)
                if score is not None
            ]
            probability = sum(components) / len(components) if components else 1
            result = {
                "entry": entry,
                "probability": probability,
                "observed_pattern": observed_pattern,
                "expected_pattern": expected_pattern,
                "observed_metre": observed_metre,
                "expected_metre": entry.get("metre"),
                "expected_rhymes": entry.get("rhymes") or entry.get("rhyme_kind"),
                "observed_rhyme_pairs": format_pairs(observed_pairs),
                "expected_rhyme_pairs": format_pairs(expected_pairs),
                "pattern_similarity": pattern_score,
                "metre_similarity": metre_score,
                "rhyme_type_similarity": rhyme_score,
            }
            if best is None or result["probability"] > best["probability"]:
                best = result

        return best

    def candidate_pair_type(stanza, left_index, right_index, source_key):
        if source_key == "asonante":
            return "asonante"

        left = stanza[left_index][1]
        right = stanza[right_index][1]
        if left["rhyme_tail"] == right["rhyme_tail"] and left["rhyme_tail"] not in (None, False, ""):
            return "consonante"
        return "asonante"

    def candidate_observed_pair_data(stanza, observed_pattern, source_key):
        pairs = {}

        for left_index in range(len(stanza)):
            for right_index in range(left_index + 1, len(stanza)):
                if observed_pattern[left_index] == "-":
                    continue
                if observed_pattern[left_index] != observed_pattern[right_index]:
                    continue

                pairs[(left_index, right_index)] = candidate_pair_type(
                    stanza,
                    left_index,
                    right_index,
                    source_key,
                )

        return pairs

    def predefined_pattern_probability(stanza, observed_pattern, source_key):
        if not stanza_patterns:
            return None

        observed_length = len(stanza)
        observed_metre = [data["metre"] for _, data in stanza]
        observed_pairs = candidate_observed_pair_data(
            stanza,
            observed_pattern,
            source_key,
        )
        scores = []

        for entry in stanza_patterns:
            if not entry_allowed_for_length(entry, observed_length):
                continue

            metre_score = stanza_metre_similarity(observed_metre, entry)
            for pattern in entry["patterns"]:
                expected_pattern = expand_pattern(pattern, observed_length)
                pattern_score = stanza_pattern_similarity(
                    observed_pattern,
                    expected_pattern,
                )
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
                    for score in (pattern_score, metre_score, rhyme_score)
                    if score is not None
                ]
                scores.append(sum(components) / len(components) if components else 1)

        return max(scores) if scores else None

    def average_available(*scores):
        scores = [score for score in scores if score is not None]
        return sum(scores) / len(scores) if scores else None

    def tied_max(items, key):
        keyed_items = [(item, key(item)) for item in items]
        best_value = max(value for _, value in keyed_items)
        return [
            item
            for item, value in keyed_items
            if abs(value - best_value) <= PROBABILITY_TIE_TOLERANCE
        ]

    def choose_subtype(parent_type, scores):
        candidates = [
            score
            for score in scores
            if score["entry"].get("parent_type") == parent_type
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda score: score["probability"])
        if best["probability"] >= args.subtype_min_probability:
            return best
        return None

    def choose_refinement(stanza_type, scores):
        candidates = [
            score
            for score in scores
            if score["entry"].get("refines_type") == stanza_type
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda score: score["probability"])
        if best["probability"] >= args.subtype_min_probability:
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

    def adjusted_probability(probability, key, poem_probabilities):
        if key in poem_probabilities:
            return average_available(probability, poem_probabilities[key])
        return probability

    def resolve_stanza_output(scores, winner, poem_probabilities=None, adjust=False):
        poem_probabilities = poem_probabilities or {}
        entry = winner["entry"]
        stanza_type = entry["stanza_type"]
        stanza_probability = winner["probability"]
        stanza_type_probability_poem = poem_probabilities.get(stanza_type)
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
            stanza_type_probability_poem = poem_probabilities.get(stanza_type)
            stanza_subtype = entry["stanza_type"]
            stanza_subtype_probability = winner["probability"]
            stanza_subtype_probability_poem = poem_probabilities.get(stanza_subtype)
        else:
            subtype = choose_subtype(stanza_type, scores)
            if subtype:
                stanza_subtype = subtype["entry"]["stanza_type"]
                stanza_subtype_probability = subtype["probability"]
                stanza_subtype_probability_poem = poem_probabilities.get(stanza_subtype)

        refinement = choose_refinement(stanza_type, scores)
        if refinement:
            winner = refinement
            entry = winner["entry"]
            stanza_type = entry["stanza_type"]
            stanza_probability = winner["probability"]
            stanza_type_probability_poem = poem_probabilities.get(stanza_type)
            stanza_subtype = None
            stanza_subtype_probability = None
            stanza_subtype_probability_poem = None

        if adjust:
            stanza_probability = adjusted_probability(
                stanza_probability,
                stanza_type,
                poem_probabilities,
            )
            if stanza_subtype:
                stanza_subtype_probability = adjusted_probability(
                    stanza_subtype_probability,
                    stanza_subtype,
                    poem_probabilities,
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

    def output_key_and_probability(output):
        if output["stanza_subtype"]:
            return output["stanza_subtype"], output["stanza_subtype_probability"]
        return output["stanza_type"], output["stanza_type_probability"]

    def poem_stanza_probabilities(outputs_by_stanza, stanza_count):
        totals = {}
        for outputs in outputs_by_stanza:
            stanza_totals = {}
            for output in outputs:
                key, probability = output_key_and_probability(output)
                if key is None or probability is None:
                    continue
                stanza_totals[key] = max(stanza_totals.get(key, probability), probability)
            for key, probability in stanza_totals.items():
                totals[key] = totals.get(key, 0) + probability
        return {
            key: total / stanza_count
            for key, total in totals.items()
        }

    def second_round_score(score, poem_probabilities):
        poem_probability = poem_probabilities.get(stanza_candidate_key(score), 0)
        return average_available(score["probability"], poem_probability)

    def add_probability(mapping, key, probability):
        if key is None or probability is None:
            return
        mapping[key] = max(mapping.get(key, probability), probability)

    def compact_labels(labels):
        labels = list(labels)
        if not labels:
            return None
        if len(labels) == 1:
            return labels[0]
        return labels

    def compact_probabilities(probabilities):
        if not probabilities:
            return None
        if len(probabilities) == 1:
            return next(iter(probabilities.values()))
        return probabilities

    def merge_stanza_outputs(outputs):
        stanza_type_probabilities = {}
        stanza_type_poem_probabilities = {}
        stanza_subtype_probabilities = {}
        stanza_subtype_poem_probabilities = {}

        for output in outputs:
            add_probability(
                stanza_type_probabilities,
                output["stanza_type"],
                output["stanza_type_probability"],
            )
            add_probability(
                stanza_type_poem_probabilities,
                output["stanza_type"],
                output["stanza_type_probability_poem"],
            )
            add_probability(
                stanza_subtype_probabilities,
                output["stanza_subtype"],
                output["stanza_subtype_probability"],
            )
            add_probability(
                stanza_subtype_poem_probabilities,
                output["stanza_subtype"],
                output["stanza_subtype_probability_poem"],
            )

        return {
            "winner": outputs[0]["winner"],
            "stanza_type": compact_labels(stanza_type_probabilities),
            "stanza_type_probability": compact_probabilities(stanza_type_probabilities),
            "stanza_type_probability_poem": compact_probabilities(stanza_type_poem_probabilities),
            "stanza_subtype": compact_labels(stanza_subtype_probabilities),
            "stanza_subtype_probability": compact_probabilities(stanza_subtype_probabilities),
            "stanza_subtype_probability_poem": compact_probabilities(stanza_subtype_poem_probabilities),
        }

    def annotate_stanza_types(poem_data):
        if not stanza_patterns:
            return

        stanza_scores = []
        for stanza in get_stanzas(poem_data).values():
            scores = [
                score_stanza_entry(stanza, entry)
                for entry in stanza_patterns
            ]
            scores = [score for score in scores if score is not None]
            if not scores:
                continue
            stanza_scores.append((stanza, scores))

        if not stanza_scores:
            return

        first_round_winners_by_stanza = [
            tied_max(
                scores,
                key=lambda score: score["probability"],
            )
            for _, scores in stanza_scores
        ]
        first_round_outputs_by_stanza = [
            [
                resolve_stanza_output(scores, winner)
                for winner in winners
            ]
            for (_, scores), winners in zip(stanza_scores, first_round_winners_by_stanza)
        ]
        poem_probabilities = poem_stanza_probabilities(
            first_round_outputs_by_stanza,
            len(stanza_scores),
        )

        for stanza, scores in stanza_scores:
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

            for _, data in stanza:
                data["observed_pattern"] = winner["observed_pattern"]
                data["expected_pattern"] = winner["expected_pattern"]
                data["observed_metre"] = winner["observed_metre"]
                data["expected_metre"] = winner["expected_metre"]
                data["expected_rhymes"] = winner["expected_rhymes"]
                data["observed_rhyme_pairs"] = winner["observed_rhyme_pairs"]
                data["expected_rhyme_pairs"] = winner["expected_rhyme_pairs"]
                data["pattern_similarity"] = winner["pattern_similarity"]
                data["metre_similarity"] = winner["metre_similarity"]
                data["rhyme_type_similarity"] = winner["rhyme_type_similarity"]
                data["stanza_type"] = output["stanza_type"]
                data["stanza_type_probability"] = output["stanza_type_probability"]
                data["stanza_type_probability_poem"] = output["stanza_type_probability_poem"]
                data["stanza_subtype"] = output["stanza_subtype"]
                data["stanza_subtype_probability"] = output["stanza_subtype_probability"]
                data["stanza_subtype_probability_poem"] = output["stanza_subtype_probability_poem"]

    def more_than_half_complete(groups):
        if not groups:
            return False

        complete_groups = [
            group
            for group in groups
            if all(value not in (None, False, "") for value in group.values())
        ]
        return len(complete_groups) > len(groups) / 2

    def probability_penalties(consonante_groups):
        if more_than_half_complete(consonante_groups):
            return True, False

        return False, True

    def choose_final_from_patterns(
        poem_data,
        patterns,
        total_patterns,
        halve_asonante_probability=False,
        halve_consonante_probability=False,
    ):
        stanzas = get_stanzas(poem_data)

        def unresolved_lines_false_in_both(stanza):
            unresolved = [
                data
                for _, data in stanza
                if data["final"] is False
            ]
            return (
                unresolved
                and all(
                    data["_asonante_key"] is False and data["_consonante_key"] is False
                    for data in unresolved
                )
            )

        for stanza in stanzas.values():
            if not any(data["final"] is False for _, data in stanza):
                continue

            asonante_pattern = candidate_pattern(stanza, "asonante")
            consonante_pattern = candidate_pattern(stanza, "consonante")
            asonante_probability_raw = pattern_probability(asonante_pattern, patterns, total_patterns)
            consonante_probability_raw = pattern_probability(consonante_pattern, patterns, total_patterns)
            asonante_probability = asonante_probability_raw
            consonante_probability = consonante_probability_raw
            if halve_asonante_probability:
                asonante_probability /= 2
            if halve_consonante_probability:
                consonante_probability /= 2
            asonante_predefined_probability = predefined_pattern_probability(
                stanza,
                asonante_pattern,
                "asonante",
            )
            consonante_predefined_probability = predefined_pattern_probability(
                stanza,
                consonante_pattern,
                "consonante",
            )
            asonante_probability = average_available(
                asonante_probability,
                asonante_predefined_probability,
            )
            consonante_probability = average_available(
                consonante_probability,
                consonante_predefined_probability,
            )

            probabilities_tied = (
                abs(asonante_probability - consonante_probability)
                <= PROBABILITY_TIE_TOLERANCE
            )

            if probabilities_tied and unresolved_lines_false_in_both(stanza):
                source_key = "asonante"
                probability = asonante_probability
            elif asonante_probability == consonante_probability == 0:
                source_key = "asonante"
                probability = asonante_probability
            elif consonante_probability >= asonante_probability:
                source_key = "consonante"
                probability = consonante_probability
            else:
                source_key = "asonante"
                probability = asonante_probability

            for _, data in stanza:
                data["asonante_pattern"] = asonante_pattern
                data["consonante_pattern"] = consonante_pattern
                data["asonante_probability_raw"] = asonante_probability_raw
                data["consonante_probability_raw"] = consonante_probability_raw
                data["asonante_predefined_probability"] = asonante_predefined_probability
                data["consonante_predefined_probability"] = consonante_predefined_probability
                data["asonante_probability"] = asonante_probability
                data["consonante_probability"] = consonante_probability
                data["chosen_source"] = source_key
                if data["final"] is False:
                    data["final"] = data[source_key]
                    data["final_probability"] = probability

    def renumber_final(poem_data, max_gap=4):
        labels = {}
        previous_verse_by_final = {}
        next_label = 1
        final_numbers = {}

        for verse in sorted(poem_data):
            final = poem_data[verse]["final"]
            if final in (None, False):
                continue

            if final not in labels or verse - previous_verse_by_final[final] > max_gap:
                labels[final] = next_label
                next_label += 1

            previous_verse_by_final[final] = verse
            final_numbers[verse] = labels[final]

        return final_numbers

    def final_to_letter(final):
        alphabet = "abcdefghijklmnñopqrstuvwxyz"
        base = len(alphabet)
        index = final - 1

        for length in range(1, final + 1):
            count = base ** length
            if index < count:
                letters = []
                for _ in range(length):
                    letters.append(alphabet[index % base])
                    index //= base
                return "".join(reversed(letters))
            index -= count

    def add_final_letters(poem_data, final_numbers):
        for verse, data in poem_data.items():
            final = data["final"]
            if final is None:
                data["final"] = "-"
                data["letter"] = "-"
            else:
                data["letter"] = final_to_letter(final_numbers[verse])

    groups = []

    for verse_pair, value in rhyme_pairs.items():
        first_verse = verse_pair[0]
        second_verse = verse_pair[1]
        matching_groups = [
            group
            for group in groups
            if first_verse in group or second_verse in group
        ]

        if not matching_groups:
            groups.append({first_verse: value, second_verse: value})
        else:
            merged = {}
            for group in matching_groups:
                for verse, rhyme in group.items():
                    merged[verse] = keep_rhyme(merged.get(verse), rhyme)
                groups.remove(group)

            merged[first_verse] = keep_rhyme(merged.get(first_verse), value)
            merged[second_verse] = keep_rhyme(merged.get(second_verse), value)
            groups.append(merged)

    consonante_groups = make_subgroups(groups)

    next_label = label_groups(poem_data, groups, "asonante", 1)
    label_groups(poem_data, consonante_groups, "consonante", next_label)
    clear_asonante_when_same_as_consonante(poem_data, groups, consonante_groups)
    set_final_from_consonante(poem_data)
    patterns, total_patterns = count_stanza_patterns(poem_data)
    choose_final_from_patterns(
        poem_data,
        patterns,
        total_patterns,
        *probability_penalties(consonante_groups),
    )
    annotate_stanza_types(poem_data)
    final_numbers = renumber_final(poem_data)
    add_final_letters(poem_data, final_numbers)
    verse_number = 1
    if args.rhyme_column and args.rhyme_column not in df.columns:
        print(f"Rhyme column {args.rhyme_column!r} not found. Available columns: {list(df.columns)}")
        args.rhyme_column = None

    for stanza_n, stanza in poem.groupby(args.stanza_column, sort=False):
        for _, verse in stanza.iterrows():
            rhyme = verse[args.rhyme_column] if args.rhyme_column else ""
            poem_values = poem_data[verse_number].copy()
            poem_values.pop("stanza")
            poem_values.pop("_asonante_key")
            poem_values.pop("_consonante_key")
            poem_values["rima"] = poem_values.pop("rhyme_tail")
            poem_values["vogais"] = ",".join(poem_values.pop("vowels"))
            letter = poem_values.pop("letter")
            stanza_type = poem_values.pop("stanza_type")
            stanza_type_probability = poem_values.pop("stanza_type_probability")
            stanza_type_probability_poem = poem_values.pop("stanza_type_probability_poem")
            stanza_subtype = poem_values.pop("stanza_subtype")
            stanza_subtype_probability = poem_values.pop("stanza_subtype_probability")
            stanza_subtype_probability_poem = poem_values.pop("stanza_subtype_probability_poem")
            extra_columns = {}
            if "prepro" in df.columns:
                extra_columns["prepro"] = verse["prepro"]
            result_rows.append(
                {
                    args.poem_column: poem_id,
                    args.stanza_column: stanza_n,
                    "verse_n": verse_number,
                    "stanza_type": stanza_type,
                    "stanza_type_probability": stanza_type_probability,
                    "stanza_type_probability_poem": stanza_type_probability_poem,
                    "stanza_subtype": stanza_subtype,
                    "stanza_subtype_probability": stanza_subtype_probability,
                    "stanza_subtype_probability_poem": stanza_subtype_probability_poem,
                    args.verse_column: verse[args.verse_column],
                    **extra_columns,
                    "letter": letter,
                    args.rhyme_column or "rhyme": rhyme,
                    **poem_values,
                }
            )
            result_rows[-1] = {
                key: clean_output_value(value)
                for key, value in result_rows[-1].items()
            }
            verse_number += 1

results = pd.DataFrame(result_rows).map(clean_output_value)
results.to_csv(
    args.results_path,
    sep="\t",
    index=False,
    quoting=csv.QUOTE_NONE,
    quotechar=TSV_QUOTECHAR,
    escapechar="\\",
)
print(f"Wrote {len(result_rows)} rows to {args.results_path}")
    
