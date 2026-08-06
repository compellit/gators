# Evaluation

`evaluate_rhyme_tags.py` evaluates predicted rhyme labels and, when the required
columns are available, predicted stanza types. Rhyme detection is evaluated as a
set of relationships between lines rather than by comparing the label assigned
to each line literally.

## Why rhyme is evaluated pairwise

Rhyme labels are arbitrary within a poem. For example, `abab` and `cdcd`
describe the same rhyme structure even though none of their labels match. The
evaluator therefore converts every non-empty rhyme chain into all the pairs of
lines belonging to that chain.

For example, the chain `aaaa` contains six rhyme pairs:

```text
1-2  1-3  1-4  2-3  2-4  3-4
```

Pairs are created only within the same group, normally a poem. A pair is:

- a true positive (`tp`) when it appears in both prediction and gold;
- a false positive (`fp`) when it appears only in the prediction;
- a false negative (`fn`) when it appears only in gold.

Pairs absent from both sets are skipped. Consequently, `tn` is currently always
zero.

The following normalized values are treated as no-rhyme labels and never form a
rhyme pair:

```text
""  -  0  nan  none  null
```

Labels are normalized by stripping surrounding whitespace and converting them
to lowercase.

## Rhyme metrics

The summary reports these corpus-level metrics:

```text
precision = tp / (tp + fp)
recall    = tp / (tp + fn)
f1        = 2 * precision * recall / (precision + recall)
accuracy  = (tp + tn) / pairs
pairs     = tp + fp + fn + tn
```

Because pairs absent from both prediction and gold are skipped, `tn` is zero and
the reported `accuracy` is equivalent to the Jaccard similarity of the predicted
and gold rhyme-pair sets:

```text
accuracy = tp / (tp + fp + fn)
```

It is not conventional binary-classification accuracy. Use pairwise `f1` as the
main overall rhyme-recognition result, with `precision` and `recall` explaining
whether errors come mainly from extra or missed rhymes.

## Stanza evaluation

Stanza evaluation runs when the input contains a stanza identifier and a gold
stanza-type column. By default the evaluator uses:

```text
stanza identifier:  stanzaNbr or stanza_n
gold type:          stanzaTypeNarrow
predicted type:     stanza_type and stanza_subtype
```

Verses are grouped by poem and stanza. The first populated gold value in each
stanza is compared with the first populated predicted broad type and subtype.
A stanza is correct when the normalized gold value exactly equals either
`stanza_type` or `stanza_subtype`.

Gold values that normalize to `""`, `-`, `0`, `nan`, `none`, or `null` are
excluded. A stanza with valid gold but no prediction remains in the denominator,
is counted as incorrect, and increments `stanza_type_missing_predictions`.

```text
stanza_type_accuracy = stanza_type_correct / stanza_type_stanzas
```

This is exact label accuracy. Rhyme-pattern, metre, and other similarity scores
produced by `rhyme.py` do not contribute to it.

## Running the evaluator

From the `rhyme-gl-wk` directory:

```bash
python evaluate_rhyme_tags.py \
  data/test_results_rhyme.tsv \
  --pred-column letter \
  --gold-column rhyme \
  --group-column workId \
  --line-id-column verse_n \
  --text-column gumperLine \
  --pairs-path data/rhyme_pairs.tsv \
  --stanzas-path data/stanzas.tsv \
  --summary-path data/summary.tsv
```

Important options:

- `--pred-column`: predicted rhyme-label column; default `letter`.
- `--gold-column`: gold rhyme-label column; inferred as `gold` or `rhyme`.
- `--group-column`: comparison boundary, normally the poem ID; repeat it to use
  a compound group.
- `--line-id-column`: line identifier written to the pair details.
- `--text-column`: verse text written to the pair details.
- `--stanza-column`: stanza identifier override.
- `--stanza-gold-column`: gold stanza-type override.
- `--stanza-pred-column`: use one custom stanza prediction column instead of
  `stanza_type` and `stanza_subtype`.

## Output files

### Pair details

`--pairs-path` is overwritten on each run and contains one row for every pair
present in prediction, gold, or both:

- `line_pair`: identifiers of the two lines;
- `pred_pair` and `gold_pair`: their normalized labels;
- `pred_same` and `gold_same`: whether each annotation links the lines;
- `correct`: whether the two pairwise decisions agree.

### Stanza details

When stanza evaluation is available, `--stanzas-path` is overwritten with one
row per evaluated stanza. It records the gold and predicted labels, broad-type
and subtype matches, missing predictions, and observed/expected patterns.

### Summary

`--summary-path` is an append-only experiment log. Its columns are:

```text
input_path
pairs_path
groups
lines
pairs
accuracy
precision
recall
f1
tp
fp
fn
tn
stanza_type_stanzas
stanza_type_correct
stanza_type_missing_predictions
stanza_type_accuracy
```

`groups` is the number of evaluated poems or explicitly requested groups;
`lines` is the number of input rows included in those groups. Blank stanza
fields mean stanza evaluation was unavailable for that run.

Because the summary is append-only, rerunning the same command adds another row
and can produce duplicates. `data/summary_stanza.tsv` is a legacy experiment
log; new evaluations store both rhyme and stanza metrics in `data/summary.tsv`.

## Comparing systems

For a strictly controlled model comparison, use the same lines, group boundaries,
and gold rhyme relationships for every system. Different test corpora can still
use the same method, but their scores should not be interpreted as a direct
head-to-head comparison.
