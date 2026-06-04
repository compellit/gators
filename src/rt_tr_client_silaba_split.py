import random
import time
from math import ceil

import pandas as pd
import nltk

from rhymetagger import RhymeTagger
from utils import normalize_rhymetagger_ipa


RANDOM_SEED = 42
TRAIN_FRACTION = 0.8
MAX_ITER = 200

INPUT_PATH = "../data/gl-prepro-35k-silaba.tsv"
SILABA_COLUMN = "phSilaba"
MODEL_PATH = "../models/gl-35k-silaba-train80.rtmodel"
TEST_POEM_IDS_PATH = "../models/gl-35k-silaba-test-poem-ids.txt"
TSV_QUOTECHAR = "\x07"


def ensure_nltk_tokenizers():
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)


def create_corpus_from_df(dfpath):
    df = pd.read_csv(dfpath, sep="\t", quotechar=TSV_QUOTECHAR)
    required_columns = {"poem_id", "stanza_n", "running_text", SILABA_COLUMN}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required column(s): {missing}")

    poems = []
    for poem_id, poem_df in df.groupby("poem_id", sort=False):
        stanzas = []
        for _, stanza_df in poem_df.groupby("stanza_n", sort=False):
            if stanza_df["running_text"].isna().any() or stanza_df[SILABA_COLUMN].isna().any():
                continue

            stanza = [
                {
                    "text": row["running_text"].strip(),
                    "ipa": normalize_rhymetagger_ipa(row[SILABA_COLUMN]),
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


if __name__ == "__main__":
    ensure_nltk_tokenizers()

    corpus = create_corpus_from_df(INPUT_PATH)
    train_corpus, test_corpus = split_poems(corpus)

    print(f"Total poems: {len(corpus)}")
    print(f"Train poems: {len(train_corpus)}")
    print(f"Test poems: {len(test_corpus)}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"SILABA column: {SILABA_COLUMN}")
    print(f"Max iterations: {MAX_ITER}")

    rt = RhymeTagger()
    rt.new_model(lang="gl", transcribed=True, max_iter=MAX_ITER)

    print(f"Start adding train poems to model: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    for poem in train_corpus:
        rt.add_to_model(poem["stanzas"])

    print(f"Start training: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    rt.train_model()
    rt.save_model(MODEL_PATH)

    with open(TEST_POEM_IDS_PATH, "w") as f:
        for poem in test_corpus:
            f.write(f"{poem['poem_id']}\n")
