import json
import os
import re
import sys

from cerebrovoice.helpers.helpers import run_command, timer

CREDENTIALS = "configuration.json"


def dir_to_date(s):
    mon_str = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    pattern = "[a-z]{3}[0-9]{2}_[0-9]{4}"
    match = re.match(pattern, s)
    if match:
        date = match.group(0)
        if date[:3] not in mon_str:
            raise ValueError(
                "Root directory month name is none of\n\t[jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nove, dec]")
        date = date.replace(date[:3], mon_str[date[:3]] + "_")
        return date
    raise ValueError(
        "Root directory date should be in the format:\n\t[lower-case-3-letter-month-abbreviation][dd]_[yyyy]")


def make_dirs(root):
    audio = os.path.join(root, "audio")
    if "no_voice" in root:
        category = os.path.join(audio, "no_voice")
    else:
        category = os.path.join(audio, "voice")
    date = os.path.join(category, dir_to_date(root))
    if not os.path.isdir(audio):
        os.mkdir(audio)
    if not os.path.isdir(category):
        os.mkdir(category)
    if not os.path.isdir(date):
        os.mkdir(date)
    return date


if __name__ == "__main__":
    ROOT = sys.argv[1]

    # load credentials
    assert (os.path.isfile(CREDENTIALS))
    with open(CREDENTIALS, 'r') as file:
        credentials = json.load(file)

    # check for correct input directory structure
    original_audio_path = os.path.join(ROOT, "original_audio/")
    split_audio_path = os.path.join(ROOT, "split_audio/")
    assert (os.path.isdir(original_audio_path))
    assert (os.path.isdir(split_audio_path))

    # make all the new directories
    temp_path = make_dirs(ROOT)
    date = os.path.basename(temp_path)
    zip_path = os.path.join(ROOT, "{}_audio.zip".format(date))
    o_zip_path = os.path.join(ROOT, "{}_original_audio.zip".format(date))
    csv_path = os.path.join(ROOT, "outputs.csv")
    new_csv_path = os.path.join(ROOT, "{}_outputs.csv".format(date))

    # make commands to zip and upload audio and files
    commands = [["cp", "-r", split_audio_path, temp_path],
                ["zip", "-0", "-q", "-m", "-r", zip_path, os.path.join(ROOT, "audio/")],
                ["gsutil", "cp", "-r", zip_path, credentials["bucket"]],
                ["zip", "-0", "-q", "-r", o_zip_path, original_audio_path],
                ["gsutil", "cp", "-r", o_zip_path, credentials["bucket"]], ["cp", csv_path, new_csv_path],
                ["gsutil", "cp", new_csv_path, credentials["bucket"]], ["rm", o_zip_path, zip_path, new_csv_path]]

    # execute all the commands
    for command in commands:
        print("\n>>> " + " ".join(command))
        timer(run_command, command)
    print("Done!")
    sys.exit()
