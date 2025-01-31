# Preparing for Target Scene
This application requires some meta information about the camera scene. The information informs the application on how to count vehicles per traffic lane.

1. Obtain an image from target camera. We recommend taking an image that clearly shows traffic lanes. For example, an image showing lanes without any vehicle in the lanes.

2. Run [prep-image.py](../scripts/prep-image.py) as follows,
```bash
# Assume an image from camera is in /path/to/image.jpg
python3 prep-image.py --input-path /path/to/image.jpg
```

The script will generate the same image in the same directory of the input image after resizing. This is the same resolution that the detection model sees. If the model does not resize images the same as the width and height of the script, change accordingly.

3. Run [lane-drawin.py](../scripts/lane-drawing.py) to mark individual lanes,
```bash
# The image_resized.jpg is generated from the previous step
python3 lane-drawing.py --image /path/to/image_resized.jpg
```

This Python is an interactive tool for drawing lanes and a line for counting vehicles. Drawing a line, named "count", to count traffic is __required__.  Follow the instructions below to draw the count line as well as lanes of interest,
- Write a name in the "Lane name" text box for a lane. Use a name that represents the lane. For example, "outgoing.straight" for a lane going straight. Click "Add a new lane" to add

> The lane names must consist of [a-z0-9_] and may be joined by `.` because those names are checked by Waggle when publishing a traffic count for the lane.

- Click points in the image that belong to the lane. The points and connected lines are later used to calculate whether a vehicle is in the lane. Make sure to have points well representing the lane.
- Add new lanes as needed. Lane names must be unique. Click name of the lane in the list box to select the lane.
- Click "Remove Last Point" to remove the last point of the selected lane.
- When done, Click "Save Lanes". A file named "out.json" is generated for all lanes with their points in it.