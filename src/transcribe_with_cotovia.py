import argparse
import random
import re
import string
import subprocess
#from TTS.utils.synthesizer import Synthesizer

import pandas as pd

PUNCLIST = [';', '?', '¿', ',', ':', '.', '!', '¡']


def sanitize_filename(filename):
    """Remove or replace any characters that are not allowed in file names."""
    return ''.join(c for c in filename if c.isalnum() or c in (' ', '_', '-')).rstrip()


def canBeNumber(n):
    try:
        int(n)
        return True
    except ValueError:
        # Not a number
        return False


def is_number(index, text):
    if index == 0:
        return False
    elif index == len(text) - 1:
        return False
    else:
        return canBeNumber(text[index - 1]) and canBeNumber(text[index + 1])


def split_punc(text):
    segments = []
    puncs = []
    curr_seg = ""
    previous_punc = False

    for i, c in enumerate(text):
        if c in PUNCLIST and not previous_punc and not is_number(i, text):
            segments.append(curr_seg.strip())
            puncs.append(c)
            curr_seg = ""
            previous_punc = True
        elif c in PUNCLIST and previous_punc:
            puncs[-1] += c
        else:
            curr_seg += c
            previous_punc = False

    segments.append(curr_seg.strip())

    # Remove empty segments in the list
    segments = filter(None, segments)

    # store segments as a list
    segments = list(segments)

    return segments, puncs


def remove_tra3_tags(phontrans):
    s = re.sub(r'#(.+?)#', r'', phontrans)
    s = re.sub(r'%(.+?)%', r'', s)
    s = re.sub(' +', ' ', s)
    s = re.sub('-', '', s)
    return s.strip()


def to_cotovia(text_segments):
    # Input and output Cotovía files
    res = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    COTOVIA_IN_TXT_PATH = res + '.txt'
    COTOVIA_IN_TXT_PATH_ISO = 'iso8859-1' + res + '.txt'
    COTOVIA_OUT_PRE_PATH = 'iso8859-1' + res + '.tra'
    COTOVIA_OUT_PRE_PATH_UTF8 = 'utf8' + res + '.tra'

    with open(COTOVIA_IN_TXT_PATH, 'w') as f:
        for seg in text_segments:
            if seg:
                f.write(seg + '\n')
            else:
                f.write(',' + '\n')

    # utf-8 to iso8859-1
    subprocess.run(["iconv", "-f", "utf-8", "-t", "iso8859-1", COTOVIA_IN_TXT_PATH, "-o", COTOVIA_IN_TXT_PATH_ISO],
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    # call cotovia with -t3 option
    subprocess.run(["cotovia", "-i", COTOVIA_IN_TXT_PATH_ISO, "-t3", "-n"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.STDOUT)
    # iso8859-1 to utf-8
    subprocess.run(["iconv", "-f", "iso8859-1", "-t", "utf-8", COTOVIA_OUT_PRE_PATH, "-o", COTOVIA_OUT_PRE_PATH_UTF8],
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    segs = []
    try:
        with open(COTOVIA_OUT_PRE_PATH_UTF8, 'r') as f:
            segs = [line.rstrip() for line in f]
            segs = [remove_tra3_tags(line) for line in segs]
    except:
        print("ERROR: Couldn't read cotovia output")

    subprocess.run(
        ["rm", COTOVIA_IN_TXT_PATH, COTOVIA_IN_TXT_PATH_ISO, COTOVIA_OUT_PRE_PATH, COTOVIA_OUT_PRE_PATH_UTF8],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    return segs


def merge_punc(text_segs, puncs):
    merged_str = ""

    for i, seg in enumerate(text_segs):
        merged_str += seg + " "
        if i < len(puncs):
            merged_str += puncs[i] + " "

    # remove spaces before , . ! ? ; : ) ] of the merged string
    merged_str = re.sub(r"\s+([.,!?;:)\]])", r"\1", merged_str)

    # remove spaces after ( [ ¡ ¿ of the merged string
    merged_str = re.sub(r"([\(\[¡¿])\s+", r"\1", merged_str)

    return merged_str.strip()


def accent_convert(phontrans):
    transcript = re.sub('a\^', 'á', phontrans)
    transcript = re.sub('e\^', 'é', transcript)
    transcript = re.sub('i\^', 'í', transcript)
    transcript = re.sub('o\^', 'ó', transcript)
    transcript = re.sub('u\^', 'ú', transcript)
    transcript = re.sub('E\^', 'É', transcript)
    transcript = re.sub('O\^', 'Ó', transcript)
    return transcript


def text_preprocess(text):
    # Split from punc
    text_segments, puncs = split_punc(text)
    cotovia_phon_segs = to_cotovia(text_segments)
    cotovia_phon_str = merge_punc(cotovia_phon_segs, puncs)
    phon_str = accent_convert(cotovia_phon_str)
    return phon_str


def main():
    # parser = argparse.ArgumentParser(description='Cotovia phoneme transcription.')
    # parser.add_argument('text', type=str, help='Text to synthetize')
    # parser.add_argument('model_path', type=str, help='Absolute path to the model checkpoint.pth')
    # parser.add_argument('config_path', type=str, help='Absolute path to the model config.json')
    # 
    # args = parser.parse_args()

    df = pd.read_csv("data/gl-prepro-35k.tsv", sep="\t")
    df.dropna(inplace=True)
    df["phCotovia"] = df["running_text"].apply(text_preprocess)
    df.to_csv("data/gl-prepro-35k-cotovia-3.tsv", sep="\t", index=False)
    # with open("data/gl-prepro-35k-cotovia-2.tsv", "w") as f:
    #     for idx, row in df.iterrows():
    #         if idx <= 12466:
    #             continue
    #         f.write(text_preprocess(row["running_text"]) + "\n")
    #         f.flush()

    # print("Text before preprocessing: ", args.text)
    # text = text_preprocess(args.text)
    # print("Text after preprocessing: ", text)
    # synthesizer = Synthesizer(
    #     args.model_path, args.config_path, None, None, None, None,
    # )

    # Step 1: Extract the first word from the text
    # first_word = args.text.split()[0] if args.text.split() else "audio"
    # first_word = sanitize_filename(first_word)  # Sanitize to make it a valid filename

    # Step 2: Use synthesizer's built-in function to synthesize and save the audio
    # wavs = synthesizer.tts(text)
    # filename = f"{first_word}.wav"
    # synthesizer.save_wav(wavs, filename)

    # print(f"Audio file saved as: {filename}")


if __name__ == "__main__":
    main()
