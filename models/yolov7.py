import torch
import torch.nn as nn
import cv2

from .common import Conv
from .experimental import Ensemble
from .utils.general import non_max_suppression


class YOLOv7_Main():
    def __init__(self, weightfile, class_names, detection_threshold, iou_threshold):
        self.det_thr = detection_threshold
        self.iou_thres = iou_threshold

        self.use_cuda = torch.cuda.is_available()
        if self.use_cuda:
            self.device = 'cuda'
        else:
            self.device = 'cpu'

        self.model = Ensemble()
        ckpt = torch.load(weightfile, map_location=self.device)
        self.model.append(ckpt['ema' if ckpt.get('ema') else 'model'].float().fuse().eval())  # FP32 model

        # Compatibility updates
        for m in self.model.modules():
            if type(m) in [nn.Hardswish, nn.LeakyReLU, nn.ReLU, nn.ReLU6, nn.SiLU]:
                m.inplace = True  # pytorch 1.7.0 compatibility
            elif type(m) is nn.Upsample:
                m.recompute_scale_factor = None  # torch 1.11.0 compatibility
            elif type(m) is Conv:
                m._non_persistent_buffers_set = set()  # pytorch 1.6.0 compatibility

        self.model = self.model.half()
        self.model.eval()

        self.class_names = class_names

    def prepare_input(self, frame, size=(640, 640)):
        sized = cv2.resize(frame, size)
        image = sized / 255.0
        image = image.transpose((2, 0, 1))
        image = torch.from_numpy(image).to(self.device).half()
        image = image.unsqueeze(0)
        return image

    def run(self, frame):
        image = self.prepare_input(frame)

        with torch.no_grad():
            pred = self.model(image)[0]
            pred = non_max_suppression(
                pred,
                self.det_thr,
                self.iou_thres,
                classes=self.class_names,
                agnostic=True
            )
        return pred