# rhyme-gl-wk

Utilities for assigning Galician rhyme labels and stanza-pattern metadata from
preprocessed verse data.

The main script is `rhyme.py`. It reads a TSV of verses, groups rows by poem and
stanza, extracts rhyme tails from phonetic/syllabified text, detects assonant
and consonant rhyme groups, chooses a final rhyme label per verse, and optionally
scores stanza types using `data/stanza_patterns.json` and poem types using
`data/poem_patterns.json`.

## Requirements

Install the Python dependencies used by `rhyme.py`:

```bash
pip install pandas regex
```

## Input Data

By default, `rhyme.py` reads:

```text
data/gl-prepro-35k-silaba.tsv
```

The default column names are:

```text
poem_id       poem identifier
stanza_n      stanza identifier inside the poem
verse_text    original verse text
phSilaba      phonetic/syllabified representation
rhyme         optional gold rhyme label, copied to the output when present
```

The script can also use a syllable-count column for metre-aware stanza scoring.
If `--syllable-column` is not supplied, it tries these names in order:

```text
nbSyll
nbSG
syllables
num_silabas
```

The script can also use a rhythmic-accent column for verse-type tagging. If
`--rhythm-column` is not supplied, it tries these names in order:

```text
gprMet
meterNbr
gprMetNoA
```

Verse-type tags are assigned only for perfect rhythmic matches. For
`gaita_galega` lines shorter than 10 syllables, the tag is kept only when the
line can be assigned to a non-overlapping adjacent pair in the same stanza where
both lines are shorter than 10 syllables and match a `gaita_galega` rhythm.

Poem-type scoring uses `data/poem_patterns.json` by default. To use another
file, pass:

```bash
--poem-patterns-path path/to/poem_patterns.json
```

Poem types are output only when the best poem-type probability is at least
`0.8` by default. Change this with:

```bash
--poem-type-min-probability 0.75
```

## Running

From this directory:

```bash
python rhyme.py
```

This writes the default output:

```text
data/test_results_rhyme.tsv
```

To choose explicit input and output paths:

```bash
python rhyme.py \
  --input-path data/gl-prepro-35k-silaba.tsv \
  --results-path data/test_results_rhyme.tsv
```

To process only selected poems:

```bash
python rhyme.py --poem-ids 1,2,3
```

To use non-default column names:

```bash
python rhyme.py \
  --input-path my_verses.tsv \
  --poem-column workId \
  --stanza-column stanzaNbr \
  --verse-column gumperLine \
  --ph-column phSilaba \
  --rhyme-column rhyme \
  --results-path my_rhyme_results.tsv
```

## Stanza Patterns

`rhyme.py` loads stanza definitions from:

```text
data/stanza_patterns.json
```

These definitions help with two tasks:

- disambiguating assonant vs. consonant rhyme when both are plausible
- assigning stanza fields such as `stanza_type`, `stanza_subtype`, and their
  probabilities

Use a different pattern file with:

```bash
python rhyme.py --stanza-patterns-path data/stanza_patterns.json
```

Disable predefined stanza-pattern evidence by pointing to a missing or empty
path.

The stanza-pattern scoring design is documented in:

```text
STANZA_PATTERN_SCORING.md
```

## Output

The output TSV keeps the poem, stanza, verse text, and optional gold rhyme
column, then adds predicted rhyme and stanza fields.

Important output columns include:

```text
letter                         final rhyme label for the verse
rima                           extracted rhyme tail
vogais                         vowel signature used for assonance
asonante                       assonant group id or false/blank
consonante                     consonant group id or false/blank
final                          selected internal final group
final_probability              probability used when resolving uncertain groups
chosen_source                  asonante or consonante
asonante_pattern               candidate stanza rhyme pattern from assonance
consonante_pattern             candidate stanza rhyme pattern from consonance
asonante_probability           combined assonant probability
consonante_probability         combined consonant probability
verse_type                     rhythmic verse type, only for perfect matches
observed_rhythm                observed rhythmic accents from gprMet/meterNbr
expected_rhythm                required and optional accents for verse_type
retrouso                       repeated verse/refrain marker
poem_type                      selected poem type
poem_type_probability          poem type probability
poem_observed_pattern          full-poem observed rhyme pattern
poem_expected_pattern          expected full-poem rhyme pattern
poem_pattern_similarity        poem rhyme-pattern component
poem_metre_similarity          poem metre component
poem_rhyme_type_similarity     poem rhyme-type component
poem_stanza_type_similarity    poem stanza-type component
poem_refrain_similarity        poem refrain/retrouso component
poem_stanza_length_similarity  poem stanza-length component
stanza_type                    selected broad stanza type
stanza_type_probability        local stanza probability
stanza_type_probability_poem   poem-level support for the selected type
stanza_subtype                 selected subtype, when any
observed_pattern               final observed stanza rhyme pattern
expected_pattern               best matching predefined pattern
observed_metre                 observed syllable counts when available
expected_metre                 expected metre from the selected pattern entry
pattern_similarity             rhyme-pattern similarity component
metre_similarity               metre similarity component
rhyme_type_similarity          assonant/consonant type similarity component
```

`letter` is usually the column to use as the predicted rhyme tag in downstream
evaluation or interfaces. Unrhymed lines are written as `-`.

## Evaluation

Use `evaluate_rhyme_tags.py` to compare predicted labels against a gold column.
By default it uses `letter` as the prediction column and chooses `gold` or
`rhyme` as the gold column.

Example:

```bash
python evaluate_rhyme_tags.py \
  data/test_results_rhyme.tsv \
  --pred-column letter \
  --gold-column rhyme \
  --group-column poem_id \
  --pairs-path data/rhyme_pairs.tsv \
  --summary-path data/summary.tsv
```

The evaluator computes pairwise same-rhyme metrics inside each poem or requested
group. This is useful because rhyme labels are arbitrary within a poem: what
matters is whether two lines are predicted to rhyme with each other.
