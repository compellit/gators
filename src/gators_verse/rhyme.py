"""Rhyme detection.

Each line's rhyme is taken from its last word, from the vowel trasgo marks as
stressed; a last word without a mark gets one on its first syllable, for rhyme
detection only (stress_final_word). Lines up to four lines apart rhyme when
their rhyme vowels match (assonance) and, for consonant rhyme, when the whole
ending matches. assign_rhymes() is the entry point.
"""

import regex as re

from .patterns import (
    average_available,
    entry_allowed_for_length,
    expand_pattern,
    expected_pair_data,
    get_stanzas,
    make_pattern,
    rhyme_type_similarity,
    stanza_meter_similarity,
    stanza_pattern_similarity,
)

SCORE_TIE_TOLERANCE = 1e-12


def rhyme_ending(transcription):
    """Return the rhyme ending of a transcribed line and its rhyme vowels.

    The ending runs from the stressed vowel of the last word to the end of the
    line; E and O (open vowels) count as e and o. The rhyme vowels are the
    stressed vowel and the last vowel.
    """
    accented_tail = stress_final_word(transcription).split('"')[-1]
    match = re.search(r"(([aeiouEO].*[A-Za-z])|[aeiouEO])", accented_tail)
    rhyme_tail = match.group(0) if match else ""
    rhyme_tail = rhyme_tail.replace("E", "e").replace("O", "o")
    vowels = re.findall(r"[aeiouEO]", rhyme_tail)
    if len(vowels) > 2:
        vowels = [vowels[0], vowels[-1]]
    return rhyme_tail, vowels


def stress_final_word(transcription):
    """Mark a stress on the last word of a transcribed line, for rhyme only.

    The rhyme is taken from the line's last word, from the vowel marked as
    stressed. Silaba leaves some words without a stress mark: function words
    ("que", "unha", "polo") and old spellings without their accent ("lua",
    "mais"). The rhyme would then start in an earlier word ("misteriosa lua":
    "o.sa lu.a" instead of "u.a"), so an unmarked last word gets a mark on its
    first syllable. This is only used to find where the rhyme starts; it is
    not a claim about the word's stress, and the transcription stored in the
    data is left as Silaba gives it.
    """
    if not isinstance(transcription, str):
        return transcription
    words = transcription.split(" ")
    for index in range(len(words) - 1, -1, -1):
        word = words[index]
        if re.search(r"[aeiouEO]", word):
            if '"' not in word:
                # Keep leading punctuation ("¡", "—") before the stress mark.
                words[index] = re.sub(r"^([^A-Za-z]*)", r'\1"', word, count=1)
            break
    return " ".join(words)


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


def poem_pattern_score(candidate, patterns, total_patterns):
    if total_patterns == 0:
        return 0

    candidate_windows = pattern_windows(candidate)
    candidate_score = 0

    for candidate_window in candidate_windows:
        window_score = 0

        for reference, count in patterns.items():
            if len(candidate_window) != len(reference):
                continue

            frequency = count / total_patterns
            window_score += pattern_similarity(candidate_window, reference) * frequency

        candidate_score += window_score

    return candidate_score / len(candidate_windows)


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


def predefined_pattern_score(stanza, observed_pattern, source_key, stanza_patterns):
    if not stanza_patterns:
        return None

    observed_length = len(stanza)
    observed_meter = [data["meter"] for _, data in stanza]
    observed_pairs = candidate_observed_pair_data(
        stanza,
        observed_pattern,
        source_key,
    )
    scores = []

    for entry in stanza_patterns:
        if not entry_allowed_for_length(entry, observed_length):
            continue

        meter_score = stanza_meter_similarity(observed_meter, entry)
        # detection_rhyme_kind overrides rhyme_kind when choosing between
        # the asonante and consonante candidates (not for stanza typing)
        detection_rhyme_kind = entry.get(
            "detection_rhyme_kind",
            entry.get("rhyme_kind"),
        )
        for pattern in entry["patterns"]:
            expected_pattern = expand_pattern(pattern, observed_length)
            pattern_score = stanza_pattern_similarity(
                observed_pattern,
                expected_pattern,
            )
            expected_pairs = expected_pair_data(
                expected_pattern,
                entry.get("rhymes"),
                detection_rhyme_kind,
            )
            rhyme_score = rhyme_type_similarity(
                observed_pairs,
                expected_pairs,
                detection_rhyme_kind,
            )
            components = [
                score
                for score in (pattern_score, meter_score, rhyme_score)
                if score is not None
            ]
            scores.append(sum(components) / len(components) if components else 1)

    return max(scores) if scores else None


