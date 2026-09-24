#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
EVALUATION_DIR="${RHYME_EVALUATION_DIR:-$PROJECT_DIR/evaluation}"

cd "$PROJECT_DIR"

python3 src/transcribe_with_silaba.py \
  --input-path "$EVALUATION_DIR/test_corpus.tsv" \
  --output-path "$EVALUATION_DIR/test_corpus-silaba.tsv" \
  --text-column lines \
  --prepro

python3 rhyme.py \
  --input-path "$EVALUATION_DIR/test_corpus-silaba.tsv" \
  --results-path "$EVALUATION_DIR/test_results_rhyme.tsv" \
  --poem-column workId \
  --stanza-column stanzaNbr \
  --verse-column gumperLine \
  --ph-column phSilaba \
  --rhyme-column rhyme

python3 scripts/evaluate_rhyme_tags.py \
  "$EVALUATION_DIR/test_results_rhyme.tsv" \
  --pred-column letter \
  --gold-column rhyme \
  --group-column workId \
  --line-id-column verse_n \
  --text-column gumperLine \
  --stanza-column stanzaNbr \
  --stanza-gold-column stanzaTypeNarrow \
  --pairs-path "$EVALUATION_DIR/rhyme_pairs.tsv" \
  --stanzas-path "$EVALUATION_DIR/stanzas.tsv" \
  --summary-path "$EVALUATION_DIR/summary.tsv"
