import argparse
from pathlib import Path

import pandas as pd

from rhymetagger import RhymeTagger

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_DIR / "evaluation" / "gl-prepro-35k.tsv"
DEFAULT_MODEL_PATH = PROJECT_DIR / "models" / "gl-35k-500.rtmodel"

def create_corpus_from_df(dfpath):
    df = pd.read_csv(dfpath, sep="\t")
    df.dropna(inplace=True)
    poems = df.groupby("poem_id")
    poem_list = []
    for idx, poem in poems:
        #poem_list.append("\n".join(poem["running_text"]))
        poem_list.append([x.strip() for x in poem["running_text"]])
    return poem_list

def main():
    parser = argparse.ArgumentParser(description="Train a basic orthographic rhyme model.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--max-poems", type=int, default=500)
    args = parser.parse_args()

    rt = RhymeTagger()
    rt.new_model(lang="es")

    corpus = create_corpus_from_df(args.input_path)
    corpus = corpus[:args.max_poems]

    for poem in corpus:
        #if len(poem) > 100:
        #    poem = poem[0:100]
        rt.add_to_model(poem)

    rt.train_model()
    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    rt.save_model(str(args.model_path))


if __name__ == "__main__":
    main()
