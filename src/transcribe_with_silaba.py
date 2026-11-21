"""Command-line wrapper for transcribe_with_silaba_module: TSV in, TSV out.

With --prepro, lines are first normalised with the scansion preprocessing
(as the web app does through its preprocessing service), and each line keeps
its normalised form only where rhyme_text() accepts it; --silaba-prepro
applies only a light spelling cleanup instead.
"""
import argparse
import csv
from pathlib import Path

import pandas as pd

from transcribe_with_silaba_module import (
    GUMPER_PREPROCESSOR_PATH,
    OUTPUT_COLUMN,
    PROJECT_DIR,
    TEXT_COLUMN,
    TSV_QUOTECHAR,
    main as transcribe,
    normalize_with_gumper,
    rhyme_text,
)

INPUT_PATH = PROJECT_DIR / "data" / "gl-prepro-35k.tsv"
OUTPUT_PATH = PROJECT_DIR / "data" / "gl-prepro-35k-silaba.tsv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", default=INPUT_PATH)
    parser.add_argument("--output-path", default=OUTPUT_PATH)
    parser.add_argument("--text-column", default=TEXT_COLUMN)
    parser.add_argument("--output-column", default=OUTPUT_COLUMN)
    parser.add_argument(
        "--prepro",
        action="store_true",
        help="Preprocess the text with the same running-text preprocessing used by Gumper.",
    )
    parser.add_argument(
        "--silaba-prepro",
        action="store_true",
        help="Use the older Silaba-specific transcription cleanup instead of Gumper preprocessing.",
    )
    parser.add_argument(
        "--gumper-preprocessor-path",
        type=Path,
        default=GUMPER_PREPROCESSOR_PATH,
        help="Path to preprocessing/g2s_client_running_text.py.",
    )
    args = parser.parse_args()

    if args.prepro and args.silaba_prepro:
        raise SystemExit("Choose only one preprocessing mode: --prepro or --silaba-prepro.")

    # Verses can contain quotation marks: read them as text (8773948).
    df = pd.read_csv(
        args.input_path,
        sep="\t",
        quoting=csv.QUOTE_NONE,
        quotechar=TSV_QUOTECHAR,
        escapechar="\\",
    )
    df.dropna(subset=[args.text_column], inplace=True)
    text_column = args.text_column
    if args.prepro:
        normalized = normalize_with_gumper(df[args.text_column], args.gumper_preprocessor_path)
        df["prepro"] = [
            rhyme_text(original, line)
            for original, line in zip(df[args.text_column], normalized)
        ]
        text_column = "prepro"

    df = transcribe(
        df,
        text_column=text_column,
        output_column=args.output_column,
        prepro=args.silaba_prepro,
    )
    df.to_csv(
        args.output_path,
        sep="\t",
        index=False,
        quoting=csv.QUOTE_NONE,
        quotechar=TSV_QUOTECHAR,
        escapechar="\\",
    )
    print(f"Wrote {len(df)} rows to {args.output_path}")


if __name__ == "__main__":
    main()
