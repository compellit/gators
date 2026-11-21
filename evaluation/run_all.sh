#!/usr/bin/env bash
# Rerun the evaluation on the test corpus, in three settings:
#   gold_metre  gama-verse normalizes the spelling; metre from the gold annotation
#   end_to_end  gama-verse normalizes the spelling and scans the lines (Gumper)
#   no_gama     no gama-verse: light spelling cleanup and no metre
# Needs gators-verse installed with the gama extra, and gama-verse's data files.
set -euo pipefail
cd "$(dirname "$0")"

python prepare.py test_corpus.tsv results/input

run() {
    local setting=$1 input=$2
    shift 2
    mkdir -p "results/$setting"
    gators-verse "results/input/$input" -o "results/$setting/results.tsv" "$@"
    echo "== $setting"
    python evaluate.py "results/$setting/results.tsv" "results/$setting"
}

run gold_metre input_gold_metre.tsv
run end_to_end input_no_metre.tsv
run no_gama input_no_metre.tsv --no-gama