def more_than_half_complete(groups):
    if not groups:
        return False

    complete_groups = [
        group
        for group in groups
        if all(value not in (None, False, "") for value in group.values())
    ]
    return len(complete_groups) > len(groups) / 2


def score_penalties(consonante_groups):
    if more_than_half_complete(consonante_groups):
        return True, False

    return False, True


def choose_final_from_patterns(
    poem_data,
    patterns,
    total_patterns,
    stanza_patterns,
    halve_asonante_score=False,
    halve_consonante_score=False,
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
        asonante_score_raw = poem_pattern_score(asonante_pattern, patterns, total_patterns)
        consonante_score_raw = poem_pattern_score(consonante_pattern, patterns, total_patterns)
        asonante_score = asonante_score_raw
        consonante_score = consonante_score_raw
        if halve_asonante_score:
            asonante_score /= 2
        if halve_consonante_score:
            consonante_score /= 2
        asonante_predefined_score = predefined_pattern_score(
            stanza,
            asonante_pattern,
            "asonante",
            stanza_patterns,
        )
        consonante_predefined_score = predefined_pattern_score(
            stanza,
            consonante_pattern,
            "consonante",
            stanza_patterns,
        )
        asonante_score = average_available(
            asonante_score,
            asonante_predefined_score,
        )
        consonante_score = average_available(
            consonante_score,
            consonante_predefined_score,
        )

        scores_tied = (
            abs(asonante_score - consonante_score)
            <= SCORE_TIE_TOLERANCE
        )

        if scores_tied and unresolved_lines_false_in_both(stanza):
            source_key = "asonante"
            score = asonante_score
        elif asonante_score == consonante_score == 0:
            source_key = "asonante"
            score = asonante_score
        elif consonante_score >= asonante_score:
            source_key = "consonante"
            score = consonante_score
        else:
            source_key = "asonante"
            score = asonante_score

        for _, data in stanza:
            data["asonante_pattern"] = asonante_pattern
            data["consonante_pattern"] = consonante_pattern
            data["asonante_score_raw"] = asonante_score_raw
            data["consonante_score_raw"] = consonante_score_raw
            data["asonante_predefined_score"] = asonante_predefined_score
            data["consonante_predefined_score"] = consonante_predefined_score
            data["asonante_score"] = asonante_score
            data["consonante_score"] = consonante_score
            data["chosen_source"] = source_key
            if data["final"] is False:
                data["final"] = data[source_key]
                data["final_score"] = score


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
        if data["final"] is None:
            data["letter"] = "-"
        else:
            data["letter"] = final_to_letter(final_numbers[verse])


def find_rhyme_pairs(poem_data):
    """Pairs of lines up to four lines apart with the same rhyme vowels.

    The value is the rhyme ending when the endings are identical (consonant
    rhyme), and False when only the vowels match (assonant rhyme).
    """
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
    return rhyme_pairs


def group_rhyme_pairs(rhyme_pairs):
    """Merge rhyme pairs that share a line into groups of rhyming lines."""
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

    return groups


def assign_rhymes(poem_data, stanza_patterns):
    """Set each line's rhyme class ("final") and rhyme letter ("letter").

    Lines are grouped by assonance; each group is split into consonant-rhyme
    subgroups. Where a stanza has lines that rhyme by assonance but not by
    consonance, the reading (assonant or consonant) is chosen by how well each
    fits the poem's other stanzas and the predefined stanza patterns.
    """
    groups = group_rhyme_pairs(find_rhyme_pairs(poem_data))
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
        stanza_patterns,
        *score_penalties(consonante_groups),
    )
    add_final_letters(poem_data, renumber_final(poem_data))
