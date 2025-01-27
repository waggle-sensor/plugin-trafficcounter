from pathlib import Path
import argparse
import logging

import ffmpeg
import cv2
import numpy as np
from waggle.data.vision import Camera

from record import take_sample
from models.yolov7 import YOLOv7_Main
from models.sort import Sort


def get_stream_info(stream):
    try:
        input_probe = ffmpeg.probe(stream)
        fps = eval(input_probe['streams'][0]['r_frame_rate'])
        width = int(input_probe['streams'][0]['width'])
        height = int(input_probe['streams'][0]['height'])
        return True, fps, width, height
    except:
        return False, 0., 0, 0


def load_class_names(namesfile):
    class_names = []
    with open(namesfile, 'r') as fp:
        lines = fp.readlines()
    for line in lines:
        line = line.rstrip()
        class_names.append(line)
    return class_names


def main(args):
    if args.stream != "":
        logging.info(f"Recording from {args.stream} for {args.duration} seconds")
        result, input_video_path, timestamp = take_sample(args.stream, args.duration)
        if result is False:
            print("Error: Failed to take a sample")
            return -1
    else:
        if args.input_file == "":
            print("Error: Please provide a stream or input file")
            return -1
        logging.info(f"Taking input from {args.input_file}")
        # TODO: Need to provide a timestamp
        input_video_path = args.input_file

    logging.info("Loading models")
    class_names = load_class_names(args.labels)
    yolov7_main = YOLOv7_Main(args.model, class_names, args.det_thr, args.iou_thres)
    mot_tracker = Sort(max_age=args.max_age,
        min_hits=args.min_hits,
        iou_threshold=args.iou_threshold) #create instance of the SORT tracker

    _, fps, width, height = get_stream_info(input_video_path)
    if args.output_file == "":    
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_stream = cv2.VideoWriter(args.output_file, fourcc, fps, (int(width), int(height)), True)

    with Camera(input_video_path) as camera:
        for sample in camera.stream():
            frame = sample.data
            detections = yolov7_main.run(frame)
            results = np.asarray(detections[0].cpu().detach())
            if len(results) == 0:
                logging.info("No detections")
                # SORT recommends updating it even with no detections
                trackers = mot_tracker.update()
            else:
                for result in results:
                    result[0] = result[0] * width/640  ## x1
                    result[1] = result[1] * height/640  ## y1
                    result[2] = result[2] * width/640  ## x2
                    result[3] = result[3] * height/640  ## y2
                results[:, 2:4] += results[:, 0:2] #convert to [x1,y1,w,h] to [x1,y1,x2,y2]
                trackers = mot_tracker.update(detections)

            for track in trackers:
                id_num = track[4] #Get the ID for the particular track.
                l = track[0]  ## x1
                t = track[1]  ## y1
                r = track[2]-track[0]  ## x2
                b = track[3]-track[1]  ## y2

                name = class_names[int(track[-1])]
                frame = cv2.putText(frame, f'{id_num}:{name}', (int(l), int(t)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

                out_stream.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    out_stream.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Traffic counter')
    # Detection
    parser.add_argument('--model', type=Path, default=Path('model.pt'))
    parser.add_argument('--labels', dest='labels',
        action='store', default=Path('coco.names'), type=Path,
        help='Labels for detection')
    parser.add_argument("--detection-thres", dest='det_thr', type=float, default=0.5)
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    parser.add_argument('--target-class', nargs='+', type=int, help='Filter by class: --target-class 0, or --target-class 0 2 3')

    # Tracking
    parser.add_argument("--max-age",
        help="Maximum number of frames to keep alive a track without associated detections.",
        type=int, default=15)
    parser.add_argument("--min-hits",
        help="Minimum number of associated detections before track is initialised.",
        type=int, default=3)
    parser.add_argument("--iou-threshold",
        help="Minimum IOU for match for Kalman Filter.", type=float, default=0.3)

    # Recording
    parser.add_argument(
        '--stream', action='store', default="", type=str,
        help='ID or name of a stream, e.g. sample')
    parser.add_argument(
        '--duration', dest='duration',
        action='store', default=10., type=float,
        help='Time duration for input video')

    # Input
    parser.add_argument(
        '--input-file', dest='input_file',
        action='store', default="", type=str,
        help='Path to input video file')
    # parser.add_argument(
    #     '-sampling-interval', dest='sampling_interval',
    #     action='store', default=-1, type=int,
    #     help='Inferencing interval for sampling results')
    
    # Output
    parser.add_argument(
        '--output-file', dest='output_file',
        action='store', type=str,
        help='Path to output video file for validation')
    args = parser.parse_args()

    
    

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S')

    main(args)