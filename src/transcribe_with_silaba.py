import csv
from pathlib import Path
from types import SimpleNamespace
import re
import sys

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parent
SILABA_DIR = WORKSPACE_DIR / "silaba_gl"

sys.path.insert(0, str(SILABA_DIR))

from silaba_py import Silaba, SilabaError  # noqa: E402


INPUT_PATH = PROJECT_DIR / "data" / "gl-prepro-35k.tsv"
OUTPUT_PATH = PROJECT_DIR / "data" / "gl-prepro-35k-silaba.tsv"
OUTPUT_COLUMN = "phSilaba"
TSV_QUOTECHAR = "\x07"

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?")
TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?|\d+(?:[.,]\d+)?|[^\w\s]")


def build_silaba_args():
    return SimpleNamespace(
        l=False,
        i=True,
        d=False,
        p=True,
        s=False,
        c=True,
        t=True,
        r=False,
        h=False,
        b=True,
    )


def merge_tokens(tokens):
    text = " ".join(tokens)
    text = re.sub(r"\s+([.,!?;:)\]])", r"\1", text)
    text = re.sub(r"([\(\[¡¿])\s+", r"\1", text)
    return text.strip()


def reset_silaba_state(silaba):
    silaba.entrada = ""
    silaba.entrada2 = None
    silaba.entrada_lem = None
    silaba.entrada_lem2 = None
    silaba.entrada_vbex = None
    silaba.input_word = ""
    silaba.palavra = ""
    silaba.deep = ""


def transcribe_token(token, silaba, cache):
    if not WORD_RE.fullmatch(token):
        return token

    key = token.lower()
    if key not in cache:
        try:
            reset_silaba_state(silaba)
            cache[key] = silaba.run(token)
        except SilabaError:
            cache[key] = "erro"
    return cache[key]


def transcribe_text(text, silaba, cache):
    tokens = TOKEN_RE.findall(text)
    transcribed_tokens = [transcribe_token(token, silaba, cache) for token in tokens]
    return merge_tokens(transcribed_tokens)


def main():
    df = pd.read_csv(INPUT_PATH, sep="\t")
    df.dropna(subset=["running_text"], inplace=True)

    silaba = Silaba(build_silaba_args())
    cache = {}
    df[OUTPUT_COLUMN] = df["running_text"].apply(lambda text: transcribe_text(text, silaba, cache))
    df.to_csv(
        OUTPUT_PATH,
        sep="\t",
        index=False,
        quoting=csv.QUOTE_NONE,
        quotechar=TSV_QUOTECHAR,
        escapechar="\\",
    )

    print(f"Wrote {len(df)} rows to {OUTPUT_PATH}")
    print(f"Unique word forms transcribed: {len(cache)}")


if __name__ == "__main__":
    main()
