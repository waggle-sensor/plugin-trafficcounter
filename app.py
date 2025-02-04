import os
from pathlib import Path
import argparse
import logging
import json
from shapely.geometry.polygon import Polygon, LineString, Point

import ffmpeg
import cv2
import numpy as np
from waggle.plugin import Plugin
from waggle.data.vision import Camera
from waggle.data.timestamp import get_timestamp

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

class Vehicle:
    def __init__(self, id):
        self.id = id
        self.lane_scores = {}
        self.is_counted = False
        self.current_position = None
        self.current_position_poly = None
        self.reference_point = None
        self.name = ""

    def update_vehicle(self, classifed_name, position):
        self.name = classifed_name
        # left, top, right, bottom
        self.current_position = position
        self.current_position_poly = Polygon([(position[0], position[1]), (position[2], position[1]), (position[0], position[3]), (position[2], position[3])])
        lower_centroid_y_diff = (self.current_position_poly.bounds[3] - self.current_position_poly.centroid.y) / 2
        lower_centroid = (self.current_position_poly.centroid.x, self.current_position_poly.centroid.y + lower_centroid_y_diff)
        self.reference_point = lower_centroid

    def is_intersected(self, polyline: LineString):
        if self.current_position_poly is None:
            return False

        return polyline.intersects(self.current_position_poly)

    def score_lane(self, lane_name):
        score = self.lane_scores.get(lane_name, 0)
        score += 1
        self.lane_scores[lane_name] = score

    def get_best_lane(self):
        """ get_best_lane returns the best lane based on the accumulated scores
        """
        best_lane = ""
        best_score = 0
        for lane, score in self.lane_scores.items():
            if score > best_score:
                best_lane = lane
                best_score = score
        return best_lane, best_score


