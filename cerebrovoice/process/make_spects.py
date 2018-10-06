# coding: utf-8

import os
import re

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile

from cerebrovoice.helpers.helpers import curr_time, timer

# get_ipython().run_line_magic('matplotlib', 'inline')


# replace this with your root directory
ROOT = os.getcwd() + "/audio/"
IMG_ROOT = os.getcwd() + "/images_scaled/"
pattern = "[0-9]{2}_[0-9]{2}"

if not os.path.isdir(IMG_ROOT):
    os.mkdir(IMG_ROOT)

"""
Expected directory structure:
[INSIDE ROOT DIRECTORY]
---- [category] voice, no_voice
-------- [date] 07_02, 07_09, ...
------------ [label] down, go, ...
---------------- [channel] ch1, ch2, ...
-------------------- [wave files] *.wav
"""

VALID_LABELS = ["yes", "no", "stop", "go", "right", "left", "down", "up", "on", "off", "test"]
IMG_EXT = ".png"
VERBOSITY = 1000


# In[3]:


def preprocess(samples, sample_rate, multiplier=1):
    sr = sample_rate * multiplier
    padded = np.zeros(sr)
    samples = samples[:sr]
    padded[:samples.shape[0]] = samples
    return padded


def make_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)


# In[4]:


def process(input_dir, output_dir, overwrite=False):
    items = 0
    created = 0
    found = 0
    date_mult = {"08_08": 2, "08_11": 2, "08_14": 2}
    plt.ioff()
    for date in [x for x in os.listdir(input_dir) if re.match(pattern, x)]:
        multiplier = 1
        if date in date_mult:
            multiplier = date_mult[date]
        date_path = os.path.join(input_dir, date)
        o_date_path = os.path.join(output_dir, date)
        make_dir(o_date_path)
        for label in [d for d in os.listdir(date_path) if d in VALID_LABELS]:
            label_path = os.path.join(date_path, label)
            o_label_path = os.path.join(o_date_path, label)
            make_dir(o_label_path)
            print("\tProcessing: {}".format(label_path))
            print("\tTime: {}".format(curr_time()))
            for channel in [d for d in os.listdir(label_path) if d.startswith("ch")]:
                voice = False
                ch = int(channel[2:])
                if ch == 4 or ch >= 9:
                    voice = True
                channel_path = os.path.join(label_path, channel)
                o_channel_path = os.path.join(o_label_path, channel)
                make_dir(o_channel_path)
                for file in [f for f in os.listdir(channel_path) if f.endswith(".wav")]:
                    items += 1
                    wavpath = os.path.join(channel_path, file)
                    imgpath = os.path.join(o_channel_path, file[:-4] + IMG_EXT)
                    if overwrite or not os.path.isfile(imgpath):
                        created += 1
                        if items % VERBOSITY == 0:
                            print("\t\tCreated {}th image".format(items))
                        sample_rate, samples = wavfile.read(wavpath)
                        samples = preprocess(samples, sample_rate, multiplier)
                        # freqs, times, spectrogram = signal.spectrogram(samples, sample_rate)
                        if voice:
                            s = librosa.feature.melspectrogram(samples, sr=sample_rate, n_mels=128)
                        else:
                            s = librosa.feature.melspectrogram(samples, sr=sample_rate, n_mels=128, fmax=512)
                        log_s = librosa.power_to_db(s, ref=np.max)
                        fig = plt.figure(figsize=(1.28, 1.28), dpi=100, frameon=False)
                        ax = plt.Axes(fig, [0., 0., 1., 1.])
                        ax.set_axis_off()
                        fig.add_axes(ax)
                        plt.axis('off')
                        librosa.display.specshow(log_s)
                        plt.savefig(imgpath)
                        plt.close()
                    else:
                        found += 1
                        if items % VERBOSITY == 0:
                            print("\t\tFound {}th image".format(items))
    print("\tFound:\t\t{}\n\tCreated:\t{}".format(found, created))
    plt.ion()


# In[5]:


dir_pairs = {
    ROOT + "voice": IMG_ROOT + "voice",
    ROOT + "no_voice": IMG_ROOT + "no_voice"
}

# In[6]:


for input_dir in dir_pairs:
    output_dir = dir_pairs[input_dir]
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    timer(process, input_dir, output_dir)

print("#" * 21 + "  CREATED SPECTROGRAMS  " + "#" * 21)
