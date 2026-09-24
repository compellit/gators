import argparse
import time
from pathlib import Path

import pandas as pd

from rhymetagger import RhymeTagger

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_DIR / "evaluation" / "gl-prepro-35k-cotovia-3.tsv"
DEFAULT_MODEL_PATH = PROJECT_DIR / "models" / "gl-35k-cotovia-3.rtmodel"


def create_corpus_from_df(dfpath):
    df = pd.read_csv(dfpath, sep="\t")

    poems = []
    for _, poem_df in df.groupby("poem_id", sort=False):
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
            poems.append(stanzas)

    return poems


def main():
    parser = argparse.ArgumentParser(description="Train a Cotovia-transcribed rhyme model.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()

    rt = RhymeTagger()
    rt.new_model(lang="gl", transcribed=True)

    corpus = create_corpus_from_df(args.input_path)

    print(f"Start adding poems to model: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    for poem in corpus:
        rt.add_to_model(poem)

    print(f"Start training: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    rt.train_model()
    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    rt.save_model(str(args.model_path))


if __name__ == "__main__":
    main()
