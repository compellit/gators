import argparse
import csv
import subprocess
import tempfile
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
GUMPER_PREPROCESSOR_PATH = WORKSPACE_DIR / "galapre" / "preprocessing" / "g2s_client_running_text.py"
GUMPER_PREPROCESSED_RELATIVE_PATH = Path("out_001") / "input_pp_out_norm_spa_001.txt"
PREPRO_LETTER = "A-Za-zÁÉÍÓÚÜÑÏáéíóúüñïÂÊÎÔÛâêîôû"
PREPRO_APOSTROPHE = "'’‘"
NONSTANDARD_VOWEL_TRANSLATION = str.maketrans(
    "âêîôûÂÊÎÔÛàèìòùÀÈÌÒÙ",
    "aeiouAEIOUaeiouAEIOU",
)

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
    text = text.translate(NONSTANDARD_VOWEL_TRANSLATION)
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
    text = text.translate(NONSTANDARD_VOWEL_TRANSLATION)
    return text


def run_gumper_preprocessing(texts, preprocessor_path):
    preprocessor_path = Path(preprocessor_path)
    if not preprocessor_path.exists():
        raise FileNotFoundError(f"Gumper preprocessing script not found: {preprocessor_path}")

    with tempfile.TemporaryDirectory(prefix="silaba-gumper-prepro-") as tmp:
        work_dir = Path(tmp)
        input_path = work_dir / "input.txt"
        input_path.write_text("\n".join(str(text).strip() for text in texts) + "\n", encoding="utf-8")

        subprocess.run(
            [
                sys.executable,
                str(preprocessor_path),
                str(input_path),
                "-p",
                "-d",
                "-n",
                "-s",
                "-b",
                "001",
                "-m",
            ],
            check=True,
            cwd=preprocessor_path.parent,
        )

        output_path = work_dir / GUMPER_PREPROCESSED_RELATIVE_PATH
        lines = output_path.read_text(encoding="utf-8").splitlines()

    if len(lines) != len(texts):
        raise RuntimeError(
            "Gumper preprocessing count mismatch: "
            f"got {len(lines)} rows for {len(texts)} input rows"
        )
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", default=INPUT_PATH)
    parser.add_argument("--output-path", default=OUTPUT_PATH)
    parser.add_argument("--text-column", default=TEXT_COLUMN)
    parser.add_argument("--output-column", default=OUTPUT_COLUMN)
    parser.add_argument(
        "--prepro",
        action="store_true",
        help="Preprocess the text with the same running-text preprocessing used by Gumper.",
    )
    parser.add_argument(
        "--silaba-prepro",
        action="store_true",
        help="Use the older Silaba-specific transcription cleanup instead of Gumper preprocessing.",
    )
    parser.add_argument(
        "--gumper-preprocessor-path",
        type=Path,
        default=GUMPER_PREPROCESSOR_PATH,
        help="Path to preprocessing/g2s_client_running_text.py.",
    )
    args = parser.parse_args()

    if args.prepro and args.silaba_prepro:
        raise SystemExit("Choose only one preprocessing mode: --prepro or --silaba-prepro.")

    df = pd.read_csv(args.input_path, sep="\t")
    df.dropna(subset=[args.text_column], inplace=True)
    transcription_column = args.text_column
    if args.prepro:
        df["prepro"] = run_gumper_preprocessing(df[args.text_column], args.gumper_preprocessor_path)
        transcription_column = "prepro"
    elif args.silaba_prepro:
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
