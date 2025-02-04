# Traffic Counter
The full description of this application can be found [here](ecr-meta/ecr-science-description.md).

# Run
This application requires meta information regarding the scene for counting traffic. Read the [preparation](docs/preparation.md) to prepare a json file that indicates how the application should count vehicles.

## Recording a Video from Live Stream
```bash
# Record a 60 second video from given stream and
# save the video as sample.mp4
python3 record.py \
    --stream rtsp://mystream \
    --duration 60
```

## With an Input Video
```bash
# Take input.mp4 as an input
python3 app.py \
  --lanes-file /path/to/lanes.json \
  --input-file file:///path/to/input.mp4 \
```

## With a Live Stream
```bash
# Take a 60 second video from given stream
python3 app.py \
  --lanes-file /path/to/lanes.json \
  --stream rtsp://mystream \
  --duration 60
```

## Lane Configuration from String
```bash
# Lanes in a JSON-formatted string is also acceptable
# Make sure to use --lanes, not --lanes-file
python3 app.py \
  --lanes '[{"name": "mylane", "points": [[100, 100], [200, 200]]}"]' \
  --stream rtsp://mystream \
  --duration 60
```