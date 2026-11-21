import pandas as pd
import pytest

from gators_verse import analyze, annotate, transcribe
from gators_verse.pipeline import gama_available, read_poem_text
from gators_verse.rhyme import rhyme_ending
from gators_verse.transcription import rhyme_text

# Two abba quatrains from the test corpus, with their gold meter: only the
# meter tells the redondilla (octosyllables) from the cuarteto (hendecasyllables).
REDONDILLA = [
    ("-Ña muller, pilla esa roca", 8, "3 4 5 7"),
    ("e déixate de ir á misa,", 8, "2 7"),
    ("pensa que non tés camisa", 8, "1 4 5 7"),
    ("e fía unha mazaroca.", 8, "2 3 7"),
]
CUARTETO = [
    ("Muitos qu'ás tuas ordes pelearon,", 11, "1 4 6 10"),
    ("E as suas roxas faixas che deberon,", 11, "2 4 6 10"),
    ("En cuanto os sumos grados atingueron,", 11, "4 6 10"),
    ("Po-los pátridos eidos suspiraron.", 11, "3 6 10"),
]


def make_table(stanza, with_meter=True):
    df = pd.DataFrame(stanza, columns=["text", "metrical_syllables", "stressed_syllables"])
    df.insert(0, "poem_id", 1)
    df.insert(1, "stanza_n", 1)
    df["transcription"] = transcribe(df["text"].tolist())
    if not with_meter:
        df = df.drop(columns=["metrical_syllables", "stressed_syllables"])
    return df


def test_rhyme_ending_starts_at_last_stressed_vowel():
    assert rhyme_ending('"ew "bEN "biN es".tar o "mow.tSo') == ("ow.tSo", ["o", "o"])


def test_unstressed_last_word_gets_stress_on_first_syllable():
    # "lua" without its accent: the rhyme must not start in the previous word.
    assert rhyme_ending('mis.te".rjo.sa lu.a')[0] == "u.a"


def test_rhyme_text_keeps_normalization_that_only_adds_accents():
    assert rhyme_text("a fermosa lua", "a fermosa lúa") == "a fermosa lúa"


def test_rhyme_text_rejects_normalization_that_changes_spelling():
    # "camino" -> "camiño" changes the sounds the poet rhymed.
    assert rhyme_text("polo camino", "polo camiño") == "polo camino"


def test_redondilla_and_cuarteto_differ_by_meter():
    results, _, _ = annotate(make_table(REDONDILLA))
    assert results["rhyme"].tolist() == ["a", "b", "b", "a"]
    assert set(results["stanza_type"]) == {"redondilla"}
    results, _, _ = annotate(make_table(CUARTETO))
    assert results["rhyme"].tolist() == ["A", "B", "B", "A"]  # arte maior
    assert set(results["stanza_type"]) == {"cuarteto"}


def test_rhymes_without_meter():
    # Without meter, letters stay lowercase: the line length is unknown.
    results, _, _ = annotate(make_table(CUARTETO, with_meter=False))
    assert results["rhyme"].tolist() == ["a", "b", "b", "a"]


def test_annotate_keeps_input_columns_and_order():
    table = make_table(REDONDILLA)
    results, _, _ = annotate(table)
    assert results["text"].tolist() == table["text"].tolist()


def test_read_poem_text_splits_stanzas_on_blank_lines():
    table = read_poem_text("uno\ndous\n\n\ntres\n")
    assert table["stanza_n"].tolist() == [1, 1, 2]
    assert table["text"].tolist() == ["uno", "dous", "tres"]


def poem_text(stanza):
    return "\n".join(text for text, _, _ in stanza)


def test_analyze_text_without_gama_warns_and_finds_rhymes():
    with pytest.warns(UserWarning, match="no meter"):
        results, _, _ = analyze(poem_text(REDONDILLA), use_gama=False)
    assert results["rhyme"].tolist() == ["a", "b", "b", "a"]


@pytest.mark.skipif(not gama_available(), reason="gama-verse not installed")
def test_analyze_text_with_gama_gets_meter_and_stanza_type():
    results, _, _ = analyze(poem_text(REDONDILLA))
    assert results["metrical_syllables"].tolist() == [8, 8, 8, 8]
    assert set(results["stanza_type"]) == {"redondilla"}


def test_decima_that_is_not_an_espinela_is_a_decima_antiga():
    # "1" in a pattern (abba111111) means that the line rhymes, with any line.
    lines = ["Vou camiñando ao luar", "polo camiño esquecido", "co corazón tan ferido",
             "sen ninguén a quen amar.", "A noite chega silente", "coa súa negra figura,",
             "chea de fonda tristura,", "baixo a lúa transparente,", "e eu sigo o meu carreiro",
             "como un vello romeiro."]
    table = make_table([(line, 8, "7") for line in lines])
    results, _, _ = annotate(table)
    assert "".join(results["rhyme"]) == "abbacddcee"
    assert set(results["stanza_type"]) == {"décima_antiga"}
