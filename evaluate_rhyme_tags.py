import argparse
import csv
from pathlib import Path
from itertools import combinations


TSV_QUOTECHAR = "\x07"
NO_RHYME_VALUES = {"", "-", "0", "nan", "none", "null"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate rhyme labels with pairwise same-rhyme comparisons."
    )
    parser.add_argument("input_path")
    parser.add_argument("--pred-column", default="letter")
    parser.add_argument(
        "--gold-column",
        help="Gold label column. Defaults to gold, or rhyme if gold is absent.",
    )
    parser.add_argument(
        "--group-column",
        action="append",
        dest="group_columns",
        help=(
            "Column used to keep pairwise comparisons inside each poem/group. "
            "Can be repeated. Defaults to workId, poem_id, or all rows."
        ),
    )
    parser.add_argument(
        "--pairs-path",
        help="Optional TSV path for one row per pairwise comparison.",
    )
    parser.add_argument(
        "--summary-path",
        help=(
            "Optional TSV path for summary metrics. Defaults to summary.tsv "
            "beside --pairs-path, or in the current directory if no --pairs-path is used."
        ),
    )
    parser.add_argument(
        "--stanzas-path",
        help=(
            "Optional TSV path for one row per stanza-type comparison. Defaults "
            "to stanzas.tsv beside --pairs-path, or in the current directory if "
            "no --pairs-path is used. Written only when stanza evaluation is available."
        ),
    )
    parser.add_argument(
        "--line-id-column",
        default=None,
        help="Optional line identifier column to include in --pairs-path output.",
    )
    parser.add_argument(
        "--text-column",
        help=(
            "Optional verse text column to include in --pairs-path output. "
            "Defaults to lines, verse_text, or prepro when available."
        ),
    )
    parser.add_argument(
        "--stanza-gold-column",
        help=(
            "Gold narrow stanza-type column. Defaults to stanzaTypeNarrow "
            "when present."
        ),
    )
    parser.add_argument(
        "--stanza-pred-column",
        help=(
            "Predicted narrow stanza-type column. By default, uses stanza_subtype "
            "when populated and falls back to stanza_type."
        ),
    )
    parser.add_argument(
        "--stanza-column",
        help="Stanza identifier column. Defaults to stanzaNbr or stanza_n.",
    )
    return parser.parse_args()


def normalize_label(value):
    return str(value if value is not None else "").strip().lower()


def is_rhyme_label(value):
    return normalize_label(value) not in NO_RHYME_VALUES


def same_rhyme(left, right):
    left = normalize_label(left)
    right = normalize_label(right)
    return left == right and is_rhyme_label(left)


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
            quotechar=TSV_QUOTECHAR,
            escapechar="\\",
        )
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        return reader.fieldnames, rows


def choose_group_columns(fieldnames, requested):
    if requested:
        missing = [column for column in requested if column not in fieldnames]
        if missing:
            raise ValueError(
                f"Missing group column(s): {', '.join(missing)}. "
                f"Available columns: {', '.join(fieldnames)}"
            )
        return requested

    for candidate in ("workId", "poem_id"):
        if candidate in fieldnames:
            return [candidate]

    return []


def choose_gold_column(fieldnames, requested):
    if requested:
        if requested not in fieldnames:
            raise ValueError(
                f"Missing column {requested!r}. Available columns: {', '.join(fieldnames)}"
            )
        return requested

    for candidate in ("gold", "rhyme"):
        if candidate in fieldnames:
            return candidate

    raise ValueError(
        "Could not infer a gold column. Pass --gold-column. "
        f"Available columns: {', '.join(fieldnames)}"
    )


def choose_text_column(fieldnames, requested):
    if requested:
        if requested not in fieldnames:
            raise ValueError(
                f"Missing column {requested!r}. Available columns: {', '.join(fieldnames)}"
            )
        return requested

    for candidate in ("lines", "verse_text", "prepro"):
        if candidate in fieldnames:
            return candidate

    return None


