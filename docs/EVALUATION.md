# Evaluation

`evaluation/evaluate.py` evaluates the rhyme letters and stanza types that
Gators assigns, against the gold annotation of the test corpus
(`evaluation/test_corpus.tsv`, 33 poems, 2,188 lines). Rhyme detection is
evaluated as a set of relationships between lines rather than by comparing the
letter assigned to each line literally.

`evaluation/run_all.sh` reruns the whole evaluation; see
[Running the evaluation](#running-the-evaluation).

Stanza types were also evaluated on poems from a corpus of Galician poetry that
cannot be redistributed; see [Corpus evaluation](#corpus-evaluation).

## Why rhyme is evaluated pairwise

Rhyme letters are arbitrary within a poem. For example, `abab` and `cdcd`
describe the same rhyme structure even though none of their letters match. The
evaluator therefore converts every rhyme chain into all the pairs of lines
belonging to that chain.

For example, the chain `aaaa` contains six rhyme pairs:

```text
1-2  1-3  1-4  2-3  2-4  3-4
```

Pairs are created only within the same poem. A pair is:

- a true positive (`tp`) when it appears in both prediction and gold;
- a false positive (`fp`) when it appears only in the prediction;
- a false negative (`fn`) when it appears only in gold.

Pairs absent from both are not counted, so there are no true negatives.

Unrhymed lines never form a pair: Gators marks them `-`, and the gold
annotation `0`; an empty cell counts as unrhymed too. Letters are compared
ignoring case, so `A` and `a` are the same rhyme.

## Rhyme metrics

```text
precision = tp / (tp + fp)
recall    = tp / (tp + fn)
f1        = 2 * precision * recall / (precision + recall)
```

Pairwise F1 is the main rhyme result, with precision and recall showing
whether errors come mainly from extra or missed rhymes. None of these needs
true negatives.

Metrics that need true negatives (accuracy, specificity, Cohen's kappa) are
not reported. True negatives would be all the remaining pairs of lines within
a poem, and they would swamp the rest; accuracy would be disproportionately high.

## Stanza evaluation

Lines are grouped by poem and stanza. The first gold stanza type in each stanza
is compared with the first predicted `stanza_type` and `stanza_subtype`. A
stanza is correct when the gold type exactly equals either of them. A stanza
with no predicted type stays in the denominator and counts as wrong
(`stanzas_without_prediction`).

Stanzas whose type in the gold column is `none` or empty are not evaluated. In the test
corpus, `none` means that the stanza is not part of the gold annotation, not
that it should get no stanza type. Of the 368 stanzas in the corpus, 255 have
a gold type and 113 have "none".

```text
stanza_accuracy = stanzas_correct / stanzas
```

This is exact label accuracy. The pattern, meter and other similarity scores
that Gators computes do not contribute to it.

## Running the evaluation

`evaluation/run_all.sh` needs `gators-verse` installed with the `gama` extra, and
`gama-verse`'s data files. It runs three steps:

1. `prepare.py` writes the test corpus as Gators input, with the
   standard column names, to `evaluation/results/input/`. The gold meter
   (`nbSyll`, `meterNbr`) goes into `metrical_syllables` and
   `stressed_syllables`; the gold rhyme letters and stanza types go into
   `gold_rhyme` and `gold_stanza_type`. The corpus's `nbSG` and `gprMet`
   columns are an earlier Gama output and are not used.
2. `gators-verse` annotates the corpus in three settings.
3. `evaluate.py` scores each setting.

| Setting | Spelling normalization | meter |
|---|---|---|
| `gold_meter` | Gama | gold annotation |
| `end_to_end` | Gama | Gama |
| `no_gama` | none (light cleanup only) | none |

`gold_meter` evaluates the rhyme and stanza analysis on its own; `end_to_end`
is what a user gets with `gators-verse[gama]`, and `no_gama` what a user gets
with the base install and no meter in the input.

To evaluate a single results file:

```bash
python evaluation/evaluate.py RESULTS.tsv OUTPUT_DIR
```

The results file must have the columns `poem_id`, `stanza_n`, `line_id`,
`text`, `rhyme`, `gold_rhyme`, `stanza_type`, `stanza_subtype`,
`gold_stanza_type`, `stanza_rhyme_pattern` and `stanza_expected_pattern`, as
written by Gators from `prepare.py`'s input.

## Output files

Each setting's folder in `evaluation/results/` has:

- `results.tsv`: the output of Gators.
- `pairs.tsv`: one row for every pair present in prediction, gold, or both:
  - `line_pair`: identifiers of the two lines;
  - `pred_pair` and `gold_pair`: their labels;
  - `pred_same` and `gold_same`: whether each annotation links the lines;
  - `correct`: whether the two pairwise decisions agree.
- `stanzas.tsv`: one row per evaluated stanza, with the gold and predicted
  types, whether the prediction is correct, and the observed and expected rhyme
  patterns.
- `summary.tsv`: the metrics above, with the counts of poems, lines, pairs and
  stanzas.

## Results on the public test set

| Setting | Rhyme F1 (pairwise) | Stanza type accuracy |
|---|---|---|
| `gold_meter` | 98.14% | 96.47% (246 of 255) |
| `end_to_end` | 98.13% | 96.86% (247 of 255) |
| `no_gama` | 88.98% | 32.94% (84 of 255) |

The public test set covers 18 stanza types, but only 11 with five or more
stanzas.

## Corpus evaluation

### The corpus

The corpus has about 155,000 lines of poetry in Galician (4,736 poems by 108
authors, 1777-1908). It cannot be redistributed, so its annotation and the
scripts that use it are not in this repository. An earlier version of
Gators had tagged the whole corpus with stanza types and scores, which were
used to choose the test poems; the results below are from the current
version.

### Sampled poems

Sampling unit: whole poems of 4 to 80 lines, entirely in Galician, with less
than 30% of their lines in the public test set. Each poem was put in a
confidence bin by the mean score of its stanzas:

| Bin | Mean stanza type score | Poems | Annotated stanzas | Share of sample stanzas | Share of eligible corpus stanzas\* |
|---|---|---|---|---|---|
| low confidence | below 0.75 | 26 | 122 | 41% | 15% |
| mid confidence | 0.75 to 0.95 | 20 | 126 | 43% | 23% |
| high confidence | 0.95 and above | 15 | 48 | 16% | 62% |

\* Eligible corpus stanzas: the stanzas of all the corpus poems that meet the
sampling filters above (4 to 80 lines, entirely in Galician, less than 30% of
their lines in the public test set) and have a stanza type score.

The low and mid bins have a larger share of the sample than of the corpus, on
purpose: high-confidence poems are mostly correct and say little about errors. Within a bin, poems were
taken in turns over their most frequent predicted stanza type, so that
frequent, easy types (`cantar`, `romance`) did not take up the sample, and
there were at most two poems per author.

The 61 poems cover 30 stanza types. Each stanza was annotated with its stanza
type, or `no_type` when no type in Gators's inventory fits it.

### Targeted poems

Sampling by confidence left out some types that are frequent in the corpus. We
added 12 poems for six of them (`romance_arte_maior`, `seguidilla_real`,
`soledad`, `seguidilla`, `copla_real`, `sexta_rima`), chosen among the poems
Gators assigns these types to, with the same filters and at most one poem per
author for each type. Gators finds `sexta_rima` only in poems longer than 80
lines, so the first 13 stanzas of one such poem were used.

These poems were chosen by hand, so they are not a sample of the corpus: they
show how Gators handles these types, and are left out of the corpus estimate.

### Annotation

The annotator saw Gators's prediction for each stanza and confirmed or
corrected it. To check whether seeing the prediction biases the annotation,
12 of the sampled poems (5, 4 and 3 per bin) were annotated without it. On
these, accuracy is 54.2% (72 stanzas), against 81.3% on the others (224
stanzas). The gap comes from four poems, with 30 of the 72 blind stanzas
(42%; 167 of 383 lines), of which Gators gets one right: two whose stanzas
fit no type in the inventory, a `sexteto_lira` with five hendecasyllables and
one heptasyllable, which Gators's rule for mixed meter rejects, and a `lira`
with non-canonical meter. On the other 42 blind stanzas, accuracy is 90.5%.
The blind sample is too small to tell anchoring apart from these poems'
difficulty.

### Scoring

Gators was run end to end (Gama normalization and meter). Scoring follows
[Stanza evaluation](#stanza-evaluation), with three differences:

- Stanzas of a single line are not evaluated.
- A stanza annotated `no_type` is correct only when Gators gives it no type.
  Gators always outputs the best-scoring type when one is possible, so these
  stanzas count as errors, unless a minimum score is required.
- With a minimum score, a type or subtype scoring below it is not output, and
  a stanza left without a type is predicted `no_type`.

### Corpus estimate

Accuracy on the sample is lower than on the corpus as a whole, because the
low and mid bins are over-represented. The estimate weights each bin's
accuracy by that bin's share of the eligible corpus stanzas (the table
above):

```text
estimate = 0.15 * accuracy_low + 0.23 * accuracy_mid + 0.62 * accuracy_high
```

### Results

| Stanza type accuracy | All types | Min. score 0.75 |
|---|---|---|
| **Public test set** (255 stanzas) | 96.9% | 93.3% |
| **Corpus sample**, all (296 stanzas) | 74.7% | 69.6% |
| ↳ low confidence (122 stanzas) | 72.1% | 62.3% |
| ↳ mid confidence (126 stanzas) | 69.0% | 66.7% |
| ↳ high confidence (48 stanzas) | 95.8% | 95.8% |
| **Corpus estimate** | **86.1%** | **84.1%** |
| **Targeted poems** (60 stanzas) | 86.7% | 80.0% |

The public test set is scored here with the corpus rules; it has no `no_type`
stanzas, so only the minimum score changes its result.

A minimum score of 0.75 turns some low-scoring errors into correct `no_type`
predictions, but drops more correct types than that, so accuracy goes down.

On the targeted poems, all 13 `seguidilla`, 9 `soledad`, 7 `sexta_rima` and
6 `seguidilla_real` stanzas are right, and 7 of 9 `romance_arte_maior`. The
other two `romance_arte_maior` stanzas have two lines each and got no type.

The remaining six errors are a single poem: hendecasyllabic quatrains with
the same ó-o assonance in the even lines throughout. Gators tags them
`romance_arte_maior`; they were annotated `no_type`, as quatrains rather than
a romance laid out in quatrains. Counting them as `romance_arte_maior` would
give 58 of 60 (96.7%).

### Coverage

Together, the public test set, the corpus sample and the targeted poems cover
37 of the 49 stanza types (29 with five or more stanzas). The other 12 are
rare in the corpus. These are the numbers of corpus stanzas that Gators
assigns them to (not gold counts: stanzas of these types that Gators misses
are not counted):

| Stanza type | Corpus stanzas |
|---|---|
| `seguidilla_xitana` | 12 |
| `copla_arte_menor` | 10 |
| `cuarteta_asonantada` | 8 |
| `copla_arte_maior` | 3 |
| `ovillejo` | 3 |
| `endecha_real` | 2 |
| `seguidilla_chamberga` | 1 |
| `copla_mixta`, `cuaderna_vía`, `décima_antiga`, `estrofa_alcaica`, `terceto_monorrimo` | 0 |

In all, 39 of the 18,417 stanzas in the corpus (0.2%).

## Comparing systems

For a strictly controlled comparison, use the same lines, poem boundaries and
gold rhyme relationships for every system. Different test corpora can still
use the same method, but their scores should not be interpreted as a direct
head-to-head comparison.
