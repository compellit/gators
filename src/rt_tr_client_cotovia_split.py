import argparse
import random
import time
from math import ceil
from pathlib import Path

import pandas as pd

from rhymetagger import RhymeTagger


RANDOM_SEED = 42
TRAIN_FRACTION = 0.8
PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_DIR / "evaluation" / "gl-prepro-35k-cotovia-3.tsv"
DEFAULT_MODEL_PATH = PROJECT_DIR / "models" / "gl-35k-cotovia-3-train80.rtmodel"
DEFAULT_TEST_IDS_PATH = PROJECT_DIR / "models" / "gl-35k-cotovia-3-test-poem-ids.txt"


def create_corpus_from_df(dfpath):
    df = pd.read_csv(dfpath, sep="\t")

    poems = []
    for poem_id, poem_df in df.groupby("poem_id", sort=False):
        stanzas = []
        for _, stanza_df in poem_df.groupby("stanza_n", sort=False):
            if stanza_df["running_text"].isna().any() or stanza_df["phCotovia"].isna().any():
                continue

            stanza = [
                {"text": row["running_text"].strip(), "ipa": row["phCotovia"].strip()}
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


def main():
    parser = argparse.ArgumentParser(description="Train/test split for a Cotovia rhyme model.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--test-poem-ids-path", type=Path, default=DEFAULT_TEST_IDS_PATH)
    parser.add_argument("--train-fraction", type=float, default=TRAIN_FRACTION)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    corpus = create_corpus_from_df(args.input_path)
    train_corpus, test_corpus = split_poems(corpus, args.train_fraction, args.random_seed)

    print(f"Total poems: {len(corpus)}")
    print(f"Train poems: {len(train_corpus)}")
    print(f"Test poems: {len(test_corpus)}")
    print(f"Random seed: {args.random_seed}")

    rt = RhymeTagger()
    rt.new_model(lang="gl", transcribed=True)

    print(f"Start adding train poems to model: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    for poem in train_corpus:
        rt.add_to_model(poem["stanzas"])

    print(f"Start training: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    rt.train_model()
    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    rt.save_model(str(args.model_path))

    args.test_poem_ids_path.parent.mkdir(parents=True, exist_ok=True)
    with args.test_poem_ids_path.open("w", encoding="utf-8") as f:
        for poem in test_corpus:
            f.write(f"{poem['poem_id']}\n")


if __name__ == "__main__":
    main()
