"""Write the test corpus as gators-verse input, with the standard column names.

Two inputs are written to the output folder:

- input_gold_meter.tsv: with the gold meter (syllable count nbSyll and
  metrical stresses meterNbr), to evaluate rhyme and stanza analysis alone.
- input_no_meter.tsv: without meter, so that gators-verse gets it from
  gama-verse (end to end), or goes without it if gama-verse is not used.

The gold rhyme letters and stanza types are kept as gold_rhyme and
gold_stanza_type, for evaluate.py. Only nbSyll and meterNbr are gold meter;
nbSG and gprMet in the corpus are an earlier GAMA output and are not used.
"""

import argparse
import csv
from pathlib import Path

import pandas as pd

COLUMNS = {
    "lineID": "line_id",
    "workId": "poem_id",
    "stanzaNbr": "stanza_n",
    "lines": "text",
    "rhyme": "gold_rhyme",
    "stanzaTypeNarrow": "gold_stanza_type",
}
METER_COLUMNS = {"nbSyll": "metrical_syllables", "meterNbr": "stressed_syllables"}
TSV_OPTIONS = {"sep": "\t", "quoting": csv.QUOTE_NONE}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("test_corpus")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    corpus = pd.read_csv(args.test_corpus, keep_default_na=False, na_values=[""], **TSV_OPTIONS)
    # The file ends with two empty rows.
    corpus = corpus.dropna(subset=["lines"])
    corpus = corpus.astype({"lineID": int, "workId": int, "stanzaNbr": int})
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gold_meter = corpus[list(COLUMNS) + list(METER_COLUMNS)].rename(columns={**COLUMNS, **METER_COLUMNS})
    gold_meter.to_csv(output_dir / "input_gold_meter.tsv", index=False, **TSV_OPTIONS)
    no_meter = corpus[list(COLUMNS)].rename(columns=COLUMNS)
    no_meter.to_csv(output_dir / "input_no_meter.tsv", index=False, **TSV_OPTIONS)
    print(f"Wrote {len(corpus)} verses to {output_dir}")


if __name__ == "__main__":
    main()
