import pandas as pd

from gators_verse import annotate, transcribe
from gators_verse.cli import read_poem_text
from gators_verse.rhyme import rhyme_ending
from gators_verse.transcribe import rhyme_text

# Two abba quatrains from the test corpus, with their gold metre: only the
# metre tells the redondilla (octosyllables) from the cuarteto (hendecasyllables).
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


def make_table(stanza, with_metre=True):
    df = pd.DataFrame(stanza, columns=["text", "metrical_syllables", "stressed_syllables"])
    df.insert(0, "poem_id", 1)
    df.insert(1, "stanza_n", 1)
    df["transcription"] = transcribe(df["text"].tolist())
    if not with_metre:
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


def test_redondilla_and_cuarteto_differ_by_metre():
    results, _, _ = annotate(make_table(REDONDILLA))
    assert results["rhyme"].tolist() == ["a", "b", "b", "a"]
    assert set(results["stanza_type"]) == {"redondilla"}
    results, _, _ = annotate(make_table(CUARTETO))
    assert results["rhyme"].tolist() == ["a", "b", "b", "a"]
    assert set(results["stanza_type"]) == {"cuarteto"}


def test_rhymes_without_metre():
    results, _, _ = annotate(make_table(CUARTETO, with_metre=False))
    assert results["rhyme"].tolist() == ["a", "b", "b", "a"]


def test_annotate_keeps_input_columns_and_order():
    table = make_table(REDONDILLA)
    results, _, _ = annotate(table)
    assert results["text"].tolist() == table["text"].tolist()


def test_read_poem_text_splits_stanzas_on_blank_lines():
    table = read_poem_text("uno\ndous\n\n\ntres\n")
    assert table["stanza_n"].tolist() == [1, 1, 2]
    assert table["text"].tolist() == ["uno", "dous", "tres"]
