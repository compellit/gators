# Stanza and poem types

Gators assigns a stanza type to each stanza and a poem type to each poem
by scoring them against the entries of two files:

- `src/gators_verse/data/stanza_patterns.json` (49 stanza types, in 50
  entries: `ovillejo` has two)
- `src/gators_verse/data/poem_patterns.json` (10 poem types)

Each entry describes one type: its rhyme scheme, meter, rhyme type, and, for
poems, the stanza types and counts it expects. Every entry gets a score
between 0 and 1, and the best one is chosen. The score is an average of
similarities, not a probability: the scores of competing types do not add up
to 1, and they are not calibrated.

To add a type or change one, edit these files; no code changes are needed.

## Types

The tables summarize the entries; the files are the reference. "Syllables"
reads as in [Meter](#meter): "up to 8" is `meter_kind: "max"`, "9 or more"
`"min"`, "7 and 11" `"mixed"`, and "7-5-7-5" gives the count of each line.
A scheme marked "any" is not scored. Subtypes and refinements are explained in
[Subtypes and refinements](#subtypes-and-refinements).

The definitions are based on Domínguez Caparrós (2014), Paraíso (2000),
Rodríguez Fer (1991) and Jauralde Pou (2020); see [References](#references).
The `sources` and `notes` of an entry give the pages or sections it follows,
and which work was preferred where they disagree.


### Stanza types

| Stanza type | Lines | Syllables | Rhyme scheme | Rhyme | Relation |
|---|---|---|---|---|---|
| `pareado` | 2 | 3 to 20 | `aa` | either |  |
| `tercerilla` | 3 | up to 8 | `a-a` | consonant |  |
| `terceto` | 3 | 9 or more | `-aa`, `a-a`, `aa-` | consonant |  |
| `soledad` | 3 | 8 | `a-a` | assonant |  |
| `terceto_monorrimo` | 3 | 9 or more | `aaa` | consonant |  |
| `cantar` | 4 | up to 8 | `-a-a` | either | refines `romance`, `romancillo` |
| `cuaderna_vía` | 4 | 14 | `aaaa` | consonant |  |
| `cuarteta` | 4 | up to 8 | `abab` | consonant | refines `cantar` |
| `cuarteta_asonantada` | 4 | up to 8 | `abab` | assonant | refines `romance`, `romancillo` |
| `cuarteto` | 4 | 9 or more | `abba` | consonant |  |
| `cuarteto_lira` | 4 | 7 and 11 | `abab`, `abba` | either |  |
| `estrofa_francisco_de_la_torre` | 4 | 11-11-11-7 | `----` | any | subtype of `cuarteto_lira` |
| `estrofa_sáfica` | 4 | 11-11-11-5 | `----` | any | subtype of `cuarteto_lira` |
| `estrofa_alcaica` | 4 | 10-10-9-10 | `0000` | any | subtype of `cuarteto_lira` |
| `endecha_real` | 4 | 7-7-7-11 | `-a-a` | assonant |  |
| `redondilla` | 4 | up to 8 | `abba` | either |  |
| `seguidilla` | 4 | 7-5-7-5 | `-a-a` | either | subtype of `cantar` |
| `seguidilla_real` | 4 | 10-6-10-6 | `-a-a` | either |  |
| `seguidilla_xitana` | 4 | 6-6-11-6 | `-a-a` | assonant |  |
| `serventesio` | 4 | 9 or more | `abab` | consonant |  |
| `lira` | 5 | 7 and 11 | `ababb` | consonant |  |
| `quinteto` | 5 | 9 or more | 5 schemes, e.g. `aabab` | consonant |  |
| `quintilla` | 5 | up to 8 | 5 schemes, e.g. `aabab` | consonant |  |
| `sexteto` | 6 | 9 or more | any | consonant |  |
| `sexta_rima` | 6 | 11 | `aabcbc`, `aabccb`, `ababcc` | consonant | subtype of `sexteto` |
| `sexteto_lira` | 6 | 7 and 11 | any | consonant | subtype of `sexteto` |
| `sextilla` | 6 | up to 8 | any | consonant |  |
| `estrofa_manriqueña` | 6 | 8-8-4-8-8-4 | `abcabc` | consonant | subtype of `sextilla` |
| `copla_mixta` | 7 | up to 8 | `abbacca` | consonant |  |
| `seguidilla_composta` | 7 | 7-5-7-5-5-7-5 | `-a-ab-b` | either | subtype of `setina` |
| `sétima` | 7 | 9 or more | any | any |  |
| `sétima_lira` | 7 | 7 and 11 | any | consonant | subtype of `sétima` |
| `setina` | 7 | up to 8 | any | any |  |
| `copla_arte_maior` | 8 | 9 or more | 8 schemes, e.g. `ababbaab` | consonant | subtype of `oitava` |
| `copla_arte_menor` | 8 | up to 8 | 24 schemes, e.g. `abababab` | consonant | subtype of `octavilla` |
| `copla_castelá` | 8 | 8 | 4 schemes, e.g. `ababcdcd` | consonant | subtype of `octavilla` |
| `octavilla` | 8 | up to 8 | any | either |  |
| `oitava` | 8 | 9 or more | any | any |  |
| `oitava_real` | 8 | 11 | `abababcc` | consonant | subtype of `oitava` |
| `novena` | 9 | any | any | any |  |
| `copla_real` | 10 | 8 | 25 schemes, e.g. `aababccdcd` | consonant | refines `décima_antiga` |
| `décima_antiga` | 10 | 8 | 4 schemes, e.g. `abab111111` | consonant |  |
| `espinela` | 10 | 8 | `abbaaccddc` | consonant | refines `décima_antiga` |
| `ovillejo` | 10 | 8-4-8-4-8-4-8-8-8-8 or 8-3-8-3-8-3-8-8-8-8 | `aabbcccddc` | consonant |  |
| `seguidilla_chamberga` | 10 | 7-5-7-5-3-7-3-7-3-7 | `-a-abbccdd` | per rhyme |  |
| `romance` | 4 or more | 8 | `-a` repeated | assonant |  |
| `romancillo` | 4 or more | up to 7 | `-a` repeated | assonant | refines `octavilla`, `sextilla` |
| `romance_arte_maior` | 4 or more | 9 or more | `-a` repeated | assonant | refines `oitava`, `sexteto` |
| `silva_arromanzada` | 4 or more | 7 and 11 | `-a` repeated | assonant |  |

### Poem types

| Poem type | Lines | Stanzas | Syllables | Rhyme |
|---|---|---|---|---|
| `haiku` | 3 | one, 3 lines | 5-7-5 | none |
| `romance` | 4 or more, even | `romance` | 8 | assonant |
| `romancillo` | 4 or more, even | `romancillo` | up to 7 | assonant |
| `romance_heroico` | 4 or more, even | `romance_arte_maior` | 9 or more | assonant |
| `silva` | 2 or more | any | 7 and 11 | consonant |
| `silva_arromanzada` | 4 or more | `silva_arromanzada` | 7 and 11 | assonant |
| `soneto` | 14 | 4-4-3-3: `cuarteto` or `serventesio` twice, `terceto` twice | 9 or more | consonant |
| `soneto_con_estrambote` | 17 or more | as `soneto`, then `terceto` | 9 or more | consonant |
| `sonetillo` | 14 | 4-4-3-3: `redondilla` or `cuarteta` twice, `tercerilla` twice | up to 8 | consonant |
| `cosaute` | 6 or more, multiple of 3 | `aab` repeated, refrain in the third line | any | either |

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

## References

- Domínguez Caparrós, José (2014). *Métrica española*. Madrid: UNED.
- Paraíso, Isabel (2000). *La métrica española en su contexto románico*.
  Madrid: Arco/Libros.
- Rodríguez Fer, Claudio (1991). *Arte literaria*. Vigo: Edicións Xerais de
  Galicia.
- Jauralde Pou, Pablo (2020). *Métrica española*. Madrid: Cátedra.
