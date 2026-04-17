import time

import pandas as pd

from rhymetagger import RhymeTagger


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


if __name__ == "__main__":
    rt = RhymeTagger()
    rt.new_model(lang="gl", transcribed=True)

    corpus = create_corpus_from_df("../data/gl-prepro-35k-cotovia-3.tsv")

    print(f"Start adding poems to model: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    for poem in corpus:
        rt.add_to_model(poem)

    print(f"Start training: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    rt.train_model()
    rt.save_model("../models/gl-35k-cotovia-3.rtmodel")