class TrafficCounter:
    def __init__(self, lanes, class_names, counter_lane_name="count"):
        self.lanes = {}
        self.count_line = None
        for lane in lanes:
            name = lane["name"]
            points = lane["points"]
            poly = LineString(points)
            if poly.is_valid is False:
                logging.error(f"Lane {name} is invalid")
            if name == counter_lane_name:
                self.count_line = poly
            else:
                self.lanes[name] = poly

        # This ensures that we have a line for counting vehicles
        # as it is the primary output of the application
        if self.count_line is None:
            raise Exception(f"{counter_lane_name} not found in the config")
        self.vehicles = {}
        self.class_names = class_names

    def get_best_overlap_lane(self, point):
        best_lane = ""
        max_distance = 100000
        for lane_name, lane in self.lanes.items():
            distance = lane.distance(Point(point))
            if distance < max_distance:
                max_distance = distance
                best_lane = lane_name
        logging.info(f"{best_lane}: {max_distance} from {point}")
        return best_lane
    
    def update(self, trackers):
        """ Update finds the best matching lane number of each tracker.
        The points representing a lane and trackers should share the same coordination space
        because they are directly compared.
        """
        for tracker in trackers:
            # Step: Get vehicle of the tracker
            track_id = tracker[4]
            vehicle = self.vehicles.get(track_id, Vehicle(track_id))

            # Step: Update the vehicle class name and position
            track_name = self.class_names[int(tracker[-1])]
            track_pos = tracker[:4]
            vehicle.update_vehicle(track_name, track_pos)
            logging.info(f"{track_id}-{track_name}: {track_pos}")

            # Step: Find the best lane matched to the current vehicle position
            best_matched_lane = self.get_best_overlap_lane(vehicle.reference_point)
            if best_matched_lane != "":
                vehicle.score_lane(best_matched_lane)

            # Step: Mark the vehicle if it steps on the line to be counted
            if vehicle.is_counted is False and vehicle.is_intersected(self.count_line):
                vehicle.is_counted = True

            # Step: Store the updated vehicle
            self.vehicles[track_id] = vehicle

    def visualize(self, frame, trackers):
        for _, points in self.lanes.items():
            points = np.array(points, np.int32)
            points = points.reshape((-1, 1, 2))
            frame = cv2.polylines(frame, [points], isClosed=False, color=(0, 255, 255), thickness=4)
        
        points = np.array(self.count_line, np.int32)
        points = points.reshape((-1, 1, 2))
        frame = cv2.polylines(frame, [points], isClosed=False, color=(0, 0, 255), thickness=4)

        # We visualize only the vehicles being tracked currently
        # If we want to visualize all tracked vehicles use the for loop below
        # for vehicle_id, vehicle in self.vehicles.items():
        for tracker in trackers:
            track_id = tracker[4]
            vehicle = self.vehicles.get(track_id, None)
            if vehicle is None:
                continue
        
            vehicle_id = track_id
            name = vehicle.name
            l = vehicle.current_position[0]
            t = vehicle.current_position[1]
            r = vehicle.current_position[2]
            b = vehicle.current_position[3]
            best_lane, best_score = vehicle.get_best_lane()
            if vehicle.is_counted:
                frame = cv2.rectangle(frame, (int(l), int(t)), (int(r), int(b)), (255, 0, 0), 2)
            else:
                frame = cv2.rectangle(frame, (int(l), int(t)), (int(r), int(b)), (255, 255, 0), 2)
            ref_point = vehicle.reference_point
            frame = cv2.circle(frame, (int(ref_point[0]), int(ref_point[1])), 5, (255, 0, 0), -1)
            # frame = cv2.putText(frame, f'{int(vehicle_id)}', (int(ref_point[1]), int(ref_point[0])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
            frame = cv2.putText(frame, f'{int(vehicle_id)}:{name}', (int(l), int(t)-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
            frame = cv2.putText(frame, f'{best_lane}:{best_score}', (int(l), int(t)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
        return frame

    def report_results(self):
        total_count = 0
        count_per_lane = {}
        for vehicle_id, vehicle in self.vehicles.items():
            if not vehicle.is_counted:
                continue

            total_count += 1
            best_lane, _ = vehicle.get_best_lane()
            logging.info(f"{vehicle.name} ({vehicle_id}) is counted and stayed in lane {best_lane}")
            if best_lane != "":
                lane_count = count_per_lane.get(best_lane, 0)
                lane_count += 1
                count_per_lane[best_lane] = lane_count
        return total_count, count_per_lane

def main(args):
    if args.lanes_file:
        logging.info(f"Loading Lane configurations from {args.lanes_file}")
        lanes = json.loads(args.lanes_file.read_text())
    elif args.lanes != "":
        logging.info("Loading lane configurations from lanes argument")
        lanes = json.loads(args.lanes.strip())
    else:
        logging.error("No lane configurations provided")
        return -1

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
        timestamp = get_timestamp()

    logging.info("Loading models")
    class_names = load_class_names(args.labels)
    yolov7_main = YOLOv7_Main(args.model, args.det_thr, args.iou_thres)
    mot_tracker = Sort(max_age=args.max_age,
        min_hits=args.min_hits,
        iou_threshold=args.iou_thres) #create instance of the SORT tracker

    _, fps, width, height = get_stream_info(input_video_path)
    if args.output_file != "":
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # out_stream = cv2.VideoWriter(args.output_file, fourcc, fps, (int(width), int(height)), True)
        out_stream = cv2.VideoWriter(args.output_file, fourcc, fps, (640, 640), True)

    class_names = load_class_names(args.labels)
    traffic_counter = TrafficCounter(lanes, class_names)
    with Camera(Path(input_video_path)) as camera:
        for sample in camera.stream():
            frame = sample.data
            out_frame = cv2.resize(frame, (640, 640))

            # Step: Detection of vehicles
            detections = yolov7_main.run(frame)
            results = np.asarray(detections[0].cpu().detach())

            # Step: Update the trackers
            if len(results) == 0:
                logging.info("No detections")
                # SORT recommends updating it even with no detections
                trackers = mot_tracker.update()
            else:
                # for result in results:
                #     result[0] = result[0] * width/640  ## x1
                #     result[1] = result[1] * height/640  ## y1
                #     result[2] = result[2] * width/640  ## x2
                #     result[3] = result[3] * height/640  ## y2
                # results[:, 2:4] += results[:, 0:2] #convert to [x1,y1,w,h] to [x1,y1,x2,y2]
                det = results
                trackers = mot_tracker.update(det)

            # Step: Update the traffic counter for recognized tracks
            traffic_counter.update(trackers)

            # Step (optional): Visualize the result for validation
            # Passing the trackers allows visualization of vehicles currently being tracked.
            if args.output_file != "":
                out_frame = traffic_counter.visualize(out_frame, trackers)
                out_stream.write(cv2.cvtColor(out_frame, cv2.COLOR_RGB2BGR))
            # break
    if args.output_file != "":
        out_stream.release()

    with Plugin() as plugin:
        total_count, count_per_lane = traffic_counter.report_results()
        logging.info(f"Publishing total count: {total_count}")
        plugin.publish("env.traffic.count.total", total_count, timestamp=timestamp)

        for lane, count in count_per_lane.items():
            logging.info(f"Publishing count for {lane}: {count}")
            plugin.publish(f"env.traffic.count.{lane}", count, timestamp=timestamp)

        if args.output_file != "":
            logging.info(f"Uploading output video")
            plugin.upload_file(args.output_file, timestamp=timestamp)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Traffic counter')
    # Detection
    parser.add_argument('--model', type=Path, default=Path('model.pt'))
    parser.add_argument('--labels', dest='labels',
        action='store', default=Path('coco.names'), type=Path,
        help='Labels for detection')
    parser.add_argument("--detection-thres", dest='det_thr', type=float, default=0.5)
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')

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
    parser.add_argument(
        '--lanes-file', dest='lanes_file',
        action='store', type=Path,
        help='Path to coordinations of target lanes in json.')
    parser.add_argument(
        '--lanes', dest='lanes',
        action='store', type=str, default=os.getenv('LANES', ''),
        help='A string of coordinations of target lanes in json.')
    
    # Output
    parser.add_argument(
        '--output-file', dest='output_file',
        action='store', type=str, default='',
        help='Path to output video file for validation')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S')
    exit(main(args))