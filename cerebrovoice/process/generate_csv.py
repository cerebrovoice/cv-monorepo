
# coding: utf-8

# In[1]:


import pandas as pd
import os, re
from cerebrovoice.helpers.helpers import *


# In[2]:


# replace this with your root directory
ROOT = os.getcwd() + "/images_scaled/"
OUTPUT = os.getcwd() + "/demo.csv"
DATE_PATTERN = "[0-9]{2}_[0-9]{2}"
VALID_LABELS = ["yes", "no", "stop", "go", "right", "left", "down", "up", "on", "off"]
IMG_EXT = ".png"
VERBOSITY = 100
NUM_CHANNELS = 22
CATS, MONTHS, DAYS, LABELS, SEQ, SETS = [], [], [], [], [], []
for i in range(1, NUM_CHANNELS+1):
    globals()["PATH{}".format(i)] = []


# In[3]:


def make_df_from_images(image_root):
    for cat in [d for d in os.listdir(image_root) if "voice" in d]:
        cat_path = os.path.join(image_root, cat)
        for date in [d for d in os.listdir(cat_path) if re.match(DATE_PATTERN, d)]:
            print("\tProcessing {}".format(date))
            date_path = os.path.join(cat_path, date)
            month = int(date[:2])
            day = int(date[3:])
            date_count = 0
            for label in [d for d in os.listdir(date_path) if d in VALID_LABELS]:
                label_path = os.path.join(date_path, label)
                placeholder = os.path.join(label_path, "ch1")
                for image in [f for f in os.listdir(placeholder) if f.endswith(IMG_EXT)]:
                    date_count += 1
                    for i in range(1, NUM_CHANNELS+1):
                        p = os.path.join(label_path, "ch{}".format(i), image)
                        if os.path.exists(p):
                            globals()["PATH{}".format(i)].append(p)
                        else:
                            globals()["PATH{}".format(i)].append(float('nan'))
                    CATS.append(cat)
                    DAYS.append(day)
                    MONTHS.append(month)
                    LABELS.append(label)
                    sequence_number = int(image[:-4])
                    basenum = sequence_number % 10
                    SEQ.append(sequence_number)
                    if basenum < 8:
                        SETS.append("Training")
                    elif basenum < 9:
                        SETS.append("Validation")
                    else:
                        SETS.append("Testing")
            print("\t\tProcessed {} sequences".format(date_count))
    d = {
            "Category":CATS,
            "Day":DAYS,
            "Month":MONTHS,
            "Label":LABELS,
            "SequenceNumber":SEQ,
            "Set":SETS
        }
    for i in range(1, NUM_CHANNELS+1):
        d["Path{}".format(i)] = globals()["PATH{}".format(i)]
    return pd.DataFrame(d)


# In[4]:


# os.remove('./demo.csv')
df = timer(make_df_from_images, ROOT)
df.to_csv(OUTPUT, index=False)

print(df.describe())

print("#" * 21 + " GENERATED CSV " + "#" * 21)
