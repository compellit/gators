"""Command-line wrapper for rhyme_module: read a verse TSV, write the results.

The analysis itself is in rhyme_module.main(), which the web app also uses.
"""
import argparse
import csv

import pandas as pd

from rhyme_module import (
    DEFAULT_INPUT_PATH,
    DEFAULT_POEM_PATTERNS_PATH,
    DEFAULT_RESULTS_PATH,
    DEFAULT_STANZA_PATTERNS_PATH,
    TSV_QUOTECHAR,
    main,
)


def write_tsv(frame, path):
    frame.to_csv(
        path,
        sep="\t",
        index=False,
        quoting=csv.QUOTE_NONE,
        quotechar=TSV_QUOTECHAR,
        escapechar="\\",
    )


parser = argparse.ArgumentParser()
parser.add_argument("--input-path", default=DEFAULT_INPUT_PATH)
parser.add_argument("--poem-column", default="poem_id")
parser.add_argument("--stanza-column", default="stanza_n")
parser.add_argument("--verse-column", default="verse_text")
parser.add_argument("--ph-column", default="phSilaba")
parser.add_argument("--rhyme-column", default="rhyme")
parser.add_argument("--syllable-column")
parser.add_argument("--rhythm-column")
parser.add_argument("--no-syllable-column", action="store_true")
parser.add_argument("--no-rhythm-column", action="store_true")
parser.add_argument("--stanza-patterns-path", default=DEFAULT_STANZA_PATTERNS_PATH)
parser.add_argument("--poem-patterns-path", default=DEFAULT_POEM_PATTERNS_PATH)
parser.add_argument("--subtype-min-probability", type=float, default=0.8)
parser.add_argument("--poem-type-min-probability", type=float, default=0.8)
parser.add_argument("--results-path", default=DEFAULT_RESULTS_PATH)
parser.add_argument("--stanza-scores-path")
parser.add_argument("--poem-scores-path")
parser.add_argument("--poem-ids")
args = parser.parse_args()

df = pd.read_csv(
    args.input_path,
    sep="\t",
    quotechar=TSV_QUOTECHAR,
    escapechar="\\",
)
results, stanza_scores, poem_scores = main(
    df,
    syllable_column=args.syllable_column,
    rhythm_column=args.rhythm_column,
    poem_ids=args.poem_ids,
    poem_column=args.poem_column,
    stanza_column=args.stanza_column,
    verse_column=args.verse_column,
    ph_column=args.ph_column,
    rhyme_column=args.rhyme_column,
    stanza_patterns_path=args.stanza_patterns_path,
    poem_patterns_path=args.poem_patterns_path,
    subtype_min_probability=args.subtype_min_probability,
    poem_type_min_probability=args.poem_type_min_probability,
    no_syllable_column=args.no_syllable_column,
    no_rhythm_column=args.no_rhythm_column,
    return_scores=True,
)
write_tsv(results, args.results_path)
print(f"Wrote {len(results)} rows to {args.results_path}")

if args.stanza_scores_path:
    write_tsv(stanza_scores, args.stanza_scores_path)
    print(f"Wrote {len(stanza_scores)} rows to {args.stanza_scores_path}")

if args.poem_scores_path:
    write_tsv(poem_scores, args.poem_scores_path)
    print(f"Wrote {len(poem_scores)} rows to {args.poem_scores_path}")
