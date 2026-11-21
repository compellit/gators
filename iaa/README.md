# Rhyme inter-annotator agreement

From the `rhyme-gl-wk` directory, run:

```bash
python iaa/evaluate_inter_annotator.py \
  evaluation/test_corpus.tsv evaluation/test_corpus-pr.tsv \
  --annotator-1-column rhyme \
  --annotator-2-column rhLtr \
  --pairs-path iaa/inter_annotator_disagreements.tsv \
  --summary-path iaa/inter_annotator_summary.tsv
```

The evaluator aligns rows by order within each shared `workId`. Rhyme letters
are arbitrary names, so it compares whether pairs of lines belong to the same
rhyme class. Thus, `ABAB` and `CDCD` agree fully.

## Summary columns

| Column | Meaning |
| --- | --- |
| `annotator_1_rows` | All data rows read from the first file. |
| `annotator_2_rows` | All data rows read from the second file. |
| `blank_group_rows_1` | First-file rows with a blank group identifier; excluded. |
| `blank_group_rows_2` | Second-file rows with a blank group identifier; excluded. |
| `shared_groups` | Groups found in both files and available for evaluation. |
| `shared_lines` | Aligned lines from shared groups used in evaluation. |
| `annotator_1_only_groups` | Groups found only in the first file; excluded. |
| `annotator_1_only_lines` | Lines belonging to first-file-only groups. |
| `annotator_2_only_groups` | Groups found only in the second file; excluded. |
| `annotator_2_only_lines` | Lines belonging to second-file-only groups. |
| `aligned_text_mismatches` | Aligned positions whose normalized text differs. They remain included, but should be checked. |
| `groups` | Number of evaluated groups; currently the same as `shared_groups`. |
| `perfect_relation_groups` | Groups in which every same/different-rhyme pair decision agrees. Literal rhyme letters need not match. |
| `all_line_pairs` | All unordered within-group line pairs. No pairs cross group boundaries. |
| `union_rhyme_pairs` | Pairs marked same-rhyme by either annotator: `same_same + annotator_1_only_same + annotator_2_only_same`. |
| `same_same` | Pairs marked same-rhyme by both annotators. |
| `annotator_1_only_same` | Pairs marked same-rhyme only by annotator 1; false negatives for annotator 2 when annotator 1 is the reference. |
| `annotator_2_only_same` | Pairs marked same-rhyme only by annotator 2; false positives when annotator 1 is the reference. |
| `different_different` | Pairs marked different-rhyme by both annotators. |
| `pairwise_precision_2_vs_1` | `same_same / (same_same + annotator_2_only_same)`. |
| `pairwise_recall_2_vs_1` | `same_same / (same_same + annotator_1_only_same)`. |
| `pairwise_f1` | Harmonic mean of precision and recall. It is symmetric under swapping annotators and is most comparable to `evaluation/evaluate.py`. |
| `pairwise_jaccard` | Same-rhyme intersection over union: `same_same / union_rhyme_pairs`. |
| `binary_pair_accuracy` | `(same_same + different_different) / all_line_pairs`. This can be inflated by frequent different-rhyme pairs. |
| `cohen_kappa` | Binary pair agreement corrected for agreement expected from the annotators' marginal decision rates. |
| `perfect_relation_group_accuracy` | `perfect_relation_groups / groups`. |
| `disagreements` | Pairs on which the annotators' same/different decisions conflict; also the number of disagreement-file rows. |

## Disagreement-file columns

| Column | Meaning |
| --- | --- |
| `group` | Normalized group identifier, normally `workId`. |
| `line_pair` | One-based positions of the lines within the group, as `left-right`. |
| `left_text` | First line's text from annotator 1's file. |
| `right_text` | Second line's text from annotator 1's file. |
| `annotator_1_pair` | Annotator 1's normalized labels for the two lines. |
| `annotator_2_pair` | Annotator 2's normalized labels for the two lines. |
| `annotator_1_same` | `1` for the same nonempty rhyme label, otherwise `0`. Blank, `-`, `0`, `nan`, `none`, and `null` mean no rhyme. |
| `annotator_2_same` | The equivalent annotator 2 decision; it always differs here because this file contains only disagreements. |
