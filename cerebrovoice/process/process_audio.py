import os
import pandas as pd
import shutil
import sys
import threading
from cerebrovoice.helpers.helpers import ms_to_strtime, progress_bar, run_command, timer
from multiprocessing import Queue, Value, Lock

VERBOSITY = 100
PER_WORD_DURATION = 1000  # ms

# Input CSV and the expected column names
CSV = "/Users/annieho/Desktop/subvocalization_stream/outputs.csv"
TIME_NAME = "timeStamp"
KEY_NAME = "keyPressed"
WORD_NAME = "wordSaid"

# Audio paths to read/write
AUDIO_PATH = "original_audio"
SPLIT_PATH = "split_audio"


# General Helpers
def nearest_1000(n):
    return round(n / 1000) * 1000


# Multi-Threading
def run_job(q, num_jobs, dryrun=False):
    while not q.empty():
        command = q.get()
        counter.increment()
        job_num = counter.value()
        progress_bar(job_num, num_jobs, 1, "Splitting ")
        if not dryrun:
            run_command(command)


def make_pool(q, num_jobs, num_threads=8, dryrun=False):
    threads = []
    for i in range(num_threads):
        threads.append(threading.Thread(target=run_job, args=(q, num_jobs, dryrun)))
    return threads


def run_jobs(pool):
    for thread in pool:
        thread.start()
        thread.join()


def del_threads(pool):
    for thread in pool:
        del thread


class Counter(object):
    """A thread-safe counter"""
    def __init__(self, initval=0):
        self.val = Value('i', initval)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.val.value += 1

    def value(self):
        with self.lock:
            return self.val.value


# Dataframe IO and Manipulation
def read_inputs(file):
    return pd.read_csv(file, sep=',')


def first_signal(df):
    return df.iloc[0][TIME_NAME]


def postprocess_df(df):
    """Custom post-processing function. Add anything required for a particular dataset here"""
    df = df.tail(df.shape[0] - 2)  # drop the first 2 entries for rhythm reasons
    df = df.reset_index()
    return df


def make_start_end_df(df):
    """Generate a dataframe with the word, start time, end time, and duration"""
    global PER_WORD_DURATION
    idx = df.index[df[KEY_NAME] == "PAUSE"]
    df.loc[idx, WORD_NAME] = "PAUSE"
    prev_word = None
    start_end = pd.DataFrame()
    prev = 0
    for i, row in df.iterrows():
        word = row[WORD_NAME]
        if prev_word is not None and word != prev_word:
            start = prev
            end = row[TIME_NAME]
            duration = end - start
            if PER_WORD_DURATION is None:
                PER_WORD_DURATION = nearest_1000(duration)
            repeats = nearest_1000(duration) // PER_WORD_DURATION
            per_sample_time = int(duration / repeats) if repeats else 0
            for _ in range(repeats - 1):
                curr_start = int(start + _ * per_sample_time)
                curr_end = int(start + (_ + 1) * per_sample_time)
                start_end = start_end.append([pd.Series([prev_word, curr_start, curr_end, per_sample_time])])
            curr_start = int(start + (repeats - 1) * per_sample_time)
            curr_end = int(start + repeats * per_sample_time)
            start_end = start_end.append([pd.Series([word, curr_start, curr_end, per_sample_time])])
            prev = end
        prev_word = word
    start_end.columns = ["word", "start", "end", "duration"]
    start_end.start = start_end.start.shift(-1).fillna(0).astype(int)
    start_end.end = start_end.end.shift(-1).fillna(0).astype(int)
    start_end.duration = start_end.duration.shift(-1).fillna(0).astype(int)
    start_end = start_end[(start_end.word != "PAUSE") & (start_end.word != "NONE")]
    length = start_end.shape[0]
    start_end = start_end.head(length - 2)  # drop the last 2 for pause reasons
    if start_end.iloc[0]["duration"] < 750:
        length = start_end.shape[0]
        start_end = start_end.tail(length - 1)  # drop the first one for pause reasons
    start_end = start_end.reset_index()
    start_end = start_end.drop(['index'], axis=1)
    return postprocess_df(start_end)


