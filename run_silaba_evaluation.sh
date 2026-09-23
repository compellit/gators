#!/usr/bin/env bash

set -euo pipefail

cd /home/anxo/compellit/rhyme-gl-wk

python3 src/transcribe_with_silaba.py \
  --input-path eval/test_corpus.tsv \
  --output-path eval/test_corpus-silaba.tsv \
  --text-column lines \
  --prepro

python3 rhyme.py \
  --input-path eval/test_corpus-silaba.tsv \
  --results-path eval/test_results_rhyme.tsv \
  --poem-column workId \
  --stanza-column stanzaNbr \
  --verse-column gumperLine \
  --ph-column phSilaba \
  --rhyme-column rhyme

python3 evaluate_rhyme_tags.py \
  eval/test_results_rhyme.tsv \
  --pred-column letter \
  --gold-column rhyme \
  --group-column workId \
  --line-id-column verse_n \
  --text-column gumperLine \
  --stanza-column stanzaNbr \
  --stanza-gold-column stanzaTypeNarrow \
  --pairs-path eval/rhyme_pairs.tsv \
  --stanzas-path eval/stanzas.tsv \
  --summary-path eval/summary.tsv
