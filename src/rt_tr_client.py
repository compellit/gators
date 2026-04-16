import pandas as pd

from rhymetagger import RhymeTagger

def create_corpus_from_df(dfpath):
    df = pd.read_csv(dfpath, sep="\t")
    df.dropna(inplace=True)
    poems = df.groupby("poem_id")
    poem_list = []
    for idx, poem in poems:
        #poem_list.append("\n".join(poem["running_text"]))
        poem_list.append([x.strip() for x in poem["running_text"]])
    return poem_list

if __name__ == "__main__":

    rt = RhymeTagger()
    rt.new_model(lang="es")
    
    corpus = create_corpus_from_df("../data/gl-prepro-35k.tsv")
    corpus = corpus[0:500]

    for poem in corpus:
        #if len(poem) > 100:
        #    poem = poem[0:100]
        rt.add_to_model(poem)

    rt.train_model()
    rt.save_model("../models/gl-35k-500.rtmodel")
