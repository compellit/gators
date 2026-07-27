# Rhyme inter-annotator agreement

Run:

```bash
python evaluate_inter_annotator.py \
  data/test_corpus.tsv data/test_corpus-pr.tsv \
  --annotator-1-column " rhyme" \
  --annotator-2-column rhLtr \
  --pairs-path data/inter_annotator_disagreements.tsv \
  --summary-path data/inter_annotator_summary.tsv
```

The evaluator aligns rows by their order within each shared `workId`. Rhyme
letters are arbitrary names, so it compares whether each pair of lines belongs
to the same rhyme class. Thus, schemes such as `ABAB` and `CDCD` agree fully.

`pairwise_f1` is the score most comparable to `evaluate_rhyme_tags.py`.
`pairwise_jaccard` measures overlap between the two sets of rhyming pairs.
`cohen_kappa` is chance-corrected binary agreement over all within-work pairs.
`binary_pair_accuracy` is also reported, but can be inflated because pairs of
lines that do not rhyme are much more common.

Groups found in only one file and rows with blank group identifiers are reported
but excluded. Text mismatches are counted as an alignment diagnostic. A group
with different row counts raises an error rather than silently misaligning it.

## Summary columns

The summary TSV contains one row with the following columns:

| Column | Meaning |
| --- | --- |
| `annotator_1_rows` | Total data rows read from the first annotation file, including rows later excluded because their group identifier is blank or unmatched. |
| `annotator_2_rows` | Total data rows read from the second annotation file, under the same rules. |
| `blank_group_rows_1` | Rows in the first file whose `--group-column` value is blank. These rows are excluded. |
| `blank_group_rows_2` | Rows in the second file whose `--group-column` value is blank. These rows are excluded. |
| `shared_groups` | Groups, normally works, found in both files. Only these groups are evaluated. |
| `shared_lines` | Aligned lines belonging to shared groups and used in the evaluation. |
| `annotator_1_only_groups` | Groups found only in the first file and therefore excluded. |
| `annotator_1_only_lines` | Lines belonging to groups found only in the first file. |
| `annotator_2_only_groups` | Groups found only in the second file and therefore excluded. |
| `annotator_2_only_lines` | Lines belonging to groups found only in the second file. |
| `aligned_text_mismatches` | Aligned row positions for which the normalized values of `--text-column` differ. This is an alignment warning; the rows remain included because alignment is by position within the group. |
| `groups` | Number of evaluated groups. This is currently equal to `shared_groups`. |
| `perfect_relation_groups` | Groups in which both annotators make the same same-rhyme/different-rhyme decision for every pair of lines. Literal rhyme letters need not match. |
| `all_line_pairs` | Number of unordered pairs of lines within evaluated groups. Pairs are never formed across group boundaries. |
| `union_rhyme_pairs` | Pairs marked same-rhyme by at least one annotator: `same_same + annotator_1_only_same + annotator_2_only_same`. |
| `same_same` | Pairs both annotators place in the same rhyme class. This is the true-positive count when annotator 1 is the reference. |
| `annotator_1_only_same` | Pairs placed in the same rhyme class only by annotator 1. This is the false-negative count when annotator 1 is the reference. |
| `annotator_2_only_same` | Pairs placed in the same rhyme class only by annotator 2. This is the false-positive count when annotator 1 is the reference. |
| `different_different` | Pairs both annotators classify as different-rhyme. This is the true-negative count. |
| `pairwise_precision_2_vs_1` | Of the pairs annotator 2 marks same-rhyme, the proportion also marked same-rhyme by annotator 1: `same_same / (same_same + annotator_2_only_same)`. |
| `pairwise_recall_2_vs_1` | Of the pairs annotator 1 marks same-rhyme, the proportion also marked same-rhyme by annotator 2: `same_same / (same_same + annotator_1_only_same)`. |
| `pairwise_f1` | Harmonic mean of pairwise precision and recall. Although precision and recall assign different roles to the annotators, F1 is symmetric when the files are swapped. This is the score most comparable to `evaluate_rhyme_tags.py`. |
| `pairwise_jaccard` | Intersection over union of the annotators' same-rhyme pair sets: `same_same / union_rhyme_pairs`. |
| `binary_pair_accuracy` | Proportion of all pairs on which the binary same/different decisions agree: `(same_same + different_different) / all_line_pairs`. It can appear very high because different-rhyme pairs are usually more frequent. |
| `cohen_kappa` | Cohen's kappa for the binary same-rhyme/different-rhyme decisions over all pairs. It corrects observed agreement for agreement expected from the annotators' marginal same-rhyme rates. |
| `perfect_relation_group_accuracy` | Proportion of evaluated groups with perfect pairwise agreement: `perfect_relation_groups / groups`. |
| `disagreements` | Pairs on which one annotator says same-rhyme and the other says different-rhyme. This equals the number of data rows written to `--pairs-path`. |

## Disagreement-file columns

When `--pairs-path` is supplied, the evaluator writes one row for every
disagreeing line pair:

| Column | Meaning |
| --- | --- |
| `group` | Normalized value of `--group-column`, normally the work identifier. |
| `line_pair` | One-based positions of the two lines within the group, written as `left-right`. |
| `left_text` | Value of `--text-column` for the first line, taken from annotator 1's file. |
| `right_text` | Value of `--text-column` for the second line, taken from annotator 1's file. |
| `annotator_1_pair` | Normalized rhyme labels assigned by annotator 1 to the two lines, separated by a hyphen. It is diagnostic only; literal label equality between annotators is not evaluated. |
| `annotator_2_pair` | Normalized rhyme labels assigned by annotator 2 to the two lines, in the same format. |
| `annotator_1_same` | `1` if annotator 1 assigns the two lines the same non-empty rhyme label; otherwise `0`. Blank, `-`, `0`, `nan`, `none`, and `null` are treated as no rhyme. |
| `annotator_2_same` | Equivalent binary decision for annotator 2. Since the file contains only disagreements, this always differs from `annotator_1_same`. |
