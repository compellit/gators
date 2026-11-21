"""The gators-verse command: annotate rhyme, stanza and poem types.

Input is either a plain-text poem (one verse per line, a blank line between
stanzas) or, for files ending in .tsv, a table with one row per verse.
Output is a TSV with one row per verse.
"""

import argparse
import csv
import importlib.util
import sys

import pandas as pd

from . import __version__
from .annotation import annotate
from .transcription import transcribe

TSV_OPTIONS = {"sep": "\t", "quoting": csv.QUOTE_NONE}
# Gumper's stresses passed to the rhyme analysis, as in the GAMA web app.
GAMA_STRESS_KEY = "regular_pattern"


def read_poem_text(text):
    """Turn a plain-text poem into a table: one row per verse."""
    rows = []
    stanza_n = 1
    for line in text.splitlines():
        if line.strip():
            rows.append({"poem_id": 1, "stanza_n": stanza_n, "text": line.strip()})
        elif rows and rows[-1]["stanza_n"] == stanza_n:
            stanza_n += 1
    return pd.DataFrame(rows, columns=["poem_id", "stanza_n", "text"])


def read_input(path):
    if path is None or path == "-":
        return read_poem_text(sys.stdin.read())
    if path.endswith(".tsv"):
        return pd.read_csv(path, keep_default_na=False, na_values=[""], **TSV_OPTIONS)
    with open(path, encoding="utf-8") as handle:
        return read_poem_text(handle.read())


def write_tsv(frame, path):
    frame.to_csv(path if path else sys.stdout, index=False, **TSV_OPTIONS)


def add_gama_columns(df, args, need_metre):
    """Normalize the spelling (and scan, if metre is needed) with gama-verse, poem by poem."""
    import gama_verse

    normalized = pd.Series(index=df.index, dtype=object)
    syllables = pd.Series(index=df.index, dtype=object)
    stresses = pd.Series(index=df.index, dtype=object)
    for _, poem in df.groupby(args.poem_column, sort=False):
        lines = [str(text) for text in poem[args.text_column]]
        if need_metre:
            results = gama_verse.scan("\n".join(lines))
            normalized_lines = [result["preprocessing"] for result in results]
            syllables[poem.index] = [result["metrical_syllables"] for result in results]
            stresses[poem.index] = [result[GAMA_STRESS_KEY] for result in results]
        else:
            normalized_lines = gama_verse.preprocess("\n".join(lines)).splitlines()
        if len(normalized_lines) != len(lines):
            raise RuntimeError("gama-verse returned a different number of lines")
        normalized[poem.index] = normalized_lines
    df["normalized_text"] = normalized
    if need_metre:
        df[args.syllable_column] = syllables
        df[args.stress_column] = stresses


def gama_available():
    return importlib.util.find_spec("gama_verse") is not None


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

    df = read_input(args.input)
    for column in (args.poem_column, args.stanza_column, args.text_column):
        if column not in df.columns:
            parser.error(f"column {column!r} not found in the input; available: {list(df.columns)}")
    df = df.dropna(subset=[args.text_column]).reset_index(drop=True)
    has_metre = args.syllable_column in df.columns and args.stress_column in df.columns

    normalized_lines = None
    if not args.no_gama and gama_available():
        add_gama_columns(df, args, need_metre=not has_metre)
        normalized_lines = df["normalized_text"].tolist()
    elif not has_metre:
        print(
            "Warning: no metre columns and gama-verse not used; stanza and poem types "
            "will be unreliable. Install gators-verse[gama] to get them.",
            file=sys.stderr,
        )
    df["transcription"] = transcribe(df[args.text_column].astype(str).tolist(), normalized_lines)

    results, stanza_scores, poem_scores = annotate(
        df,
        poem_column=args.poem_column,
        stanza_column=args.stanza_column,
        text_column=args.text_column,
        syllable_column=args.syllable_column,
        stress_column=args.stress_column,
    )
    write_tsv(results, args.output)
    if args.stanza_scores:
        write_tsv(stanza_scores, args.stanza_scores)
    if args.poem_scores:
        write_tsv(poem_scores, args.poem_scores)


if __name__ == "__main__":
    main()