def make_dirs(start_end, num_channels=8, root='.'):
    """Given a StartEnd DF, generate the directories required for the files the DF will generate"""
    labels = start_end["word"].unique()
    main_dir = os.path.join(root, SPLIT_PATH)
    if not os.path.isdir(main_dir):
        os.mkdir(main_dir)
    for label in labels:
        subdir = os.path.join(main_dir, label)
        if not os.path.isdir(subdir):
            os.mkdir(subdir)
        for i in range(num_channels):
            channel_path = os.path.join(subdir, "ch{}".format(i + 1))
            if not os.path.isdir(channel_path):
                os.mkdir(channel_path)


# Audio Processing
def split_audio(start_end, audio_dir, root='.'):
    labels = start_end["word"].unique()
    q = Queue()
    num_jobs = 0
    for file in [f for f in os.listdir(audio_dir) if f.endswith(".wav")]:
        labels = {label: 0 for label in labels}
        original_filepath = os.path.join(audio_dir, file)
        print("\tProcessing {}".format(original_filepath))
        channel = int(file[:2])
        for i, row in start_end.iterrows():
            if i + 1 % VERBOSITY == 0:
                print("\t\tAdded {}th clip to job queue".format(i))
            label = row["word"]
            start_time = ms_to_strtime(row["start"])
            end_time = ms_to_strtime(row["end"])
            subdir = "ch{}".format(channel)
            filename = "{:05}.wav".format(labels[label])
            labels[label] += 1
            new_filepath = os.path.join(root, SPLIT_PATH, label, subdir, filename)
            command = [
                "ffmpeg",
                "-i",
                original_filepath,
                "-ss", start_time,
                "-to", end_time,
                "-c", "copy",
                new_filepath]
            q.put(command)
            num_jobs += 1
    return q, num_jobs


def downsample(audio_path, sample_rate=8000):
    new_audio_path = os.path.join(audio_path + "_downsampled")
    if not os.path.isdir(new_audio_path):
        os.mkdir(new_audio_path)
    for wavfile in [f for f in os.listdir(audio_path) if f.endswith(".wav")]:
        original_filepath = os.path.join(audio_path, wavfile)
        new_filepath = os.path.join(new_audio_path, wavfile)
        command = ["ffmpeg", "-i", original_filepath, "-ar", str(sample_rate), new_filepath]
        print("\tDownsampling {} to {}Hz".format(original_filepath, sample_rate))
        run_command(command)
    return new_audio_path


def cleanup(d):
    for folder in d:
        print("folder is being removed - %s" % folder)
        shutil.rmtree(folder)


# Main Program
if __name__ == "__main__":
    if len(sys.argv) == 2:
        counter = Counter(0)
        root = sys.argv[1]

        # Read in the CSV file and process it
        csv = os.path.join(root, CSV)
        outputs = read_inputs(csv)
        offset = first_signal(outputs)
        outputs[TIME_NAME] = outputs[TIME_NAME] - offset
        outputs = outputs[outputs.timeStamp > 0]
        outputs = make_start_end_df(outputs)
        print(outputs)
        make_dirs(outputs, root=root)

        # Prepare the audio for processing
        DRYRUN = False
        SAMPLE_RATE = 8000
        downsampled_path = timer(downsample, os.path.join(root, AUDIO_PATH), SAMPLE_RATE)

        # Create jobs to split the audio
        job_queue, num_jobs = timer(split_audio, outputs, downsampled_path, root)
        pool = make_pool(job_queue, num_jobs, num_threads=4, dryrun=DRYRUN)

        # Run the audio jobs
        timer(run_jobs, pool)
        del_threads(pool)

        # Delete temporary folders/files created in the process
        cleanup([downsampled_path])
        print("Done!")