def grouped_rows(rows, group_columns):
    groups = {}
    for row_index, row in enumerate(rows, start=1):
        key = tuple(row[column] for column in group_columns) if group_columns else ("__all__",)
        groups.setdefault(key, []).append((row_index, row))
    return groups


def empty_counts():
    return {
        "tp": 0,
        "fp": 0,
        "tn": 0,
        "fn": 0,
        "pairs": 0,
        "line_matches": 0,
        "lines": 0,
        "perfect_groups": 0,
        "groups": 0,
    }


def add_pair_counts(counts, pred_same, gold_same):
    counts["pairs"] += 1
    if pred_same and gold_same:
        counts["tp"] += 1
    elif pred_same and not gold_same:
        counts["fp"] += 1
    elif not pred_same and gold_same:
        counts["fn"] += 1
    else:
        counts["tn"] += 1


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def metrics(counts):
    precision = safe_divide(counts["tp"], counts["tp"] + counts["fp"])
    recall = safe_divide(counts["tp"], counts["tp"] + counts["fn"])
    f1 = safe_divide(2 * precision * recall, precision + recall)
    return {
        "groups": counts["groups"],
        "lines": counts["lines"],
        "pairs": counts["pairs"],
        "tp": counts["tp"],
        "fp": counts["fp"],
        "fn": counts["fn"],
        "tn": counts["tn"],
        "accuracy": safe_divide(counts["tp"] + counts["tn"], counts["pairs"]),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "line_accuracy": safe_divide(counts["line_matches"], counts["lines"]),
        "perfect_group_accuracy": safe_divide(counts["perfect_groups"], counts["groups"]),
    }


def choose_stanza_column(fieldnames, requested):
    if requested:
        if requested not in fieldnames:
            raise ValueError(
                f"Missing stanza column {requested!r}. "
                f"Available columns: {', '.join(fieldnames)}"
            )
        return requested

    for candidate in ("stanzaNbr", "stanza_n"):
        if candidate in fieldnames:
            return candidate

    return None


def evaluate_stanza_types(
    rows,
    group_columns,
    stanza_column,
    gold_column,
    pred_column=None,
):
    stanzas = {}
    for row in rows:
        key = tuple(row[column] for column in group_columns)
        key += (row[stanza_column],)
        stanzas.setdefault(key, []).append(row)

    total = 0
    correct = 0
    missing_predictions = 0
    stanza_rows = []
    for key, stanza in stanzas.items():
        gold = next(
            (
                normalize_label(row[gold_column])
                for row in stanza
                if normalize_label(row[gold_column])
            ),
            "",
        )
        if not is_rhyme_label(gold):
            continue

        pred_type = ""
        pred_subtype = ""
        if pred_column:
            pred = next(
                (
                    normalize_label(row[pred_column])
                    for row in stanza
                    if normalize_label(row[pred_column])
                ),
                "",
            )
        else:
            pred_type = next(
                (
                    normalize_label(row.get("stanza_type"))
                    for row in stanza
                    if normalize_label(row.get("stanza_type"))
                ),
                "",
            )
            pred_subtype = next(
                (
                    normalize_label(row.get("stanza_subtype"))
                    for row in stanza
                    if normalize_label(row.get("stanza_subtype"))
                ),
                "",
            )
            pred = pred_subtype or pred_type
        pred_matches = [value for value in (pred_subtype, pred_type, pred) if value]
        stanza_match = bool(pred_type and gold == pred_type)
        subtype_match = bool(pred_subtype and gold == pred_subtype)
        custom_match = bool(pred_column and pred == gold)
        is_correct = stanza_match or subtype_match or custom_match

        verse_values = [
            normalize_label(row.get("verse_n"))
            for row in stanza
            if normalize_label(row.get("verse_n"))
        ]
        verse_range = ""
        if verse_values:
            verse_range = (
                verse_values[0]
                if verse_values[0] == verse_values[-1]
                else f"{verse_values[0]}-{verse_values[-1]}"
            )
        observed_pattern = next(
            (row.get("observed_pattern", "") for row in stanza if row.get("observed_pattern", "")),
            "",
        )
        expected_pattern = next(
            (row.get("expected_pattern", "") for row in stanza if row.get("expected_pattern", "")),
            "",
        )

        total += 1
        if not pred_matches:
            missing_predictions += 1
        elif is_correct:
            correct += 1

        stanza_rows.append(
            {
                **{column: value for column, value in zip(group_columns, key[:-1])},
                stanza_column: key[-1],
                "line_count": len(stanza),
                "verse_range": verse_range,
                "gold_stanza": gold,
                "pred_stanza": pred,
                "pred_stanza_type": pred_type,
                "pred_stanza_subtype": pred_subtype,
                "stanza_match": str(stanza_match),
                "subtype_match": str(subtype_match),
                "missing_prediction": str(not pred_matches),
                "observed_pattern": observed_pattern,
                "expected_pattern": expected_pattern,
            }
        )

    return (
        {
            "stanza_type_stanzas": total,
            "stanza_type_correct": correct,
            "stanza_type_missing_predictions": missing_predictions,
            "stanza_type_accuracy": safe_divide(correct, total),
        },
        stanza_rows,
    )


