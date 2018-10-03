import os, subprocess, re
from time import time
from datetime import datetime, timedelta

def curr_time(offset=7):
    return datetime.now() - timedelta(hours=offset) # offset from UTC to PST

def make_header(s):
	return ("#" * 42) + ("\n{:^42}\n".format(s)) + ("#" * 42)

def print_and_log(logfile, s):
	if logfile:
		with open(logfile, 'a') as log:
			log.write(str(s))
			log.write("\n")
	print(s)

def progress_bar(curr, total, tabs=0, prefix=""):
	"""Prints a progress bar, tab-spaced, with an optional message as a prefix"""
	block_char = u"\u2588"
	pct_done = curr / total * 100
	blocks = int(pct_done // 2)
	blocks *= block_char
	additional = [u"\u258F", u"\u258E", u"\u258D", u"\u258C", u"\u258B", u"\u258A", u"\u2589"]
	i = int((pct_done % 2) * 4) - 1
	if i >= 0:
		blocks += additional[i]
	tabs *= "\t"
	ret = "\r" if curr != 0 else ""
	end = "" if pct_done < 100 else "\n"
	print("{}{}{}|{:<50}| {:.2f}% ({}/{})".format(ret, tabs, prefix, blocks, pct_done, curr, total), end=end)

def print_and_log_header(logfile, s):
    h = make_header(str(s))
    if logfile:
        with open(logfile, 'a') as log:
            log.write(h)
            log.write("\n")
    print(h)

def sec_to_str(secs):
    ms = secs - int(secs)
    days = int(secs // (24 * 3600))
    hours = int((secs % ((24 * 3600))) // 3600)
    minutes = int((secs % 3600) // 60)
    seconds = int(secs % 60)
    return "{:02}:{:02}:{:02}:{:02}.{}".format(days, hours, minutes, seconds, "{:.3}".format(ms)[2:])

def run_command(command, output=False):
	"""Runs a command in a subprocess, silent by default"""
	if output:
		subprocess.run(command)
	else:
		NULL = open(os.devnull, 'w')
		subprocess.run(command, stdout=NULL, stderr=NULL)

def ms_to_strtime(ms):
	"""Converts milliseconds to a human readable string"""
	hours = int(ms // (3600000))
	minutes = int((ms % 3600000) // 60000)
	seconds = int((ms % 60000) // 1000)
	ms = int(ms % 1000)
	return "{:02}:{:02}:{:02}.{:03}".format(hours, minutes, seconds, ms)

def timer(f, *args):
	""" Time the execution of a function with optional args"""
	print("Start: {}".format(datetime.now()))
	start_ms = time() * 1000
	result = f(*args)
	end_ms = time() * 1000
	duration = end_ms - start_ms
	print("Finished in {}".format(ms_to_strtime(duration)))
	print("End: {}".format(datetime.now()))
	return result