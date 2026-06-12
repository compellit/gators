import argparse
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
TEXT_COLUMN = "running_text"
OUTPUT_COLUMN = "phSilaba"
TSV_QUOTECHAR = "\x07"
PREPRO_LETTER = "A-Za-zÁÉÍÓÚÜÑÏáéíóúüñïÂÊÎÔÛâêîôû"
PREPRO_APOSTROPHE = "'’‘"

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+(?:['’‘][A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+)?")
TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+(?:['’‘][A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+)?|\d+(?:[.,]\d+)?|[^\w\s]")


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


def prepro_text(text):
    text = re.sub(rf"(?i)q(?:u)?[{PREPRO_APOSTROPHE}]\s*(?=[{PREPRO_LETTER}])", "k", text)
    text = re.sub(rf"(?i)\bq(?:u)?\s+(?=[{PREPRO_LETTER}])", "k", text)
    text = re.sub(rf"\b([{PREPRO_LETTER}])\s+[{PREPRO_APOSTROPHE}](?=[{PREPRO_LETTER}])", r"\1", text)
    text = re.sub(rf"[{PREPRO_APOSTROPHE}]\s+(?=[{PREPRO_LETTER}])", "", text)
    text = text.translate(str.maketrans("", "", PREPRO_APOSTROPHE))
    text = re.sub(rf"\b([bcdfghjklmnñpqrstvwxzBCDFGHJKLMNÑPQRSTVWXZ])\s+(?=[{PREPRO_LETTER}])", r"\1", text)
    text = text.replace("-", "")
    text = text.translate(str.maketrans("âêîôûÂÊÎÔÛàèìòùÀÈÌÒÙ", "aeiouAEIOUáéíóúÁÉÍÓÚ"))
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", default=INPUT_PATH)
    parser.add_argument("--output-path", default=OUTPUT_PATH)
    parser.add_argument("--text-column", default=TEXT_COLUMN)
    parser.add_argument("--output-column", default=OUTPUT_COLUMN)
    parser.add_argument("--prepro", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.input_path, sep="\t")
    df.dropna(subset=[args.text_column], inplace=True)
    transcription_column = args.text_column
    if args.prepro:
        df["prepro"] = df[args.text_column].apply(prepro_text)
        transcription_column = "prepro"

    silaba = Silaba(build_silaba_args())
    cache = {}
    df[args.output_column] = df[transcription_column].apply(lambda text: transcribe_text(text, silaba, cache))
    df.to_csv(
        args.output_path,
        sep="\t",
        index=False,
        quoting=csv.QUOTE_NONE,
        quotechar=TSV_QUOTECHAR,
        escapechar="\\",
    )

    print(f"Wrote {len(df)} rows to {args.output_path}")
    print(f"Unique word forms transcribed: {len(cache)}")


if __name__ == "__main__":
    main()