def evaluate(
    rows,
    group_columns,
    pred_column,
    gold_column,
    line_id_column=None,
    text_column=None,
):
    counts = empty_counts()
    pair_rows = []

    for group_key, group in grouped_rows(rows, group_columns).items():
        counts["groups"] += 1
        counts["lines"] += len(group)

        group_perfect = True
        for _, row in group:
            pred = normalize_label(row[pred_column])
            gold = normalize_label(row[gold_column])
            if pred == gold:
                counts["line_matches"] += 1
            else:
                group_perfect = False

        if group_perfect:
            counts["perfect_groups"] += 1

        for (left_index, left), (right_index, right) in combinations(group, 2):
            pred_same = same_rhyme(left[pred_column], right[pred_column])
            gold_same = same_rhyme(left[gold_column], right[gold_column])
            if not (pred_same or gold_same):
                continue

            add_pair_counts(counts, pred_same, gold_same)

            if line_id_column:
                left_id = left.get(line_id_column, left_index)
                right_id = right.get(line_id_column, right_index)
            else:
                left_id = left_index
                right_id = right_index

            left_pred = normalize_label(left[pred_column])
            right_pred = normalize_label(right[pred_column])
            left_gold = normalize_label(left[gold_column])
            right_gold = normalize_label(right[gold_column])

            pair_rows.append(
                {
                    **{column: value for column, value in zip(group_columns, group_key)},
                    "line_pair": f"{left_id}-{right_id}",
                    "left_text": left.get(text_column, "") if text_column else "",
                    "right_text": right.get(text_column, "") if text_column else "",
                    "pred_pair": f"{left_pred}-{right_pred}",
                    "gold_pair": f"{left_gold}-{right_gold}",
                    "pred_same": int(pred_same),
                    "gold_same": int(gold_same),
                    "correct": int(pred_same == gold_same),
                }
            )

    return counts, pair_rows


def print_metrics(values):
    integer_keys = ("groups", "lines", "pairs", "tp", "fp", "fn", "tn")
    for key in integer_keys:
        print(f"{key}\t{values[key]}")
    for key in ("accuracy", "precision", "recall", "f1", "line_accuracy", "perfect_group_accuracy"):
        print(f"{key}\t{values[key]:.6f}")
    if "stanza_type_accuracy" in values:
        for key in (
            "stanza_type_stanzas",
            "stanza_type_correct",
            "stanza_type_missing_predictions",
        ):
            print(f"{key}\t{values[key]}")
        print(f"stanza_type_accuracy\t{values['stanza_type_accuracy']:.6f}")


