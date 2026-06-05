import unicodedata


IPA_PUNCTUATION = ".,!?;:¡¿'’“”\"()[]{}«»"
IPA_SEMIVOWELS = set("jw")
IPA_VOWELS = set("aeiouáéíóúàèìòùâêîôûãẽĩõũäëïöüɑɐəɛɜɞɨɪɯɵøœɔʊʌæɒɶ")
IPA_VOWELS_AND_SEMIVOWELS = IPA_VOWELS | IPA_SEMIVOWELS

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


def strip_stressed_onset(ipa_word: str) -> str:
    if not ipa_word:
        return ipa_word

    stress_idx = ipa_word.rfind("ˈ")
    if stress_idx == -1:
        stress_idx = 0
        search_start = 0
    else:
        search_start = stress_idx + 1

    for idx in range(search_start, len(ipa_word)):
        if ipa_word[idx] in IPA_VOWELS_AND_SEMIVOWELS:
            return ipa_word[:stress_idx] + "ˈ" + ipa_word[idx:]

    return ipa_word


def normalize_rhymetagger_ipa_from_final_nucleus(text: str) -> str:
    value = normalize_rhymetagger_ipa(text)
    tokens = value.split()
    if not tokens:
        return value

    tokens[-1] = strip_stressed_onset(tokens[-1])
    return " ".join(tokens)


def is_ipa_consonant(ch: str) -> bool:
    return ch not in IPA_VOWELS_AND_SEMIVOWELS and ch not in {"ˈ", "ˌ", "ː", "ˑ"}


def final_word_to_nucleus_only(ipa_word: str) -> str:
    if not ipa_word:
        return ipa_word

    stress_idx = ipa_word.rfind("ˈ")
    if stress_idx == -1:
        prefix = ""
        tail = ipa_word
    else:
        prefix = ipa_word[:stress_idx]
        tail = ipa_word[stress_idx + 1:]

    kept = [ch for ch in tail if ch in IPA_VOWELS]

    if not kept:
        return ipa_word

    return prefix + "ˈ" + "".join(kept)


def normalize_rhymetagger_ipa_nucleus_only(text: str) -> str:
    value = normalize_rhymetagger_ipa(text)
    tokens = value.split()
    if not tokens:
        return value

    tokens[-1] = final_word_to_nucleus_only(tokens[-1])
    return " ".join(tokens)


def collapse_open_close_vowels(text: str) -> str:
    return text.replace("A", "a").replace("E", "e").replace("O", "o")
