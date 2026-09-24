import argparse
import csv
from pathlib import Path

import pandas as pd
import nltk

from padded_rhymetagger import PaddedRhymeTagger
from utils import normalize_rhymetagger_ipa_nucleus_only


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_DIR / "evaluation" / "gl-prepro-35k-silaba.tsv"
DEFAULT_MODEL_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-nucleus-only-padded-train80.rtmodel.json"
DEFAULT_TEST_IDS_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-nucleus-only-padded-test-poem-ids.txt"
DEFAULT_OUTPUT_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-nucleus-only-padded-test-rhymes.tsv"
SILABA_COLUMN = "phSilaba"
TSV_QUOTECHAR = "\x07"


def read_test_poem_ids(path):
    with path.open() as f:
        return [int(line.strip()) for line in f if line.strip()]


def build_poem(poem_df, stanza_column, text_column):
    poem = []
    verses = []
    final_ipa_tokens = []
    prepro_values = []
    gold_values = []

    for _, stanza_df in poem_df.groupby(stanza_column, sort=False):
        stanza = []
        for row in stanza_df.itertuples():
            verse = getattr(row, text_column).strip()
            ipa = normalize_rhymetagger_ipa_nucleus_only(getattr(row, SILABA_COLUMN))
            verses.append(verse)
            prepro_values.append(getattr(row, "prepro", ""))
            gold_values.append(getattr(row, "rhyme", ""))
            final_ipa_tokens.append(nltk.word_tokenize(ipa)[-1])
            stanza.append(
                {
                    "text": verse,
                    "ipa": ipa,
                }
            )
        poem.append(stanza)

    return poem, verses, prepro_values, gold_values, final_ipa_tokens


def rhyme_to_letter(rhyme):
    if not rhyme:
        return ""

    try:
        final = int(rhyme)
    except (TypeError, ValueError):
        return str(rhyme)

    if final <= 0:
        return ""

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

    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--poem-id", type=int)
    parser.add_argument("--data-path", default=DEFAULT_DATA_PATH)
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-path", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--poem-column", default="poem_id")
    parser.add_argument("--stanza-column", default="stanza_n")
    parser.add_argument("--text-column", default="running_text")
    parser.add_argument("--ngram", type=int, default=3)
    parser.add_argument("--length-penalty", type=float, default=1.0)
    parser.add_argument("--window", type=int)
    parser.add_argument("--prob-ipa-min", type=float)
    parser.add_argument("--prob-ngram-min", type=float)
    parser.add_argument("--stanza-limit", action="store_true")
    parser.add_argument("--show-ipa", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.data_path, sep="\t", quotechar=TSV_QUOTECHAR)
    poem_ids = (
        [args.poem_id]
        if args.poem_id
        else [int(poem_id) for poem_id in df[args.poem_column].dropna().unique()]
    )

    rt = PaddedRhymeTagger()
    rt.load_model(str(args.model_path), verbose=False)

    output_rows = []
    for poem_id in poem_ids:
        poem_df = df[df[args.poem_column] == poem_id]
        if poem_df.empty:
            raise ValueError(f"No rows found for {args.poem_column}={poem_id}")

        poem, verses, prepro_values, gold_values, final_ipa_tokens = build_poem(
            poem_df,
            args.stanza_column,
            args.text_column,
        )

        tag_kwargs = {
            "ngram": args.ngram,
            "length_penalty": args.length_penalty,
        }
        if args.window is not None:
            tag_kwargs["window"] = args.window
        if args.prob_ipa_min is not None:
            tag_kwargs["prob_ipa_min"] = args.prob_ipa_min
        if args.prob_ngram_min is not None:
            tag_kwargs["prob_ngram_min"] = args.prob_ngram_min
        if args.stanza_limit:
            tag_kwargs["stanza_limit"] = True

        rhymes = rt.tag(poem, transcribed=True, output_format=3, **tag_kwargs)

        for line_n, (verse, prepro, rhyme, gold, final_ipa) in enumerate(
            zip(verses, prepro_values, rhymes, gold_values, final_ipa_tokens),
            start=1,
        ):
            row = {
                "poem_id": poem_id,
                "line_n": line_n,
                "verse": verse,
                "prepro": prepro,
                "rhyme": rhyme or "",
                "letter": rhyme_to_letter(rhyme),
                "gold": gold,
            }
            if args.show_ipa:
                row["final_ipa"] = final_ipa
            output_rows.append(row)

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output_rows).to_csv(
        output_path,
        sep="\t",
        index=False,
        quoting=csv.QUOTE_NONE,
        quotechar=TSV_QUOTECHAR,
        escapechar="\\",
    )
    print(f"Wrote {len(output_rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
