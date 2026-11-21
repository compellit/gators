# Stanza and poem types

gators-verse assigns a stanza type to each stanza and a poem type to each poem
by scoring them against the entries of two files:

- `src/gators_verse/data/stanza_patterns.json` (50 stanza types)
- `src/gators_verse/data/poem_patterns.json` (10 poem types)

Each entry describes one type: its rhyme scheme, meter, rhyme type, and, for
poems, the stanza types and counts it expects. Every entry gets a score
between 0 and 1, and the best one is chosen. The score is an average of
similarities, not a probability: the scores of competing types do not add up
to 1, and they are not calibrated.

To add a type or change one, edit these files; no code changes are needed.

## Rhyme schemes

Observed schemes (`stanza_rhyme_pattern` in the output) have one letter per
line, the same letter for lines that rhyme together, and `-` for lines that
rhyme with nothing in the stanza.

Expected schemes (`patterns` in the entries) can also use:

| Symbol | Meaning |
|---|---|
| a letter | lines with the same letter rhyme together; lines with different letters do not rhyme |
| `-` | free: the line is not checked |
| `0` | the line must not rhyme |
| `1` | the line must rhyme |
| `*` | any scheme: the rhyme scheme is not scored |

An entry can list several `patterns`; the one that gives the best score is
used.

## Stanza types

### Which entries are candidates

An entry is a candidate for a stanza when:

- the stanza has `stanza_length` lines, or, for entries with
  `repeat_pattern: true`, at least `min_verses` lines (by default, the
  length of the pattern), the pattern being repeated to the stanza's length
  (`-a` gives `-a-a-a...`);
- its meter similarity is at least `min_meter_similarity`, when the entry
  has one;
- its rhyme scheme similarity is at least `min_pattern_similarity`, when the
  entry has one.

### Score

The score is the average of the following similarities, leaving out those
that do not apply (an entry without meter, a stanza without meter in the
input, a `*` scheme...):

- **Rhyme scheme**: the share of checks that the observed scheme passes. There
  is one check for each line marked `0` or `1`, and one for each pair of lines
  with letters in the expected scheme (rhyme or no rhyme).
