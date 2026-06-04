import unicodedata


IPA_PUNCTUATION = ".,!?;:¡¿'’“”\"()[]{}«»"

IPA_SILABA_SAMPA_REPLACEMENTS = [
    ("tʃ", "tS"),
    ("dʒ", "dZ"),
    ("t͡ʃ", "tS"),
    ("d͡ʒ", "dZ"),
    ("ɲ", "J"),
    ("ʎ", "L"),
    ("ŋ", "N"),
    ("ɡ", "g"),
    ("ɣ", "G"),
    ("β", "B"),
    ("ð", "D"),
    ("ʃ", "S"),
    ("ʒ", "Z"),
    ("θ", "T"),
    ("ɫ", "5"),
    ("ɬ", "K"),
    ("χ", "X"),
    ("x", "x"),
    ("r", "R"),
    ("ɾ", "r"),
    ("ʧ", "tS"),
    ("ʤ", "dZ"),
    ("ə", "6"),
    ("ɐ", "6"),
    ("ɛ", "E"),
    ("ɔ", "O"),
    ("ʊ", "U"),
    ("ɪ", "I"),
    ("ˈ", '"'),
    ("ˌ", '"'),
    ("ː", ""),
    ("ˑ", ""),
]

SILABA_SAMPA_IPA_REPLACEMENTS = []
_seen_sampa_symbols = set()
for ipa_symbol, sampa_symbol in IPA_SILABA_SAMPA_REPLACEMENTS:
    if not sampa_symbol or sampa_symbol in _seen_sampa_symbols:
        continue
    SILABA_SAMPA_IPA_REPLACEMENTS.append((sampa_symbol, ipa_symbol))
    _seen_sampa_symbols.add(sampa_symbol)


def ipa_to_silaba_sampa(text: str) -> str:
    value = text.strip()
    if not value:
        return ""

    for wrapper in [("/", "/"), ("[", "]")]:
        if value.startswith(wrapper[0]) and value.endswith(wrapper[1]):
            value = value[1:-1].strip()

    for src, dst in IPA_SILABA_SAMPA_REPLACEMENTS:
        value = value.replace(src, dst)

    # Remove combining IPA diacritics such as a̝, o̞, nasalization overlays, etc.
    value = "".join(
        ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn"
    )

    value = value.replace("̃", "~")
    value = value.replace("‿", "").replace(" ", "")
    value = value.replace("·", ".")
    return value


def silaba_sampa_to_ipa(text: str) -> str:
    value = text.strip()
    if not value:
        return ""

    for src, dst in SILABA_SAMPA_IPA_REPLACEMENTS:
        value = value.replace(src, dst)

    return value


def strip_syllable_dots(text: str) -> str:
    return text.replace(".", "")


def normalize_rhymetagger_ipa(text: str) -> str:
    value = strip_syllable_dots(silaba_sampa_to_ipa(text))
    value = value.replace("_", "")
    value = "".join(ch for ch in value if ch not in IPA_PUNCTUATION)
    return " ".join(value.split())


def collapse_open_close_vowels(text: str) -> str:
    return text.replace("A", "a").replace("E", "e").replace("O", "o")
