# Gators

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24443054.svg)](https://doi.org/10.5281/zenodo.24443054)

Galician Tool for Rhyme and Stanza · 🐊

Gators finds the rhymes of Galician poems and assigns verse, stanza and
poem types. It transcribes each line with [Trasgo](https://github.com/compellit/trasgo),
takes the rhyme from the stressed vowel of the line's last word, groups lines
into assonant and consonant rhymes, and scores each stanza and poem against
the stanza and poem types defined in `src/gators_verse/data/`.

Stanza and poem types depend on meter (an `abba` quatrain is a redondilla in
octosyllables and a cuarteto in hendecasyllables), and rhyme detection is more
accurate on normalized spelling. Both meter and normalization come from
[Gama](https://github.com/compellit/gama), installed as an optional
extra. **Without Gama and without meter in the input, stanza and poem
types will be mostly wrong** (see [Evaluation](#evaluation)): install
`gators-verse[gama]` if you need them.

## Installation

```bash
git clone https://github.com/compellit/gators
cd gators
pip install ".[gama]"     # or: pip install . (without gama-verse)
gama-verse-download       # gama-verse's data files
```

This installs `trasgo` and `gama-verse` from GitHub, as they are not on PyPI yet.

Python 3.10 or later is required.

## Usage

### Command line

A poem in plain text, one verse per line, with a blank line between stanzas:

```bash
gators-verse poem.txt
gators-verse poem.txt -o poem.tsv
cat poem.txt | gators-verse
```

Several poems, or poems with their meter, go in a table (a `.tsv` file) with
one row per verse:

| Column | Content | Required |
|---|---|---|
| `poem_id` | poem identifier | yes |
| `stanza_n` | stanza number; consecutive lines with the same number form a stanza | yes |
| `text` | the verse | yes |
| `metrical_syllables` | syllable count, e.g. `8` | no |
| `stressed_syllables` | stressed syllables, e.g. `3 7`; only used for the experimental `verse_type` | no |

Other column names can be given with `--poem-column`, `--stanza-column`,
`--text-column`, `--syllable-column` and `--stress-column`; other columns are
copied to the output.

With `gama-verse` installed, Gators uses Gama to normalize the spelling of each
poem and, if the input has no syllable count, to scan it. `--no-gama` turns this off.

The syllable count, from the input or from Gama, is used for stanza and
poem types, and to write the rhyme letters of long lines in uppercase. Rhyme
detection does not use stresses: the stressed vowel where the rhyme starts
comes from Trasgo's transcription.

`--stanza-scores` and `--poem-scores` write the score of every stanza and poem
type considered, to see why a type was chosen.

### Output

A TSV with the input columns and:

| Column | Content |
|---|---|
| `normalized_text` | the verse after Gama's spelling normalization (with `gama-verse` only) |
| `transcription` | Trasgo's transcription, used for rhyme |
| `rhyme` | rhyme letter, uppercase for lines of 9 syllables or more (arte maior) when the meter is known; `-` for unrhymed lines |
| `rhyme_ending` | the transcribed ending, from the stressed vowel of the last word |
| `rhyme_vowels` | its stressed and last vowels, compared for assonance |
| `verse_type` | experimental: small subset of verse-line types defined by stress positions, when the stresses match exactly; not evaluated (note that Gama detects a full inventory of line types, independent of Gators) |
| `stanza_rhyme_pattern` | the stanza's rhyme scheme, e.g. `abba` |
| `stanza_expected_pattern` | the scheme of the chosen stanza type |
| `stanza_type`, `stanza_subtype` | stanza type and subtype, also with their `_score` field |
| `poem_type`, `poem_subtype` | poem type and subtype, also with their `_score` field |

How the stanza and poem types are scored, and how to add or change a type, is
described in [`docs/STANZA_AND_POEM_TYPES.md`](docs/STANZA_AND_POEM_TYPES.md).

### Python

```python
from gators_verse import analyze

poem = """Aquel romor de cántigas e risas,
Ir, vir, algarear;
Aquel falar de cousas que pasaron
Y outras que pasarán;
Aquela, en fin, vitalidade inquieta
Xuvenil, tanto mal
Me fixo, que lles dixen:
Ivos e non volvás."""

results, stanza_scores, poem_scores = analyze(poem)
results[["rhyme", "stanza_type"]]   # - a - a - a - a, silva_arromanzada
```

`analyze()` does what the `gators-verse` command does: it takes a plain-text poem or a
DataFrame with the columns above, and uses Gama, when `gama-verse` is installed,
for spelling normalization and meter (`use_gama=False` turns this off). Its two
last steps, `transcribe()` and `annotate()`, can also be called on their own,
for input that already has its transcription.

## Evaluation

On the test corpus (33 poems, 2,188 lines, 255 stanzas with a gold stanza
type), with `evaluation/run_all.sh`:

| Setting | Rhyme F1 (pairwise) | Stanza type accuracy |
|---|---|---|
| Gama normalization, gold meter | 98.14% | 96.47% (246) |
| Gama normalization and meter (end to end) | 98.13% | 96.86% (247) |
| without Gama, no meter | 88.98% | 32.94% (84) |

See [`docs/EVALUATION.md`](docs/EVALUATION.md) for the metrics and the settings,
and [`iaa/README.md`](iaa/README.md) for the agreement between the two rhyme
annotators.

## Tests

```bash
pip install ".[test]"
pytest
```

## Citation

Anxo Alonso Pérez and Pablo Ruiz Fabo (2026). Gators: Galician Tool for Rhyme and Stanza. CiTIUS, Universidade de Santiago de Compostela. https://doi.org/10.5281/zenodo.24443054

## License

Gators is licensed under GPLv3; see [LICENSE](LICENSE).
