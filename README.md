### Abstract

I'm **Phu**. I work on computer vision and build the systems around it.

### Selected Work

<!-- feat:start -->
**[INT8 quantization for RF-DETR on TensorRT](https://github.com/roboflow/rf-detr/pull/1595)**&nbsp;&nbsp;[`roboflow/rf-detr`](https://github.com/roboflow/rf-detr)<br>`export(format="tensorrt", quantization="int8")` for detection, segmentation and keypoint models. I place the **Q/DQ nodes myself** on the FP16 graph, run the patch embedding as a **matrix multiply**, and fold **SmoothQuant scales** and **bias correction** into the backbone.<br>[`#1595`](https://github.com/roboflow/rf-detr/pull/1595) · [`#1627`](https://github.com/roboflow/rf-detr/pull/1627) · [`#1638`](https://github.com/roboflow/rf-detr/pull/1638) · [`#1642`](https://github.com/roboflow/rf-detr/pull/1642) · [`#1645`](https://github.com/roboflow/rf-detr/pull/1645)
<!-- feat:end -->

### Contributions

<!-- os:start -->
**[roboflow/rf-detr](https://github.com/roboflow/rf-detr)** ★9.9k · [30 merged](https://github.com/roboflow/rf-detr/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw) · +31979 −5533<br>
[`#1645`](https://github.com/roboflow/rf-detr/pull/1645)&nbsp;&nbsp;|&nbsp; perf(export): smooth the backbone norms and correct the MLP biases of TensorRT INT8 detection engines<br>
[`#1642`](https://github.com/roboflow/rf-detr/pull/1642)&nbsp;&nbsp;|&nbsp; perf(export): run the segmentation and keypoint INT8 patch embedding as a matrix multiply<br>
[`#1635`](https://github.com/roboflow/rf-detr/pull/1635)&nbsp;&nbsp;|&nbsp; feat(models): accept one `threshold` per class in `predict`<br>
[+27 more →](https://github.com/roboflow/rf-detr/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw)

**[roboflow/trackers](https://github.com/roboflow/trackers)** ★4k · [2 merged](https://github.com/roboflow/trackers/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw) · +239 −8<br>
[`#614`](https://github.com/roboflow/trackers/pull/614)&nbsp;&nbsp;|&nbsp; fix(ocsort): encode ORU virtual boxes with `bbox_to_measurement` for XCYCWH<br>
[`#613`](https://github.com/roboflow/trackers/pull/613)&nbsp;&nbsp;|&nbsp; fix(base): reject non-finite boxes before `update()` mutates tracker state

**[sunsmarterjie/yolov12](https://github.com/sunsmarterjie/yolov12)** ★3k · [1 merged](https://github.com/sunsmarterjie/yolov12/pulls?q=is%3Apr+is%3Amerged+author%3Althphuw) · +1 −1<br>
[`#174`](https://github.com/sunsmarterjie/yolov12/pull/174)&nbsp;&nbsp;|&nbsp; Fix DataLoader collate crash when a batch mixes background and labelled images
<!-- os:end -->
