FROM waggle/plugin-base:1.1.1-ml-torch1.9

RUN apt-get update \
  && apt-get install ffmpeg libsm6 libxext6  -y

COPY requirements.txt /app/
RUN pip3 install --upgrade pip \
  && pip3 install --no-cache-dir -r /app/requirements.txt

ADD https://web.lcrc.anl.gov/public/waggle/models/vehicletracking/yolov7.pt /app/model.pt

# This allows PyWaggle to do test runs without Waggle Software Stack.
# data-config.json is populated by Waggle Software Stack at runtime.
RUN mkdir -p /run/waggle \
  && echo "[]" >> /run/waggle/data-config.json

WORKDIR /app
COPY models/ /app/models
COPY app.py record.py coco.names /app/

# COPY data/sample.mp4 data/lanes.json /app/

ENTRYPOINT ["python3", "/app/app.py"]