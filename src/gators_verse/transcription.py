"""Phonetic transcription of verse lines with trasgo, for rhyme detection.

Lines are transcribed word by word. Spelling normalization (gama-verse)
modernizes the spelling and restores written accents ("dia" -> "día", "lua" ->
"lúa", "mais" -> "máis"), without which trasgo misplaces the stress of many
nineteenth-century spellings. For rhyme, rhyme_text() keeps a normalized line
only where normalization just restored accents on its final word; otherwise,
and when no normalized text is available, the line gets a light spelling
cleanup (prepro_text).
"""
import functools
import re
import unicodedata

from trasgo import SilabaError, Transcriber

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


def merge_tokens(tokens):
    text = " ".join(tokens)
    text = re.sub(r"\s+([.,!?;:)\]])", r"\1", text)
    text = re.sub(r"([\(\[¡¿])\s+", r"\1", text)
    return text.strip()


# Words stressed on the last syllable whose spelling in the corpus does not
# show it, so trasgo stresses the penultimate ("marfin" read as "márfin").
# Neither normalization nor rhyme_text() adds the accent; checked in context
# against the rhyme. Some forms stay out: "Verin" and "Crispin" in Garcia
# Ferreiro's Follas are deliberately paroxytone, set against "Verín" and
# "Crispín"; "Ullin" in Pondal scans as 8 either way ("de Ú.llin" with
# dialepha, "de_U.llín" with synalepha) but ends an unrhymed odd line, so the
# usual "Úllin" is kept.
# The accent is added here, for transcription only, so scansion (gama-verse)
# still reads these words as paroxytone ("Da verde Erin" gets no stress on 4).
# Moving the list into gama-verse's preprocessing would fix that, but the list
# is too specific to this corpus for that, and every mid-line occurrence would
# need checking first ("paris").
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


TRANSCRIBER = Transcriber(complex_codas=True, thetacism=True, broad=True)


@functools.lru_cache(maxsize=None)


def transcribe_word(word):
    """Transcribe one lowercase word; "erro" if trasgo cannot."""
    try:
        return TRANSCRIBER.word(add_final_stress(word))
    except SilabaError:
        return "erro"


def transcribe_token(token):
    if not WORD_RE.fullmatch(token):
        return token
    return transcribe_word(token.lower())


def replace_cedilla(text):
    """Respell the old "ç", which trasgo can't read (it splits the word there).

    It sounds like "z". Words in "-çon(s)" ("coraçon", "devoçon") are stressed
    on the last syllable, which trasgo only knows from a written accent.
    Normalization leaves "ç" as it is, so this applies to normalized text too.
    """
    text = CEDILLA_ON_RE.sub(
        lambda match: match.group(0)[0].translate(CEDILLA_TRANSLATION)
        + ACUTE_O[match.group(1)]
        + match.group(2),
        text,
    )
    return text.translate(CEDILLA_TRANSLATION)


def transcribe_line(text):
    # '"' marks stress in trasgo's output, so quotation marks in the verse
    # would read as stress marks (and hide where the rhyme starts).
    text = text.replace('"', "")
    text = replace_cedilla(text)
    text = text.translate(NONSTANDARD_VOWEL_TRANSLATION)
    return merge_tokens([transcribe_token(token) for token in TOKEN_RE.findall(text)])


def prepro_text(text):
    """Light spelling cleanup for trasgo, used when no normalized text is available."""
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


# Combining marks that normalization may add or remove; the tilde is kept,
# so "ñ" and "n" stay different letters.
ACCENT_MARKS = {"\u0300", "\u0301", "\u0302", "\u0308"}
FINAL_WORD_RE = re.compile(r"[^\W\d_]+(?=[^\w]*$)")
VOWEL_GROUP_RE = re.compile(r"[aeiouáéíóúàèìòùâêîôûäëïöü]+")
# Nouns that normalization reads as a verb plus clitic ("escríbano").
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
    """Tell whether a normalized final word can be used for rhyme.

    Only when it differs from the original by accents alone ("dia" ->
    "día", "corazon" -> "corazón"): normalization also modernizes spellings
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
    """Tell whether normalization accented a dialectal preterite as verb + clitic.

    Dialectal third-person plural preterites in -ano/-eno ("levano" =
    "levaron", "dixeno" = "dixeron") are stressed on the a or e, and poets
    rhyme them so ("tirano" : "levano", "notano" : "castillano"). They are
    not in the normalizer's vocabulary, which lists verbs with enclitic
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

    The normalized line when its final word passes accepts_normalized_word(),
    otherwise the original line after the light cleanup (prepro_text).
    """
    if accepts_normalized_word(final_word(original), final_word(normalized)):
        return normalized
    return prepro_text(original)


def transcribe(lines, normalized_lines=None):
    """Transcribe verse lines; return one transcription per line.

    ``normalized_lines``, if given, are the same lines after gama-verse's
    spelling normalization; see rhyme_text().
    """
    if normalized_lines is None:
        texts = [prepro_text(line) for line in lines]
    else:
        if len(normalized_lines) != len(lines):
            raise ValueError("lines and normalized_lines differ in length")
        texts = [rhyme_text(line, normalized) for line, normalized in zip(lines, normalized_lines)]
    return [transcribe_line(text) for text in texts]
