# GATORS

Galician Tool for Rhyme and Stanza.

gators-verse finds the rhymes of Galician poems and assigns verse, stanza and
poem types. It transcribes each line with [trasgo](https://github.com/compellit/trasgo),
takes the rhyme from the stressed vowel of the line's last word, groups lines
into assonant and consonant rhymes, and scores each stanza and poem against
the stanza and poem types defined in `src/gators_verse/data/`.

Stanza and poem types depend on metre (an `abba` quatrain is a redondilla in
octosyllables and a cuarteto in hendecasyllables), and rhyme detection is more
accurate on normalized spelling. Both come from
[gama-verse](https://github.com/compellit/gama), installed as an optional
extra. **Without gama-verse and without metre in the input, stanza and poem
types are mostly wrong** (see [Evaluation](#evaluation)): install
`gators-verse[gama]` if you need them.

## Installation

trasgo and gama-verse are not on PyPI yet, so install them from GitHub first:

```bash
pip install git+https://github.com/compellit/trasgo
pip install git+https://github.com/compellit/gama       # optional, see above
gama-verse-download                                      # gama-verse's data files

git clone https://github.com/compellit/gators
cd gators
pip install ".[gama]"            # or: pip install . (without gama-verse)
```

Python 3.10 or later is required.

## Usage

### Command line

A poem in plain text, one verse per line, with a blank line between stanzas:

```bash
gators-verse poem.txt
gators-verse poem.txt -o poem.tsv
cat poem.txt | gators-verse
```

Several poems, or poems with their metre, go in a table (a `.tsv` file) with
one row per verse:

| Column | Content | Required |
|---|---|---|
| `poem_id` | poem identifier | yes |
| `stanza_n` | stanza number; consecutive lines with the same number form a stanza | yes |
| `text` | the verse | yes |
| `metrical_syllables` | syllable count, e.g. `8` | no |
| `stressed_syllables` | stressed syllables, e.g. `3 7` | no |

Other column names can be given with `--poem-column`, `--stanza-column`,
`--text-column`, `--syllable-column` and `--stress-column`; other columns are
copied to the output.

With gama-verse installed, gators-verse normalizes the spelling of each poem
and, if the input has no metre columns, scans it. `--no-gama`
turns this off.

The syllable count from gama is used for stanza and poem types. Rhyme does not use gama's stress patterns: the stressed vowel where the rhyme
starts comes from trasgo's transcription.

`--stanza-scores` and `--poem-scores` write the score of every stanza and poem
type considered, to see why a type was chosen.

### Output

A TSV with the input columns and:

| Column | Content |
|---|---|
| `normalized_text` | the verse after gama-verse's spelling normalization (with gama-verse only) |
| `transcription` | trasgo's transcription, used for rhyme |
| `rhyme` | rhyme letter, uppercase for lines of 9 syllables or more (arte maior) when the metre is known; `-` for unrhymed lines |
| `rhyme_ending` | the transcribed ending, from the stressed vowel of the last word |
| `rhyme_vowels` | its stressed and last vowels, compared for assonance |
| `verse_type` | experimental: verse types defined by stress positions (gaita galega, endecasílabo types), when the stresses match exactly; not evaluated |
| `stanza_rhyme_pattern` | the stanza's rhyme scheme, e.g. `abba` |
| `stanza_expected_pattern` | the scheme of the chosen stanza type |
| `stanza_type`, `stanza_subtype` | stanza type and subtype, with their `_probability` |
| `poem_type`, `poem_subtype` | poem type and subtype, with their `_probability` |

How the stanza and poem types are scored is described in
[docs/STANZA_PATTERN_SCORING.md](docs/STANZA_PATTERN_SCORING.md) and
[docs/POEM_TYPE_SCORING.md](docs/POEM_TYPE_SCORING.md).

### Python

```python
import pandas as pd
from gators_verse import annotate, transcribe

poem = pd.DataFrame({
    "poem_id": 1,
    "stanza_n": 1,
    "text": ["-Ña muller, pilla esa roca", "e déixate de ir á misa,",
             "pensa que non tés camisa", "e fía unha mazaroca."],
    "metrical_syllables": [8, 8, 8, 8],
    "stressed_syllables": ["3 4 5 7", "2 7", "1 4 5 7", "2 3 7"],
})
poem["transcription"] = transcribe(poem["text"].tolist())
results, stanza_scores, poem_scores = annotate(poem)
results[["text", "rhyme", "stanza_type"]]   # a b b a, redondilla
```

`transcribe()` takes the normalized lines as a second argument, if you have them.

## Evaluation

On the test corpus (33 poems, 2,188 lines, 255 stanzas with a gold stanza
type), with `evaluation/run_all.sh`:

| Setting | Rhyme F1 (pairwise) | Stanza type accuracy |
|---|---|---|
| gama-verse normalization, gold metre | 98.14% | 96.47% (246) |
| gama-verse normalization and metre (end to end) | 98.13% | 96.86% (247) |
| without gama-verse, no metre | 88.98% | 32.94% (84) |

See [docs/EVALUATION.md](docs/EVALUATION.md) for the metrics and the settings,
and [iaa/README.md](iaa/README.md) for the agreement between the two rhyme
annotators.

## Tests

```bash
pip install ".[test]"
pytest
```

## Authors

Anxo Alonso Pérez and Pablo Ruiz Fabo.
