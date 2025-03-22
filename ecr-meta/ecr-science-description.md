# Science
Understanding traffic volume is essential to estimate the flow of city traffic. We utilize deep neural networks and tracking algorithms to count the number of vehicles passing the street. YOLO v7 is a well-known object detection model based on deep neural networks. SORT is an object tracking method utilizing Kalman filter to calculate possible location of the target between two continuous frames. This application introduces a method that can count traffic volume using a video source.

# AI@Edge
The application either takes a live camera stream or file input to analyze the traffic. The images are then passed through the YOLO v7 [1] for vehicle detection and SORT [2] for vehicle tracking. The SORT method takes the bounding box of the vehicles and calculates possible location of the vehicle using Kalman filter. With the tracking result, we calculate traffic volume by counting individual vehicles that pass a virtual line. The virtual line represents the state that when a vehicle steps on the line it is counted for the traffic volume. The application takes various inputs to adjust parameters of the detection and tracking algorithms. This will allow users to fine-tune the parameters for better result. The application only considers vehicles such as car, truck, bus, and motorcycle.

# Using the Code
Output: counts of vehicles, counts of vehicles per lane if lane information is provided  
Input: camera stream or a video file
Image resolution (YOLOv7 input resolution): 640x640
Algorithms: YoloV7 for detection and SORT for tracking

# Arguments
Refer to the argument description,
```bash
python3 app.py --help
```

# Ontology:
The application publishes the topic "env.traffic.count.total" for total count of vehicles and topics "env.traffic.count.LANE_NAME" for given lanes. The total count should match with individual counts of the lanes.
 
# Inference Result from Sage Data Portal
To query the output from the plugin, you can do with Python library 'sage_data_client':
```
import sage_data_client

# query and load data into pandas data frame
df = sage_data_client.query(
    start="-1h",
    filter={
        "name": "env.traffic.count.*",
    }
)

# print results in data frame
print(df)
```
For more information, please see [Access and use data documentation](https://docs.waggle-edge.ai/docs/tutorials/accessing-data) and [sage_data_client](https://pypi.org/project/sage-data-client/).

# Running as a Sage Job
To run this as a job in Sage, a lane configuration for target camera should be passed to the application. See that the job specification below sets "LANES" environmental variable with the content from "secret.mysecret.RIGHTLANE."

```yaml
name: trafficcount-w064
plugins:
- name: trafficcounter-right
  pluginSpec:
    image: registry.sagecontinuum.org/yonghokim/traffic-counter:1.0.3
    args:
    - --stream
    - right_camera
    - --duration
    - "60"
    selector:
      resource.gpu: "true"
    env:
      LANES: '{secret.mysecret.RIGHTLANE}'
    resource:
      limit.cpu: "3"
      limit.memory: 3Gi
      request.cpu: "2"
      request.memory: 2Gi
nodes:
  W064: 1
scienceRules:
- 'schedule(trafficcounter-right): True'
```

First, follow [the document](https://github.com/waggle-sensor/plugin-trafficcounter/blob/main/docs/preparation.md) to prepare a configuration. Then, save the lane configuration in a file on the node and run the following command to create a Kubernetes secret for it.
```bash
# RIGHTLANE is a file containing the lane configuration for the "right" camera
kubectl -n ses create secret generic mysecret --from-file=RIGHTLANE
```

If you have 2 lane configurations for 2 cameras for a Sage node,
```bash
# Each file represents a lane configuration for the camera.
kubectl -n ses create secret generic mysecret --from-file=RIGHTLANE --from-file=LEFTLANE
```

> WARNING: You cannot create a secret if it exists. Delete one before creating a new one. To delete,
```bash
kubectl -n ses delete secret mysecret
```

Now, you can refer to the Sage job description to submit your job to the node.

# Reference
[1] Chien-Yao Wang, Alexey Bochkovskiy, and Hong-Yuan Mark Liao. "YOLOv7: Trainable bag-of-freebies sets new state-of-the-art for real-time object detectors." arXiv preprint arXiv:2207.02696 (2022).

[2] Alex Bewley, Zongyuan Ge, Lionel Ott, Fabio Ramos, and Ben Upcroft. "Simple online and realtime tracking." In 2016 IEEE international conference on image processing (ICIP), pp. 3464-3468. IEEE, 2016.
