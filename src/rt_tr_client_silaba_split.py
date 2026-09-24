import argparse
import json
import random
import time
from math import ceil
from pathlib import Path

import pandas as pd
import nltk

from padded_rhymetagger import PaddedRhymeTagger
from utils import normalize_rhymetagger_ipa_nucleus_only


RANDOM_SEED = 42
TRAIN_FRACTION = 0.8
MAX_ITER = 200
ORTHOGRAPHIC_NGRAM = 3
LENGTH_PENALTY = 1.0

PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_DIR / "evaluation" / "gl-prepro-35k-silaba.tsv"
SILABA_COLUMN = "phSilaba"
MODEL_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-nucleus-only-padded-ortho-train80.rtmodel"
TEST_POEM_IDS_PATH = PROJECT_DIR / "models" / "gl-35k-silaba-nucleus-only-padded-ortho-test-poem-ids.txt"
TSV_QUOTECHAR = "\x07"


def ensure_nltk_tokenizers():
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)


def create_corpus_from_df(dfpath, silaba_column=SILABA_COLUMN):
    df = pd.read_csv(dfpath, sep="\t", quotechar=TSV_QUOTECHAR)
    required_columns = {"poem_id", "stanza_n", "running_text", silaba_column}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required column(s): {missing}")

    poems = []
    for poem_id, poem_df in df.groupby("poem_id", sort=False):
        stanzas = []
        for _, stanza_df in poem_df.groupby("stanza_n", sort=False):
            if stanza_df["running_text"].isna().any() or stanza_df[silaba_column].isna().any():
                continue

            stanza = [
                {
                    "text": row["running_text"].strip(),
                    "ipa": normalize_rhymetagger_ipa_nucleus_only(row[silaba_column]),
                }
                for _, row in stanza_df.iterrows()
            ]

            if stanza:
                stanzas.append(stanza)

        if stanzas:
            poems.append({"poem_id": poem_id, "stanzas": stanzas})

    return poems


def split_poems(poems, train_fraction=TRAIN_FRACTION, random_seed=RANDOM_SEED):
    shuffled_poems = list(poems)
    random.Random(random_seed).shuffle(shuffled_poems)

    train_size = ceil(len(shuffled_poems) * train_fraction)
    train_poems = shuffled_poems[:train_size]
    test_poems = shuffled_poems[train_size:]

    return train_poems, test_poems


def save_model_with_settings_fix(rt, model_path):
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    rt.save_model(str(model_path))

    json_path = model_path if model_path.suffix == ".json" else Path(f"{model_path}.json")
    with json_path.open(encoding="utf-8") as f:
        model = json.load(f)
    model["settings"]["ngram"] = ORTHOGRAPHIC_NGRAM
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(model, f)


def main():
    parser = argparse.ArgumentParser(description="Train/test split for a Silaba rhyme model.")
    parser.add_argument("--input-path", type=Path, default=INPUT_PATH)
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--test-poem-ids-path", type=Path, default=TEST_POEM_IDS_PATH)
    parser.add_argument("--silaba-column", default=SILABA_COLUMN)
    parser.add_argument("--train-fraction", type=float, default=TRAIN_FRACTION)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    ensure_nltk_tokenizers()

    corpus = create_corpus_from_df(args.input_path, args.silaba_column)
    train_corpus, test_corpus = split_poems(corpus, args.train_fraction, args.random_seed)

    print(f"Total poems: {len(corpus)}")
    print(f"Train poems: {len(train_corpus)}")
    print(f"Test poems: {len(test_corpus)}")
    print(f"Random seed: {args.random_seed}")
    print(f"SILABA column: {args.silaba_column}")
    print(f"Max iterations: {MAX_ITER}")
    print(f"Orthographic ngram: {ORTHOGRAPHIC_NGRAM}")
    print(f"Length penalty: {LENGTH_PENALTY}")

    rt = PaddedRhymeTagger()
    rt.new_model(
        lang="gl",
        transcribed=True,
        max_iter=MAX_ITER,
        ngram=ORTHOGRAPHIC_NGRAM,
        length_penalty=LENGTH_PENALTY,
    )

    print(f"Start adding train poems to model: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    for poem in train_corpus:
        rt.add_to_model(poem["stanzas"])

    print(f"Start training: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    rt.train_model()
    save_model_with_settings_fix(rt, args.model_path)

    args.test_poem_ids_path.parent.mkdir(parents=True, exist_ok=True)
    with args.test_poem_ids_path.open("w", encoding="utf-8") as f:
        for poem in test_corpus:
            f.write(f"{poem['poem_id']}\n")


if __name__ == "__main__":
    main()
