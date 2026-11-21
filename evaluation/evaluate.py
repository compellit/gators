"""Evaluate gators-verse output against the gold rhyme letters and stanza types.

Rhyme is evaluated pairwise: rhyme letters are arbitrary names, so what is
compared is whether two lines of the same poem rhyme together (ABAB and CDCD
agree fully). Only pairs that the prediction or the gold marks as rhyming are
counted, so there are no true negatives; precision, recall and F1 do not
need them. See docs/EVALUATION.md.

Stanza types: a stanza is correct when its gold type equals the predicted
stanza type or subtype; a stanza without a predicted type counts as wrong.
Stanzas whose gold type is "none" or empty are not annotated in the gold and
are not evaluated; this does not mean that they should get no type.

Input: gators-verse output with the gold columns written by prepare.py
(gold_rhyme, gold_stanza_type). Writes pairs.tsv, stanzas.tsv and summary.tsv
to the output folder.
"""

import argparse
import csv
from itertools import combinations
from pathlib import Path

import pandas as pd

NO_RHYME_VALUES = {"", "-", "0", "nan", "none", "null"}
TSV_OPTIONS = {"sep": "\t", "quoting": csv.QUOTE_NONE}


def normalize_label(value):
    return "" if pd.isna(value) else str(value).strip().lower()


def same_rhyme(left, right):
    left = normalize_label(left)
    return left == normalize_label(right) and left not in NO_RHYME_VALUES


def evaluate_rhyme(results):
    """Return the pair counts and one row per counted pair."""
    counts = {"tp": 0, "fp": 0, "fn": 0}
    pair_rows = []
    for poem_id, poem in results.groupby("poem_id", sort=False):
        for left, right in combinations(poem.itertuples(), 2):
            pred_same = same_rhyme(left.rhyme, right.rhyme)
            gold_same = same_rhyme(left.gold_rhyme, right.gold_rhyme)
            if not (pred_same or gold_same):
                continue
            outcome = "tp" if pred_same and gold_same else "fp" if pred_same else "fn"
            counts[outcome] += 1
            pair_rows.append(
                {
                    "poem_id": poem_id,
                    "line_pair": f"{left.line_id}-{right.line_id}",
                    "left_text": left.text,
                    "right_text": right.text,
                    "pred_pair": f"{normalize_label(left.rhyme)}-{normalize_label(right.rhyme)}",
                    "gold_pair": f"{normalize_label(left.gold_rhyme)}-{normalize_label(right.gold_rhyme)}",
                    "pred_same": int(pred_same),
                    "gold_same": int(gold_same),
                    "correct": int(pred_same == gold_same),
                }
            )
    return counts, pair_rows


def evaluate_stanzas(results):
    """Return the number of evaluated and correct stanzas, and one row per stanza."""
    stanza_rows = []
    for (poem_id, stanza_n), stanza in results.groupby(["poem_id", "stanza_n"], sort=False):
        gold = first_value(stanza["gold_stanza_type"])
        if gold in NO_RHYME_VALUES:
            continue
        pred_type = first_value(stanza["stanza_type"])
        pred_subtype = first_value(stanza["stanza_subtype"])
        stanza_rows.append(
            {
                "poem_id": poem_id,
                "stanza_n": stanza_n,
                "line_count": len(stanza),
                "gold_stanza": gold,
                "pred_stanza_type": pred_type,
                "pred_stanza_subtype": pred_subtype,
                "correct": int(bool(pred_type and gold == pred_type) or bool(pred_subtype and gold == pred_subtype)),
                "rhyme_pattern": first_value(stanza["stanza_rhyme_pattern"]),
                "expected_pattern": first_value(stanza["stanza_expected_pattern"]),
            }
        )
    return stanza_rows


def first_value(column):
    """First non-empty value of a stanza's column, normalized."""
    return next((normalize_label(value) for value in column if normalize_label(value)), "")


def ratio(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("results", help="gators-verse output with gold_rhyme and gold_stanza_type")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    results = pd.read_csv(args.results, keep_default_na=False, na_values=[""], **TSV_OPTIONS)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    counts, pair_rows = evaluate_rhyme(results)
    precision = ratio(counts["tp"], counts["tp"] + counts["fp"])
    recall = ratio(counts["tp"], counts["tp"] + counts["fn"])
    stanza_rows = evaluate_stanzas(results)
    correct_stanzas = sum(row["correct"] for row in stanza_rows)
    summary = {
        "poems": results["poem_id"].nunique(),
        "lines": len(results),
        "pairs": len(pair_rows),
        **counts,
        "precision": precision,
        "recall": recall,
        "f1": ratio(2 * precision * recall, precision + recall),
        "stanzas": len(stanza_rows),
        "stanzas_correct": correct_stanzas,
        "stanzas_without_prediction": sum(
            1 for row in stanza_rows if not (row["pred_stanza_type"] or row["pred_stanza_subtype"])
        ),
        "stanza_accuracy": ratio(correct_stanzas, len(stanza_rows)),
    }

    pd.DataFrame(pair_rows).to_csv(output_dir / "pairs.tsv", index=False, **TSV_OPTIONS)
    pd.DataFrame(stanza_rows).to_csv(output_dir / "stanzas.tsv", index=False, **TSV_OPTIONS)
    pd.DataFrame([summary]).to_csv(output_dir / "summary.tsv", index=False, **TSV_OPTIONS)
    for key, value in summary.items():
        print(f"{key}\t{value:.4f}" if isinstance(value, float) else f"{key}\t{value}")


if __name__ == "__main__":
    main()
