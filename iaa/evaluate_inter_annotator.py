"""Pairwise inter-annotator agreement for rhyme-scheme annotations.

Rhyme letters are arbitrary cluster names, so agreement is calculated over
pairs of lines ("same rhyme" versus "different rhyme").
"""

import argparse
import csv
from collections import defaultdict
from itertools import combinations

from evaluate_rhyme_tags import TSV_QUOTECHAR, normalize_label, same_rhyme, safe_divide


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(
            handle, delimiter="\t", quotechar=TSV_QUOTECHAR, escapechar="\\"
        )
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        return reader.fieldnames, rows


def require_columns(fieldnames, path, columns):
    missing = [column for column in columns if column not in fieldnames]
    if missing:
        raise ValueError(
            f"{path} is missing {', '.join(repr(c) for c in missing)}. "
            f"Available columns: {', '.join(fieldnames)}"
        )


def group_rows(rows, group_column):
    groups = defaultdict(list)
    skipped = 0
    for row in rows:
        group = normalize_label(row[group_column])
        if group:
            groups[group].append(row)
        else:
            skipped += 1
    return groups, skipped


def align_rows(rows_1, rows_2, group_column, text_column):
    groups_1, blank_1 = group_rows(rows_1, group_column)
    groups_2, blank_2 = group_rows(rows_2, group_column)
    shared = sorted(set(groups_1) & set(groups_2))
    only_1 = set(groups_1) - set(groups_2)
    only_2 = set(groups_2) - set(groups_1)
    aligned = {}
    text_mismatches = 0
    for group in shared:
        left, right = groups_1[group], groups_2[group]
        if len(left) != len(right):
            raise ValueError(
                f"Cannot align group {group!r} by row order: annotator 1 has "
                f"{len(left)} rows and annotator 2 has {len(right)} rows."
            )
        aligned[group] = list(zip(left, right))
        text_mismatches += sum(
            normalize_label(a[text_column]) != normalize_label(b[text_column])
            for a, b in aligned[group]
        )
    audit = {
        "annotator_1_rows": len(rows_1),
        "annotator_2_rows": len(rows_2),
        "blank_group_rows_1": blank_1,
        "blank_group_rows_2": blank_2,
        "shared_groups": len(shared),
        "shared_lines": sum(map(len, aligned.values())),
        "annotator_1_only_groups": len(only_1),
        "annotator_1_only_lines": sum(len(groups_1[x]) for x in only_1),
        "annotator_2_only_groups": len(only_2),
        "annotator_2_only_lines": sum(len(groups_2[x]) for x in only_2),
        "aligned_text_mismatches": text_mismatches,
    }
    return aligned, audit


def cohen_kappa(yes_yes, yes_no, no_yes, no_no):
    total = yes_yes + yes_no + no_yes + no_no
    observed = safe_divide(yes_yes + no_no, total)
    a1_yes, a2_yes = yes_yes + yes_no, yes_yes + no_yes
    expected = safe_divide(
        a1_yes * a2_yes + (total - a1_yes) * (total - a2_yes), total * total
    )
    return safe_divide(observed - expected, 1 - expected)