- **Meter**: see [Meter](#meter).
- **Rhyme type**: the share of expected rhyming pairs whose rhyme is of the
  expected type, `asonante` or `consonante` (`rhyme_kind`, or `rhymes` for a
  type per letter, such as `{"a": "both", "b": "asonante"}`). Pairs expected
  as `both` are not checked. Two lines rhyme in consonance when their whole
  rhyme endings are the same.
- **Verse types**: 1 if the lines' `verse_type` values are exactly those in
  `verse_types`, otherwise 0. No entry uses it at present (verse types are
  experimental).

### Two rounds

Stanza types are chosen in two rounds, so that the types found in the rest of
the poem count:

1. Each stanza's best-scoring type is found.
2. For each type, the poem score is the share of the poem's stanzas that won
   it in the first round. For a type that won no stanza, it is
   `1 / (number of stanzas + number of candidate types for stanzas of that length)`.
   Each candidate's final score is the average of its own score and its poem
   score, and the best one is chosen.

The output's `stanza_type_score` is this final score. There is no minimum:
the best type is always output, and a stanza without candidates gets no type.
`--stanza-scores` shows both parts (`score`, `score_poem`) and the final score
(`score_with_poem`).

### Subtypes and refinements

Two keys relate an entry to a broader type:

- `parent_type`: the entry is a subtype. If it wins, the output has the
  parent as `stanza_type` and the entry as `stanza_subtype`. If the parent
  wins, its best subtype is added as `stanza_subtype` when it scores at least
  0.8. An entry can compare another score instead, with
  `subtype_selection_component` (e.g. `meter_similarity`) and
  `subtype_selection_threshold`.
- `refines_type`: the entry replaces the broader type (one or a list). If the
  broader type wins and the refinement scores at least 0.8, the refinement is
  output as `stanza_type`. For example, `cantar` refines `romance`: an
  octosyllabic `-a-a` quatrain that wins as `romance` is output as `cantar`.

### Meter

`meter` is a list of syllable counts. A line's similarity to an expected count
is the smaller count divided by the larger (8 against 11: 8/11 = 0.73), and
the stanza's meter similarity is the average over its lines. How the list is
read depends on `meter_kind` and `repeat_meter`:

| Keys | Meaning |
|---|---|
| `meter: [11, 11, 11, 5]` | the counts of each line, in order |
| `meter: [8], repeat_meter: true` | every line has 8 syllables |
| `meter: [9], meter_kind: "min"` | every line has at least 9 syllables |
| `meter: [8], meter_kind: "max"` | every line has at most 8 syllables |
| `meter: [7, 11], meter_kind: "range"` | every line has from 7 to 11 syllables |
| `meter: [7, 11], meter_kind: "mixed"` | every line has 7 or 11 syllables, with both counts present |

For `mixed`, each line is compared with its closest count, and the
similarity is 0 if more than 80% of the lines are closest to the same count
(a stanza of hendecasyllables is not a mix of 7 and 11).

### Rhyme detection

The stanza types also help rhyme detection. When the lines of a stanza can be
grouped by assonance or by consonance, both resulting schemes are scored
against the stanza entries (rhyme scheme, meter and rhyme type), and the
score is part of the choice. `detection_rhyme_kind` replaces `rhyme_kind` in
this step only.

## Poem types

### Which entries are candidates

An entry is a candidate when the poem has at least `min_verses` lines and,
with `length_multiple`, a number of lines divisible by it.

### Score

The score is the average of the similarities that apply:

| Similarity | Compares | Keys |
|---|---|---|
| `pattern_similarity` | the rhyme scheme of the whole poem | `patterns`, `repeat_pattern` |
| `meter_similarity` | the syllable counts of all lines, as for stanzas | `meter`, `meter_kind`, `repeat_meter` |
| `rhyme_type_similarity` | the rhyme types, as for stanzas | `rhyme_kind`, `rhymes` |
| `stanza_type_similarity` | the share of stanzas of one type, or the stanza types in order | `stanza_type`, or `stanza_types` (a list of allowed types per stanza) and `extra_stanza_type` |
| `refrain_similarity` | refrains at given positions | `refrain` |
| `stanza_length_similarity` | the number of lines of each stanza | `stanza_lengths`, `extra_stanza_length` |
| `verse_count_similarity` | the number of lines (smaller / larger) | `verse_count` |
| `stanza_count_similarity` | the number of stanzas (smaller / larger) | `stanza_count`, or `min_stanza_count` |

`extra_stanza_type` and `extra_stanza_length` describe stanzas after those
listed, as in the `soneto_con_estrambote`.

A line is a refrain when its text, ignoring case and punctuation, occurs more
than once in the poem. `refrain.positions` gives the line numbers within each
stanza (or each unit of `length_multiple` lines, in a one-stanza poem) that
must be refrains; with `repeat_across_stanzas`, they must also have the same
text across stanzas.

### Hard requirements

The score is 0, whatever the other similarities, when:

- the entry has `stanza_lengths` and the stanza lengths do not match it;
- the entry has a `refrain` with `required: true` and the refrains do not
  match it;
- one of the similarities listed in `required_components` (`pattern`,
  `meter`, `rhyme_type`, `stanza_type`) is not exactly 1. The haiku uses it:
  without it, any three-line poem would get perfect counts.

### Output

The best entry is output when it scores at least 0.8; `parent_type` and
`refines_type` work as for stanzas. Below 0.8, the poem type is:

- the stanza type, for a one-stanza poem;
- `Serie de` and the stanza type, when all stanzas have the same type;
- `-` otherwise.

`set_stanza_type` replaces the stanza type of every line when the entry is
output (the haiku sets it to `haiku`).

## Other keys

`notes` and `sources` document an entry (definitions, references, why a
threshold was chosen); they do not affect the scores.

## Score files

`--stanza-scores` and `--poem-scores` write one row for each candidate entry,
with its similarities, its observed and expected scheme and meter, and
`selected`, whether it was output. They show why a type was or was not
chosen.
