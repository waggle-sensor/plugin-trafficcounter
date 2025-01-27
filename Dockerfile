FROM waggle/plugin-base:1.1.1-ml-torch1.9

RUN apt-get update \
  && apt-get install -y \
  ffmpeg \
  && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
  && apt-get install ffmpeg libsm6 libxext6  -y

COPY requirements.txt /app/
RUN pip3 install --upgrade pip \
  && pip3 install --no-cache-dir --upgrade -r /app/requirements.txt

ADD https://web.lcrc.anl.gov/public/waggle/models/vehicletracking/yolov7.pt /app/model.pt

# This allows PyWaggle to do test runs without Waggle Software Stack.
# data-config.json is populated by Waggle Software Stack at runtime.
RUN mkdir -p /run/waggle \
  && echo "[]" >> /run/waggle/data-config.json

# COPY utils/ /app/utils
# COPY models/ /app/models
# COPY app.py app_utils.py sort.py coco.names /app/

ENTRYPOINT ["python3", "/app/app.py"]