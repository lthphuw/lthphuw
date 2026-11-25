### Abstract

I'm **Phu**. I work on computer vision and build the systems around it.

### Selected Work

<!-- feat:start -->
**[INT8 quantization for RF-DETR on TensorRT](https://github.com/roboflow/rf-detr/pull/1595)**&nbsp;&nbsp;[`roboflow/rf-detr`](https://github.com/roboflow/rf-detr)<br>`export(format="tensorrt", quantization="int8")` for detection, segmentation and keypoint models. I place the **Q/DQ nodes myself** on the FP16 graph, run the patch embedding as a **matrix multiply**, and fold **SmoothQuant scales** and **bias correction** into the backbone.<br>[`#1595`](https://github.com/roboflow/rf-detr/pull/1595) · [`#1627`](https://github.com/roboflow/rf-detr/pull/1627) · [`#1638`](https://github.com/roboflow/rf-detr/pull/1638) · [`#1642`](https://github.com/roboflow/rf-detr/pull/1642) · [`#1645`](https://github.com/roboflow/rf-detr/pull/1645)
<!-- feat:end -->

### Contributions

<!-- os:start -->
**[roboflow/rf-detr](https://github.com/roboflow/rf-detr)** ★10.2k · [32 merged](https://github.com/roboflow/rf-detr/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw) · +32288 −5566<br>
[`#1754`](https://github.com/roboflow/rf-detr/pull/1754)&nbsp;&nbsp;|&nbsp; perf(export): skip `decode_detections` debug stats when DEBUG is off<br>
[`#1751`](https://github.com/roboflow/rf-detr/pull/1751)&nbsp;&nbsp;|&nbsp; fix(export): name a CoreML export with an `FP16ComputePrecision` transform `fp16`<br>
[`#1645`](https://github.com/roboflow/rf-detr/pull/1645)&nbsp;&nbsp;|&nbsp; perf(export): smooth the backbone norms and correct the MLP biases of TensorRT INT8 detection engines<br>
[+29 more →](https://github.com/roboflow/rf-detr/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw)

**[roboflow/trackers](https://github.com/roboflow/trackers)** ★4k · [2 merged](https://github.com/roboflow/trackers/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw) · +239 −8<br>
[`#614`](https://github.com/roboflow/trackers/pull/614)&nbsp;&nbsp;|&nbsp; fix(ocsort): encode ORU virtual boxes with `bbox_to_measurement` for XCYCWH<br>
[`#613`](https://github.com/roboflow/trackers/pull/613)&nbsp;&nbsp;|&nbsp; fix(base): reject non-finite boxes before `update()` mutates tracker state

**[sunsmarterjie/yolov12](https://github.com/sunsmarterjie/yolov12)** ★3k · [1 merged](https://github.com/sunsmarterjie/yolov12/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw) · +1 −1<br>
[`#174`](https://github.com/sunsmarterjie/yolov12/pull/174)&nbsp;&nbsp;|&nbsp; Fix DataLoader collate crash when a batch mixes background and labelled images
<!-- os:end -->
