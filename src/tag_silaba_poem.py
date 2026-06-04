import argparse
import csv
from pathlib import Path

import pandas as pd
import nltk
from rhymetagger import RhymeTagger

from utils import normalize_rhymetagger_ipa


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_DIR / "data" / "gl-prepro-35k-silaba.tsv"
DEFAULT_MODEL_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-train80.rtmodel.json"
DEFAULT_TEST_IDS_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-test-poem-ids.txt"
DEFAULT_OUTPUT_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-test-rhymes.tsv"
SILABA_COLUMN = "phSilaba"
TSV_QUOTECHAR = "\x07"


def read_test_poem_ids(path):
    with path.open() as f:
        return [int(line.strip()) for line in f if line.strip()]


def build_poem(poem_df):
    poem = []
    verses = []
    final_ipa_tokens = []

    for _, stanza_df in poem_df.groupby("stanza_n", sort=False):
        stanza = []
        for row in stanza_df.itertuples():
            verse = row.running_text.strip()
            ipa = normalize_rhymetagger_ipa(getattr(row, SILABA_COLUMN))
            verses.append(verse)
            final_ipa_tokens.append(nltk.word_tokenize(ipa)[-1])
            stanza.append(
                {
                    "text": verse,
                    "ipa": ipa,
                }
            )
        poem.append(stanza)

    return poem, verses, final_ipa_tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--poem-id", type=int)
    parser.add_argument("--data-path", default=DEFAULT_DATA_PATH)
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-path", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--window", type=int)
    parser.add_argument("--prob-ipa-min", type=float)
    parser.add_argument("--prob-ngram-min", type=float)
    parser.add_argument("--stanza-limit", action="store_true")
    parser.add_argument("--show-ipa", action="store_true")
    args = parser.parse_args()

    poem_ids = [args.poem_id] if args.poem_id else read_test_poem_ids(DEFAULT_TEST_IDS_PATH)
    df = pd.read_csv(args.data_path, sep="\t", quotechar=TSV_QUOTECHAR)

    rt = RhymeTagger()
    rt.load_model(str(args.model_path), verbose=False)

    output_rows = []
    for poem_id in poem_ids:
        poem_df = df[df.poem_id == poem_id]
        if poem_df.empty:
            raise ValueError(f"No rows found for poem_id={poem_id}")

        poem, verses, final_ipa_tokens = build_poem(poem_df)

        tag_kwargs = {}
        if args.window is not None:
            tag_kwargs["window"] = args.window
        if args.prob_ipa_min is not None:
            tag_kwargs["prob_ipa_min"] = args.prob_ipa_min
        if args.prob_ngram_min is not None:
            tag_kwargs["prob_ngram_min"] = args.prob_ngram_min
        if args.stanza_limit:
            tag_kwargs["stanza_limit"] = True

        rhymes = rt.tag(poem, transcribed=True, output_format=3, **tag_kwargs)

        for line_n, (verse, rhyme, final_ipa) in enumerate(zip(verses, rhymes, final_ipa_tokens), start=1):
            row = {
                "poem_id": poem_id,
                "line_n": line_n,
                "verse": verse,
                "rhyme": rhyme or "",
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
