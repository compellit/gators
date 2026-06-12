import argparse
import csv
import pandas as pd
import regex as re
import string

TSV_QUOTECHAR = "\x07"
DEFAULT_INPUT_PATH = "/home/anxo/compellit/rhyme-gl-wk/data/gl-prepro-35k-silaba.tsv"
DEFAULT_RESULTS_PATH = "/home/anxo/compellit/rhyme-gl-wk/data/test_results_rhyme.tsv"


parser = argparse.ArgumentParser()
parser.add_argument("--input-path", default=DEFAULT_INPUT_PATH)
parser.add_argument("--poem-column", default="poem_id")
parser.add_argument("--stanza-column", default="stanza_n")
parser.add_argument("--verse-column", default="verse_text")
parser.add_argument("--ph-column", default="phSilaba")
parser.add_argument("--rhyme-column", default="rhyme")
parser.add_argument("--results-path", default=DEFAULT_RESULTS_PATH)
parser.add_argument("--poem-ids")
args = parser.parse_args()


def id_key(value):
    value = str(value)
    return value[:-2] if value.endswith(".0") else value


def clean_output_value(value):
    if pd.isna(value):
        return ""

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


poem_ids = set(id_key(value) for value in args.poem_ids.split(",")) if args.poem_ids else None

df = pd.read_csv(
    args.input_path,
    sep="\t",
    quotechar=TSV_QUOTECHAR,
    escapechar="\\",
)
df.columns = df.columns.str.strip()
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
                "asonante": None,
                "consonante": None,
                "final": None,
                "final_probability": None,
                "asonante_pattern": None,
                "consonante_pattern": None,
                "asonante_probability_raw": None,
                "consonante_probability_raw": None,
                "asonante_probability": None,
                "consonante_probability": None,
                "chosen_source": None,
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
            for verse in group:
                poem_data[verse][key] = label
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

        for value in values:
            if value is None:
                pattern.append("-")
            elif value not in labels:
                labels[value] = string.ascii_lowercase[len(labels)]
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

            if asonante_probability == consonante_probability == 0:
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
            poem_values["rima"] = poem_values.pop("rhyme_tail")
            poem_values["vogais"] = ",".join(poem_values.pop("vowels"))
            letter = poem_values.pop("letter")
            extra_columns = {}
            if "prepro" in df.columns:
                extra_columns["prepro"] = verse["prepro"]
            result_rows.append(
                {
                    args.poem_column: poem_id,
                    args.stanza_column: stanza_n,
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
    
