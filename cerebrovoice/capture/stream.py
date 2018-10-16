# Cerebro Voice 2018 @

import os
import time


MAX_FRAME_RATE = 100
LINE_SIZE_MULTIPLIER_COEFFICIENT = 2
DATA_LINE_SEPARATOR = ", "


def get_first_data_line(filepath, first_data_line):
    # Returns the size of the first data line in file or raises an error otherwise
    try:
        # We trust here that file existence is already checked
        with open(filepath, "r") as file:
            [next(file) for _ in range(first_data_line - 1)]  # Skip lines before data starts
            line = next(file)
        return line
    except StopIteration:
        raise ValueError("Couldn't retrieve a line as there are less line in file than {0}.".format(first_data_line))


def get_index_from_data_line(
        data_line,
        sample_index_column):
    data = data_line.split(DATA_LINE_SEPARATOR)
    if sample_index_column < len(data):
        raw_index = data[sample_index_column].strip()
    else:
        raise ValueError("Either separator is wrong or index column is out of data column bounds.")

    if not raw_index.isdigit():
        raise ValueError("Got {0} instead of a non negative number from line:\n{1}.".format(raw_index, data_line))
    return int(raw_index)


def read_openbci_csv_frame(
        filepath,
        frame_rate,
        sample_rate,
        sample_index_column,
        window_size_in_seconds,
        data_line_size,
        previous_last_line,
        previous_last_index):
    # We trust here that file existence is already checked
    with open(filepath, "rb") as file:
        # Multiplying by line_size_multiplier_coefficient to make sure we have at least necessary amount of lines
        offset_in_chars = int(sample_rate * window_size_in_seconds * data_line_size * LINE_SIZE_MULTIPLIER_COEFFICIENT)
        # Calculate offset_limit and check that we're not beyond the limit
        offset_limit = file.seek(0, os.SEEK_END)
        file.seek(-min(offset_in_chars, offset_limit), os.SEEK_END)
        raw_lines = file.read().decode("utf-8").split("\n")
        # Filter out empty lines and skip last line as it might be partially written
        lines = [raw_lines[i] for i in range(len(raw_lines) - 1) if raw_lines[i] != ""]
        print("Got lines, top: {0}, bottom {1}".format("\n".join(lines[:10]), "\n".join(lines[-10:])))
        number_of_lines_per_frame = sample_rate * window_size_in_seconds
        if len(lines) > number_of_lines_per_frame:
            last_lines = lines[-number_of_lines_per_frame:]
            last_line = last_lines[-1]
            last_index = get_index_from_data_line(data_line=last_line, sample_index_column=sample_index_column)
            index_changed_based_on_index = (last_index - previous_last_index + sample_rate) % sample_rate

            # We want to return here fast as comparison based on lines is a bit more expensive
            if index_changed_based_on_index * frame_rate >= sample_rate:
                return last_lines, last_line, last_index

            # As index count goes in circles up to sample_rate we should also check the difference based on new lines
            if previous_last_line:
                try:
                    previous_last_line_position = last_lines.index(previous_last_line)
                except ValueError:
                    previous_last_line_position = -1
            else:
                previous_last_line_position = -1
            index_changed_based_on_previous_line_position = len(last_lines) - 1 - previous_last_line_position

            if index_changed_based_on_previous_line_position * frame_rate >= sample_rate:
                return last_lines, last_line, last_index

    # If we're here it means we need to collect more data or in rare cases adjust LINE_SIZE_MULTIPLIER_COEFFICIENT
    # TODO(mf): use this print only for debug and abstract into logger package
    print("Warning: not enough lines for a frame. Collect more data.")
    return [], previous_last_line, previous_last_index


def read_openbci_stream(
        filepath,
        frame_rate,
        sample_rate,
        is_frame_optional=False,  # If yields are optional generator won't fail because of timeout
        sample_index_column=0,  # 1st column has index == 0
        window_size_in_seconds=1,
        first_data_line=1,
        timeout_in_seconds=10):
    if not os.path.isfile(filepath):
        raise ValueError("File {0} doesn't exist".format(filepath))
    if window_size_in_seconds < 1:
        raise ValueError("Window size in seconds cannot be less than 1 second.")
    if sample_rate < 1 or frame_rate < 1:
        raise ValueError("Sample/frame rate cannot be less than 1 per second.")
    if frame_rate > sample_rate:
        frame_rate = sample_rate
        # TODO(mf): abstract prints into logger package
        print("Warning: frame rate cannot be larger than sample rate. Frame rate is set to sample rate.")
    if frame_rate > MAX_FRAME_RATE:
        frame_rate = MAX_FRAME_RATE
        # TODO(mf): abstract prints into logger package
        print("Warning: frame rate cannot be larger than {0}. Frame rate is set to {0}.".format(MAX_FRAME_RATE))

    previous_last_line = get_first_data_line(filepath=filepath, first_data_line=first_data_line)
    previous_last_index = get_index_from_data_line(
        data_line=previous_last_line,
        sample_index_column=sample_index_column)

    request_time_start = time.time()
    message_on_timeout = "Couldn't retrieve a single frame from {0} after {1}s.".format(filepath, timeout_in_seconds)
    while is_frame_optional or time.time() - request_time_start <= timeout_in_seconds:
        last_lines, previous_last_line, previous_last_index = read_openbci_csv_frame(
            filepath=filepath,
            frame_rate=frame_rate,
            sample_rate=sample_rate,
            sample_index_column=sample_index_column,
            window_size_in_seconds=window_size_in_seconds,
            data_line_size=len(previous_last_line),
            previous_last_line=previous_last_line,
            previous_last_index=previous_last_index)
        if len(last_lines) == 0 and time.time() - request_time_start <= timeout_in_seconds:
            time.sleep(1.0 / frame_rate)
            continue
        if len(last_lines) == 0 and is_frame_optional:
            # TODO(mf): abstract prints into logger package
            print(message_on_timeout)
        frame = last_lines  # We make this assignment to signify that no processing is made and we might need it here
        yield frame
        request_time_start = time.time()

    raise ValueError(message_on_timeout)


if __name__ == "__main__":
    # TODO(mf): write up a simple test for read_openbci_stream and other methods
    exit(0)
