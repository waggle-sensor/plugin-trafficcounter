#!/usr/bin/env python3

import os
import re
import time
import argparse
import logging

import ffmpeg

from waggle.data.vision import resolve_device
from waggle.data.timestamp import get_timestamp


def take_sample(stream, duration, skip_second=0):
    stream_url = resolve_device(stream)
    # Assume PyWaggle's timestamp is in nano seconds
    timestamp = get_timestamp() + int(skip_second * 1e9)
    try:
        script_dir = os.path.dirname(__file__)
    except NameError:
        script_dir = os.getcwd()
    filename = os.path.join(script_dir, 'sample.mp4')

    # To prevent corruption in frames we prefer tcp transfer for rtsp
    if stream_url.startswith("rtsp"):
        c = ffmpeg.input(stream_url, rtsp_transport="tcp", ss=skip_second, stimeout=5000000)
    else:
        c = ffmpeg.input(stream_url, ss=skip_second, stimeout=5000000)
    c = ffmpeg.output(
        c,
        filename,
        codec="copy", # use same codecs of the original video
        f='mp4',
        t=duration).overwrite_output()
    logging.info("Running command: %s", c.compile())
    (out, err) = c.run(quiet=True, capture_stdout=True, capture_stderr=True)
    if err:
        logging.info("%s", out.decode())
        logging.error("Error: %s", err.decode())
        return False, filename, timestamp
    return True, filename, timestamp


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--stream', dest='stream',
        action='store', default="camera", type=str,
        help='ID or name of a stream, e.g. sample')
    parser.add_argument(
        '--duration', dest='duration',
        action='store', default=10., type=float,
        help='Time duration for input video')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )

    logging.info(f"Recording from {args.stream} for {args.duration} seconds")
    exitcode, filename, timestamp = take_sample(args.stream, args.duration)
    exit(exitcode)