def evaluate(aligned, column_1, column_2, text_column):
    yes_yes = yes_no = no_yes = no_no = perfect_groups = 0
    disagreements = []
    for group, lines in aligned.items():
        group_perfect = True
        indexed_pairs = combinations(enumerate(lines, start=1), 2)
        for (left_i, (left_1, left_2)), (right_i, (right_1, right_2)) in indexed_pairs:
            same_1 = same_rhyme(left_1[column_1], right_1[column_1])
            same_2 = same_rhyme(left_2[column_2], right_2[column_2])
            if same_1 and same_2:
                yes_yes += 1
            elif same_1:
                yes_no += 1
            elif same_2:
                no_yes += 1
            else:
                no_no += 1
            if same_1 != same_2:
                group_perfect = False
                disagreements.append(
                    {
                        "group": group,
                        "line_pair": f"{left_i}-{right_i}",
                        "left_text": left_1[text_column],
                        "right_text": right_1[text_column],
                        "annotator_1_pair": (
                            f"{normalize_label(left_1[column_1])}-"
                            f"{normalize_label(right_1[column_1])}"
                        ),
                        "annotator_2_pair": (
                            f"{normalize_label(left_2[column_2])}-"
                            f"{normalize_label(right_2[column_2])}"
                        ),
                        "annotator_1_same": int(same_1),
                        "annotator_2_same": int(same_2),
                    }
                )
        perfect_groups += group_perfect

    total = yes_yes + yes_no + no_yes + no_no
    union = yes_yes + yes_no + no_yes
    precision = safe_divide(yes_yes, yes_yes + no_yes)
    recall = safe_divide(yes_yes, yes_yes + yes_no)
    values = {
        "groups": len(aligned),
        "perfect_relation_groups": perfect_groups,
        "all_line_pairs": total,
        "union_rhyme_pairs": union,
        "same_same": yes_yes,
        "annotator_1_only_same": yes_no,
        "annotator_2_only_same": no_yes,
        "different_different": no_no,
        "pairwise_precision_2_vs_1": precision,
        "pairwise_recall_2_vs_1": recall,
        "pairwise_f1": safe_divide(2 * precision * recall, precision + recall),
        "pairwise_jaccard": safe_divide(yes_yes, union),
        "binary_pair_accuracy": safe_divide(yes_yes + no_no, total),
        "cohen_kappa": cohen_kappa(yes_yes, yes_no, no_yes, no_no),
        "perfect_relation_group_accuracy": safe_divide(perfect_groups, len(aligned)),
        "disagreements": len(disagreements),
    }
    return values, disagreements


def write_tsv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            quoting=csv.QUOTE_NONE,
            quotechar=TSV_QUOTECHAR,
            escapechar="\\",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pairwise inter-annotator agreement for rhyme labels."
    )
    parser.add_argument("annotator_1_path")
    parser.add_argument("annotator_2_path")
    parser.add_argument("--annotator-1-column", required=True)
    parser.add_argument("--annotator-2-column", required=True)
    parser.add_argument("--group-column", default="workId")
    parser.add_argument("--text-column", default="lines")
    parser.add_argument("--pairs-path", help="Optional disagreeing-pairs TSV.")
    parser.add_argument("--summary-path", help="Optional one-row summary TSV.")
    return parser.parse_args()


def main():
    args = parse_args()
    fields_1, rows_1 = read_rows(args.annotator_1_path)
    fields_2, rows_2 = read_rows(args.annotator_2_path)
    columns_1 = [args.annotator_1_column, args.group_column, args.text_column]
    columns_2 = [args.annotator_2_column, args.group_column, args.text_column]
    require_columns(fields_1, args.annotator_1_path, columns_1)
    require_columns(fields_2, args.annotator_2_path, columns_2)
    aligned, audit = align_rows(rows_1, rows_2, args.group_column, args.text_column)
    values, disagreements = evaluate(
        aligned, args.annotator_1_column, args.annotator_2_column, args.text_column
    )
    summary = {**audit, **values}
    for key, value in summary.items():
        print(f"{key}\t{value:.6f}" if isinstance(value, float) else f"{key}\t{value}")

    if args.pairs_path:
        pair_fields = [
            "group", "line_pair", "left_text", "right_text",
            "annotator_1_pair", "annotator_2_pair",
            "annotator_1_same", "annotator_2_same",
        ]
        write_tsv(args.pairs_path, pair_fields, disagreements)
        print(f"pairs_path\t{args.pairs_path}")
    if args.summary_path:
        write_tsv(args.summary_path, list(summary), [summary])
        print(f"summary_path\t{args.summary_path}")


if __name__ == "__main__":
    main()