def write_summary(path, values, input_path, pairs_path=None):
    fieldnames = [
        "input_path",
        "pairs_path",
        "groups",
        "lines",
        "pairs",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "tp",
        "fp",
        "fn",
        "tn",
        "line_accuracy",
        "perfect_group_accuracy",
        "stanza_type_stanzas",
        "stanza_type_correct",
        "stanza_type_missing_predictions",
        "stanza_type_accuracy",
    ]
    row = {
        "input_path": input_path,
        "pairs_path": pairs_path or "",
        **values,
    }
    path = Path(path)
    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            quoting=csv.QUOTE_NONE,
            quotechar=TSV_QUOTECHAR,
            escapechar="\\",
        )
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def write_pairs(path, pair_rows, group_columns):
    fieldnames = [
        *group_columns,
        "line_pair",
        "left_text",
        "right_text",
        "pred_pair",
        "gold_pair",
        "pred_same",
        "gold_same",
        "correct",
    ]
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
        writer.writerows(pair_rows)


def write_stanzas(path, stanza_rows, group_columns, stanza_column):
    fieldnames = [
        *group_columns,
        stanza_column,
        "line_count",
        "verse_range",
        "gold_stanza",
        "pred_stanza",
        "pred_stanza_type",
        "pred_stanza_subtype",
        "stanza_match",
        "subtype_match",
        "missing_prediction",
        "observed_pattern",
        "expected_pattern",
    ]
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
        writer.writerows(stanza_rows)


def main():
    args = parse_args()
    fieldnames, rows = read_rows(args.input_path)
    gold_column = choose_gold_column(fieldnames, args.gold_column)
    text_column = choose_text_column(fieldnames, args.text_column)
    for column in (args.pred_column, gold_column):
        if column not in fieldnames:
            raise ValueError(
                f"Missing column {column!r}. Available columns: {', '.join(fieldnames)}"
            )
    if args.line_id_column and args.line_id_column not in fieldnames:
        raise ValueError(
            f"Missing line id column {args.line_id_column!r}. "
            f"Available columns: {', '.join(fieldnames)}"
        )

    group_columns = choose_group_columns(fieldnames, args.group_columns)
    counts, pair_rows = evaluate(
        rows,
        group_columns,
        args.pred_column,
        gold_column,
        args.line_id_column,
        text_column,
    )
    metric_values = metrics(counts)
    stanza_column = choose_stanza_column(fieldnames, args.stanza_column)
    stanza_rows = None
    stanza_gold_column = args.stanza_gold_column or "stanzaTypeNarrow"
    if args.stanza_gold_column and stanza_gold_column not in fieldnames:
        raise ValueError(
            f"Missing stanza gold column {stanza_gold_column!r}. "
            f"Available columns: {', '.join(fieldnames)}"
        )
    if stanza_gold_column in fieldnames and stanza_column:
        if args.stanza_pred_column:
            if args.stanza_pred_column not in fieldnames:
                raise ValueError(
                    f"Missing stanza prediction column {args.stanza_pred_column!r}. "
                    f"Available columns: {', '.join(fieldnames)}"
                )
        elif not {"stanza_type", "stanza_subtype"}.intersection(fieldnames):
            raise ValueError(
                "Stanza evaluation requires stanza_type or stanza_subtype, "
                "or pass --stanza-pred-column."
            )
        stanza_metrics, stanza_rows = evaluate_stanza_types(
            rows,
            group_columns,
            stanza_column,
            stanza_gold_column,
            args.stanza_pred_column,
        )
        metric_values.update(stanza_metrics)
    print_metrics(metric_values)
    if args.pairs_path:
        write_pairs(args.pairs_path, pair_rows, group_columns)
        print(f"pairs_path\t{args.pairs_path}")
    if stanza_rows is not None:
        stanzas_path = args.stanzas_path
        if stanzas_path is None:
            stanzas_dir = Path(args.pairs_path).parent if args.pairs_path else Path(".")
            stanzas_path = str(stanzas_dir / "stanzas.tsv")
        if stanzas_path:
            write_stanzas(stanzas_path, stanza_rows, group_columns, stanza_column)
            print(f"stanzas_path\t{stanzas_path}")
    summary_path = args.summary_path
    if summary_path is None:
        summary_dir = Path(args.pairs_path).parent if args.pairs_path else Path(".")
        summary_path = str(summary_dir / "summary.tsv")
    if summary_path:
        write_summary(summary_path, metric_values, args.input_path, args.pairs_path)
        print(f"summary_path\t{summary_path}")


if __name__ == "__main__":
    main()
