"""Phonetic transcription of Galician verse lines with Silaba, for rhyme detection.

main() transcribes a DataFrame column. The web app calls it on the normalised
text that scansion preprocessing already produced; transcribe_with_silaba.py
wraps it for the command line and can run that normalisation itself
(normalize_with_gumper). Normalisation modernises the spelling and restores
written accents ("dia" -> "día", "lua" -> "lúa", "mais" -> "máis"), without
which Silaba misplaces the stress of many nineteenth-century spellings.
For rhyme, rhyme_text() keeps a normalised line only where normalisation just
restored accents on its final word; see there.
"""
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from types import SimpleNamespace

PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parent
SILABA_DIR = WORKSPACE_DIR / "silaba_gl"

sys.path.insert(0, str(SILABA_DIR))

from silaba_py import Silaba, SilabaError  # noqa: E402

TEXT_COLUMN = "running_text"
OUTPUT_COLUMN = "phSilaba"
TSV_QUOTECHAR = "\x07"
GUMPER_PREPROCESSOR_PATH = WORKSPACE_DIR / "preprocessing" / "g2s_client_running_text.py"
GUMPER_PREPROCESSED_RELATIVE_PATH = Path("out_001") / "input_pp_out_norm_spa_001.txt"
CEDILLA_TRANSLATION = str.maketrans("çÇ", "zZ")
CEDILLA_ON_RE = re.compile(r"[çÇ]([oO])([nN][sS]?)\b")
ACUTE_O = {"o": "ó", "O": "Ó"}
PREPRO_LETTER = "A-Za-zÁÉÍÓÚÜÑÏáéíóúüñïÂÊÎÔÛâêîôû"
PREPRO_APOSTROPHE = "'’‘"
NONSTANDARD_VOWEL_TRANSLATION = str.maketrans(
    "âêîôûÂÊÎÔÛàèìòùÀÈÌÒÙ",
    "aeiouAEIOUaeiouAEIOU",
)

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+(?:['’‘][A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+)?")
TOKEN_RE = re.compile(
    r"[A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+(?:['’‘][A-Za-zÁÉÍÓÚÜÑÏáéíóúüñï]+)?|\d+(?:[.,]\d+)?|[^\w\s]"
)


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


# Words stressed on the last syllable whose spelling in the corpus does not
# show it, so Silaba stresses the penultimate ("marfin" read as "márfin").
# Neither normalisation nor rhyme_text() adds the accent; checked in context
# against the rhyme. Some forms stay out: "Verin" and "Crispin" in Garcia
# Ferreiro's Follas are deliberately paroxytone, set against "Verín" and
# "Crispín"; "Ullin" in Pondal scans as 8 either way ("de Ú.llin" with
# dialepha, "de_U.llín" with synalepha) but ends an unrhymed odd line, so the
# usual "Úllin" is kept.
# The accent is added here, after scansion, so scansion still reads these
# words as paroxytone ("Da verde Erin" gets no stress on 4) and its syllable
# counts and rhythm feed the verse and stanza types. Fixing that would mean
# moving the list into the per-word loop of both preprocessing clients
# (g2s_client_running_text.py and g2s_client_running_text_for_api.py), next
# to diacritic_stress, but the list is too specific to this corpus for that,
# and every mid-line occurrence would need checking first ("paris").
FINAL_STRESS_WORDS = {
    "ami": "amí",  # French "mon ami"
    "ceci": "cecí",  # French
    "conocin": "conocín",
    "erin": "erín",
    "gachi": "gachí",
    "marfin": "marfín",
    "nasin": "nasín",
    "oubin": "oubín",
    "paris": "parís",  # the city
}


def add_final_stress(token):
    """Write the accent on a word of FINAL_STRESS_WORDS, keeping its case."""
    accented = FINAL_STRESS_WORDS.get(token.lower())
    if accented is None:
        return token
    if token.isupper() and len(token) > 1:
        return accented.upper()
    if token[0].isupper():
        return accented[0].upper() + accented[1:]
    return accented


def transcribe_token(token, silaba, cache):
    if not WORD_RE.fullmatch(token):
        return token

    key = token.lower()
    if key not in cache:
        try:
            reset_silaba_state(silaba)
            cache[key] = silaba.run(add_final_stress(token))
        except SilabaError:
            cache[key] = "erro"
    return cache[key]


def replace_cedilla(text):
    """Respell the old "ç", which Silaba can't read (it splits the word there).

    It sounds like "z". Words in "-çon(s)" ("coraçon", "devoçon") are stressed
    on the last syllable, which Silaba only knows from a written accent.
    Normalisation leaves "ç" as it is, so this applies to normalised text too.
    """
    text = CEDILLA_ON_RE.sub(
        lambda match: match.group(0)[0].translate(CEDILLA_TRANSLATION)
        + ACUTE_O[match.group(1)]
        + match.group(2),
        text,
    )
    return text.translate(CEDILLA_TRANSLATION)


def transcribe_text(text, silaba, cache):
    # '"' marks stress in Silaba's output, so quotation marks in the verse
    # would read as stress marks (and hide where the rhyme starts).
    text = text.replace('"', "")
    text = replace_cedilla(text)
    text = text.translate(NONSTANDARD_VOWEL_TRANSLATION)
    tokens = TOKEN_RE.findall(text)
    transcribed_tokens = [transcribe_token(token, silaba, cache) for token in tokens]
    return merge_tokens(transcribed_tokens)


def prepro_text(text):
    """Light spelling cleanup for Silaba, used when no normalised text is available."""
    text = re.sub(rf"(?i)q(?:u)?[{PREPRO_APOSTROPHE}]\s*(?=[{PREPRO_LETTER}])", "k", text)
    text = re.sub(rf"(?i)\bq(?:u)?\s+(?=[{PREPRO_LETTER}])", "k", text)
    text = re.sub(
        rf"\b([{PREPRO_LETTER}])\s+[{PREPRO_APOSTROPHE}](?=[{PREPRO_LETTER}])", r"\1", text
    )
    text = re.sub(rf"[{PREPRO_APOSTROPHE}]\s+(?=[{PREPRO_LETTER}])", "", text)
    text = text.translate(str.maketrans("", "", PREPRO_APOSTROPHE))
    text = re.sub(
        rf"\b([bcdfghjklmnñpqrstvwxzBCDFGHJKLMNÑPQRSTVWXZ])\s+(?=[{PREPRO_LETTER}])",
        r"\1",
        text,
    )
    text = text.replace("-", "")
    text = text.translate(NONSTANDARD_VOWEL_TRANSLATION)
    return text


# Combining marks that normalisation may add or remove; the tilde is kept,
# so "ñ" and "n" stay different letters.
ACCENT_MARKS = {"\u0300", "\u0301", "\u0302", "\u0308"}
FINAL_WORD_RE = re.compile(r"[^\W\d_]+(?=[^\w]*$)")
VOWEL_GROUP_RE = re.compile(r"[aeiouáéíóúàèìòùâêîôûäëïöü]+")
# Nouns that normalisation reads as a verb plus clitic ("escríbano").
WRONG_ACCENT_WORDS = {"escribano", "escribanos", "sobrana",
                      "rosales", "castelas", "paletos", "ponteareas",
                      "raxas", "trives", "rispeta", "rispeto"}


def strip_accents(word):
    decomposed = unicodedata.normalize("NFD", word.casefold())
    return unicodedata.normalize(
        "NFC", "".join(char for char in decomposed if char not in ACCENT_MARKS)
    )


def final_word(text):
    match = FINAL_WORD_RE.search(text)
    return match.group(0) if match else ""


def accepts_normalized_word(original, normalized):
    """Tell whether a normalised final word can be used for rhyme.

    Only when it differs from the original by accents alone ("dia" ->
    "día", "corazon" -> "corazón"): normalisation also modernises spellings
    ("Rosiña" -> "Rosina", "camino" -> "camiño"), which changes the sounds
    the poet rhymed, and drops words after some elisions ("rezarll'ést'igrexa"
    -> "rezarlle ést"). Added accents that are wrong in this corpus are
    rejected too: on a final -a/-e/-o of a longer word, mostly proper nouns
    ("Compostela" -> "compostelá", "Limia" -> "limiá"), and in words in -nte
    ("pesante" -> "pésante", "somente" -> "sómente").
    """
    original = original.casefold()
    normalized = normalized.casefold()
    if not original or strip_accents(original) != strip_accents(normalized):
        return False
    if original == normalized:
        return True
    if strip_accents(original) in WRONG_ACCENT_WORDS:
        return False
    if normalized.endswith("nte"):
        return False
    if normalized[-1] in "áéó" and len(VOWEL_GROUP_RE.findall(normalized)) > 1:
        return False
    if is_wrong_preterite_accent(original, normalized):
        return False
    return True


def is_wrong_preterite_accent(original, normalized):
    """Tell whether normalisation accented a dialectal preterite as verb + clitic.

    Dialectal third-person plural preterites in -ano/-eno ("levano" =
    "levaron", "dixeno" = "dixeron") are stressed on the a or e, and poets
    rhyme them so ("tirano" : "levano", "notano" : "castillano"). They are
    not in the normaliser's vocabulary, which lists verbs with enclitic
    pronouns, so it picks one of those, one accent away ("leva" + "no" ->
    "lévano", "nota" + "no" -> "nótano"). An added accent with two or more
    vowels after it, on a word in -ano/-eno, is therefore not used for rhyme.
    Real proparoxytones in -ano written without their accent ("platano",
    "organo") would be misread, but none ends a line in the corpus. Vowels
    are counted one by one after the accent, since the accented vowel may
    stand in hiatus ("alumeano" -> "aluméano").
    """
    if not original.endswith(("ano", "eno")) or original != strip_accents(original):
        return False
    accented = [index for index, char in enumerate(normalized) if strip_accents(char) != char]
    if not accented:
        return False
    following = normalized[accented[-1] + 1:]
    return len(re.findall(r"[aeiou]", following)) >= 2


def rhyme_text(original, normalized):
    """Choose the text of a line to transcribe for rhyme.

    The normalised line when its final word passes accepts_normalized_word(),
    otherwise the original line after the light cleanup (prepro_text).
    """
    if accepts_normalized_word(final_word(original), final_word(normalized)):
        return normalized
    return prepro_text(original)


def normalize_with_gumper(texts, preprocessor_path=GUMPER_PREPROCESSOR_PATH):
    """Normalise lines with the running-text preprocessing used for scansion.

    Runs preprocessing/g2s_client_running_text.py in a subprocess, which loads
    its language model on every call: fine for batch runs, too slow for the
    web app, which gets the same text from the preprocessing service instead.
    Returns one normalised line per input line.
    """
    preprocessor_path = Path(preprocessor_path)
    if not preprocessor_path.exists():
        raise FileNotFoundError(f"Gumper preprocessing script not found: {preprocessor_path}")

    texts = list(texts)
    with tempfile.TemporaryDirectory(prefix="silaba-gumper-prepro-") as tmp:
        work_dir = Path(tmp)
        input_path = work_dir / "input.txt"
        input_path.write_text(
            "\n".join(str(text).strip() for text in texts) + "\n", encoding="utf-8"
        )

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


def main(df, text_column=TEXT_COLUMN, output_column=OUTPUT_COLUMN, prepro=False):
    """Transcribe ``df[text_column]`` into ``df[output_column]``.

    Pass normalised text where available. ``prepro`` applies the light cleanup
    (prepro_text) first, for raw text, and stores the cleaned text in "prepro".
    """
    df.dropna(subset=[text_column], inplace=True)
    transcription_column = text_column
    if prepro:
        df["prepro"] = df[text_column].apply(prepro_text)
        transcription_column = "prepro"

    silaba = Silaba(build_silaba_args())
    cache = {}
    df[output_column] = df[transcription_column].apply(
        lambda text: transcribe_text(text, silaba, cache)
    )

    print(f"Transcribed {len(df)} verses.")
    print(f"Unique word forms transcribed: {len(cache)}")
    return df
