"""The gators-verse command: annotate rhyme, stanza and poem types.

Input is either a plain-text poem (one verse per line, a blank line between
stanzas) or, for files ending in .tsv, a table with one row per verse.
Output is a TSV with one row per verse.
"""

import argparse
import csv
import sys
import warnings

import pandas as pd

from . import __version__
from .pipeline import analyze, read_poem_text

TSV_OPTIONS = {"sep": "\t", "quoting": csv.QUOTE_NONE}


def read_input(path):
    if path is None or path == "-":
        return read_poem_text(sys.stdin.read())
    if path.endswith(".tsv"):
        return pd.read_csv(path, keep_default_na=False, na_values=[""], **TSV_OPTIONS)
    with open(path, encoding="utf-8") as handle:
        return read_poem_text(handle.read())


def write_tsv(frame, path):
    frame.to_csv(path if path else sys.stdout, index=False, **TSV_OPTIONS)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gators-verse",
        description="Annotate rhyme, stanza and poem types in Galician poetry.",
    )
    parser.add_argument("input", nargs="?", help="poem as plain text, or a .tsv table (default: standard input)")
    parser.add_argument("-o", "--output", help="output TSV (default: standard output)")
    parser.add_argument("--stanza-scores", metavar="PATH", help="also write every stanza pattern's score here")
    parser.add_argument("--poem-scores", metavar="PATH", help="also write every poem pattern's score here")
    parser.add_argument("--no-gama", action="store_true", help="don't use gama-verse even if it is installed")
    parser.add_argument("--poem-column", default="poem_id")
    parser.add_argument("--stanza-column", default="stanza_n")
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--syllable-column", default="metrical_syllables")
    parser.add_argument("--stress-column", default="stressed_syllables")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    warnings.formatwarning = lambda message, *_args, **_kwargs: f"Warning: {message}\n"
    try:
        results, stanza_scores, poem_scores = analyze(
            read_input(args.input),
            use_gama=not args.no_gama,
            poem_column=args.poem_column,
            stanza_column=args.stanza_column,
            text_column=args.text_column,
            syllable_column=args.syllable_column,
            stress_column=args.stress_column,
        )
    except ValueError as error:
        parser.error(str(error))
    write_tsv(results, args.output)
    if args.stanza_scores:
        write_tsv(stanza_scores, args.stanza_scores)
    if args.poem_scores:
        write_tsv(poem_scores, args.poem_scores)


if __name__ == "__main__":
    main()
