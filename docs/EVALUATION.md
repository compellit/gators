# Evaluation

`evaluation/evaluate.py` evaluates the rhyme letters and stanza types that
gators-verse assigns, against the gold annotation of the test corpus
(`evaluation/test_corpus.tsv`, 33 poems, 2,188 lines). Rhyme detection is
evaluated as a set of relationships between lines rather than by comparing the
letter assigned to each line literally.

`evaluation/run_all.sh` reruns the whole evaluation; see
[Running the evaluation](#running-the-evaluation).

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

The following values are treated as no-rhyme labels and never form a rhyme
pair (after stripping surrounding whitespace and converting to lowercase, so
`A` and `a` are the same letter):

```text
""  -  0  nan  none  null
```

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
"none" in gold.

```text
stanza_accuracy = stanzas_correct / stanzas
```

This is exact label accuracy. The pattern, meter and other similarity scores
that gators-verse computes do not contribute to it.

## Running the evaluation

`evaluation/run_all.sh` needs gators-verse installed with the `gama` extra, and
gama-verse's data files. It runs three steps:

1. `prepare.py` writes the test corpus as gators-verse input, with the
   standard column names, to `evaluation/results/input/`. The gold meter
   (`nbSyll`, `meterNbr`) goes into `metrical_syllables` and
   `stressed_syllables`; the gold rhyme letters and stanza types go into
   `gold_rhyme` and `gold_stanza_type`. The corpus's `nbSG` and `gprMet`
   columns are an earlier GAMA output and are not used.
2. `gators-verse` annotates the corpus in three settings.
3. `evaluate.py` scores each setting.

| Setting | Spelling normalization | meter |
|---|---|---|
| `gold_meter` | gama-verse | gold annotation |
| `end_to_end` | gama-verse | gama-verse |
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
written by gators-verse from `prepare.py`'s input.

## Output files

Each setting's folder in `evaluation/results/` has:

- `results.tsv`: gators-verse's output.
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

## Comparing systems

For a strictly controlled comparison, use the same lines, poem boundaries and
gold rhyme relationships for every system. Different test corpora can still
use the same method, but their scores should not be interpreted as a direct
head-to-head comparison.
