from PIL import Image
import torch
import numpy as np
import cv2
import matplotlib.pyplot as plt
import subprocess
import time
import psutil
import os
from nets.yolo import YoloBody

## 用于yolov7来对锚框解码的类
class YOLOV7DecodeBox():
    def __init__(self, anchors, num_classes, input_shape, anchors_mask = [[6,7,8], [3,4,5], [0,1,2]]):
        super(YOLOV7DecodeBox, self).__init__()
        self.anchors        = anchors
        self.num_classes    = num_classes
        self.bbox_attrs     = 5 + num_classes
        self.input_shape    = input_shape
        #-----------------------------------------------------------#
        #   13x13的特征层对应的anchor是[142, 110],[192, 243],[459, 401]
        #   26x26的特征层对应的anchor是[36, 75],[76, 55],[72, 146]
        #   52x52的特征层对应的anchor是[12, 16],[19, 36],[40, 28]
        #-----------------------------------------------------------#
        self.anchors_mask   = anchors_mask

    def decode_box(self, inputs):
        outputs = []
        for i, input in enumerate(inputs):
            batch_size = input.size(0)
            input_height = input.size(2)
            input_width = input.size(3)

            stride_h = self.input_shape[0] / input_height
            stride_w = self.input_shape[1] / input_width

            scaled_anchors = [(anchor_width, anchor_height)
                            for anchor_width, anchor_height in self.anchors[self.anchors_mask[i]]]

            # 调整输入张量形状
            prediction = input.view(batch_size, len(self.anchors_mask[i]),
                                    self.bbox_attrs, input_height, input_width).permute(0, 1, 3, 4, 2).contiguous()

            x = torch.sigmoid(prediction[..., 0])  # 中心 x
            y = torch.sigmoid(prediction[..., 1])  # 中心 y
            w = (torch.sigmoid(prediction[..., 2]) * 2) ** 2  # 宽度放大
            h = (torch.sigmoid(prediction[..., 3]) * 2) ** 2  # 高度放大
            conf = torch.sigmoid(prediction[..., 4])
            pred_cls = torch.sigmoid(prediction[..., 5:])

            device = input.device
            grid_x = torch.arange(input_width, device=device).repeat(input_height, 1).repeat(
                batch_size * len(self.anchors_mask[i]), 1, 1).view(x.shape) * stride_w
            grid_y = torch.arange(input_height, device=device).repeat(input_width, 1).t().repeat(
                batch_size * len(self.anchors_mask[i]), 1, 1).view(y.shape) * stride_h

            # 生成先验框宽高
            scaled_anchors_tensor = torch.tensor(scaled_anchors, dtype=torch.float32, device=device)
            anchor_w = scaled_anchors_tensor[:, 0:1].repeat(batch_size, 1, input_height * input_width).view(w.shape)
            anchor_h = scaled_anchors_tensor[:, 1:2].repeat(batch_size, 1, input_height * input_width).view(h.shape)

            # 真实尺度下的预测框
            pred_boxes = torch.zeros_like(prediction[..., :4], device=device)
            pred_boxes[..., 0] = x * stride_w + grid_x  # 中心点 x
            pred_boxes[..., 1] = y * stride_h + grid_y  # 中心点 y
            pred_boxes[..., 2] = w * anchor_w           # 宽度
            pred_boxes[..., 3] = h * anchor_h           # 高度

            # 组合输出
            output = torch.cat((pred_boxes.view(batch_size, -1, 4),
                                conf.view(batch_size, -1, 1),
                                pred_cls.view(batch_size, -1, self.num_classes)), -1)
            outputs.append(output)

        return torch.cat(outputs,dim=1)



## 用于加载目标检测模型的类
class BaseEngine(object):
    def __init__(self, model_path, use_gpu=True):
        """
        初始化推理引擎
        """
        self.mean = None
        self.std = None

        self.anchors_mask = [[6, 7, 8], [3, 4, 5], [0, 1, 2]]
        self.anchors, _ = get_anchors("./data/models/yolo_anchors.txt")
        self.phi = 'l'

        # 类别相关信息
        self.n_classes = 6      # 种类的个数
        self.imgsz = (640, 640)  # 默认值或文档中指定的大小

        # 设备选择
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        self.boxutil = YOLOV7DecodeBox(self.anchors, self.n_classes, input_shape=(640, 640), anchors_mask=self.anchors_mask) #实例化box工具类，得到正确的box
        print(f"Using device: {self.device}")
        print(f"Using model: {model_path}")

        self.model = YoloBody(self.anchors_mask, self.n_classes, self.phi, pretrained=False, phi_attention=0)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()


    def infer(self, img_tensor):
        """
        使用 PyTorch 实现的推理函数
        """
        # 先判断输入类型
        if isinstance(img_tensor, np.ndarray):
            img_tensor = torch.from_numpy(img_tensor).float()
        elif isinstance(img_tensor, Image.Image):
            img_tensor = torch.from_numpy(np.array(img_tensor)).float()
        else:
            raise TypeError("Unsupported input type: {}".format(type(img_tensor)))
        if len(img_tensor.shape) == 3:  # 如果缺少 batch 维度
            img_tensor = img_tensor.unsqueeze(0)

        # 将数据传输到 GPU
        img_tensor = img_tensor.to(self.device).float()

        # 确保模型在推理模式
        self.model.eval()

        # 禁用梯度计算以提高推理性能
        with torch.no_grad():
            # 执行推理
            outputs = self.boxutil.decode_box(self.model(img_tensor))    
            # 输出形状为 [batch_size,3 * (20*20 + 40*40 + 80*80), 5 + num_classes]
       
        # print(outputs.shape)

        # 如果模型输出在 GPU 上，将其传回 CPU
        if isinstance(outputs, torch.Tensor):
            outputs = outputs.cpu()

        # 将输出转换为 NumPy 格式
        if isinstance(outputs, torch.Tensor):
            outputs = outputs.numpy()
        elif isinstance(outputs, (list, tuple)):
            outputs = [out.cpu().numpy() if isinstance(out, torch.Tensor) else out for out in outputs]

        # print("outputs.shape",outputs.shape)
        # print("outputs[0].shape",outputs[0].shape)        

        return outputs[0]


    # 处理视频中的目标检测
    def detect_video(self, video_path, conf=0.5, end2end=False):
        cap = cv2.VideoCapture(video_path)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fps = int(round(cap.get(cv2.CAP_PROP_FPS)))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter('results.avi', fourcc, fps, (width, height))
        fps = 0
        import time
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            blob, ratio = preproc(frame, self.imgsz, self.mean, self.std)
            t1 = time.time()
            data = self.infer(blob)
            fps = (fps + (1. / (time.time() - t1))) / 2
            frame = cv2.putText(frame, "FPS:%d " % fps, (0, 40), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                (0, 0, 255), 2)
            if end2end:
                num, final_boxes, final_scores, final_cls_inds = data
                final_boxes = np.reshape(final_boxes / ratio, (-1, 4))
                dets = np.concatenate([final_boxes[:num[0]], np.array(final_scores)[:num[0]].reshape(-1, 1),
                                       np.array(final_cls_inds)[:num[0]].reshape(-1, 1)], axis=-1)
            else:
                dets = self.postprocess(data, ratio)

            if dets is not None:
                final_boxes, final_scores, final_cls_inds = dets[:,
                                                            :4], dets[:, 4], dets[:, 5]
                frame = vis(frame, final_boxes, final_scores, final_cls_inds,
                            conf=conf, class_names=self.class_names)
            cv2.imshow('frame', frame)
            out.write(frame)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
        out.release()
        cap.release()
        cv2.destroyAllWindows()

    # 将原始图像中的内容 + 检测框
    def inference(self, origin_img, conf=0.5, end2end=False):
        img, ratio = preproc(origin_img, self.imgsz, self.mean, self.std)
        data = self.infer(img)
        if end2end:
            num, final_boxes, final_scores, final_cls_inds = data
            final_boxes = np.reshape(final_boxes / ratio, (-1, 4))
            dets = np.concatenate([final_boxes[:num[0]], np.array(final_scores)[:num[0]].reshape(-1, 1),
                                   np.array(final_cls_inds)[:num[0]].reshape(-1, 1)], axis=-1)
        else:
            
            dets = self.postprocess(data, ratio)

        if dets is not None:
            final_boxes, final_scores, final_cls_inds = dets[:,
                                                        :4], dets[:, 4], dets[:, 5]
            origin_img = vis(origin_img, final_boxes, final_scores, final_cls_inds,
                             conf=conf, class_names=self.class_names)

        return origin_img

    # 对原始图像中内容检测，返回符合conf的检测结果
    def inference_dets(self, origin_img, conf=0.5, end2end=False, white_list=None):
        img, ratio = preproc(origin_img, self.imgsz, self.mean, self.std)
        data = self.infer(img)
        if end2end:
            num, final_boxes, final_scores, final_cls_inds = data
            final_boxes = np.reshape(final_boxes / ratio, (-1, 4))
            dets = np.concatenate([final_boxes[:num[0]], np.array(final_scores)[:num[0]].reshape(-1, 1),
                                   np.array(final_cls_inds)[:num[0]].reshape(-1, 1)], axis=-1)
        else:
            dets = self.postprocess(data, ratio, nms_threshold=0.2)

        if dets is not None:
            final_dets = []
            for i in range(dets.shape[0]):
                if (white_list is None or dets[i, 5] in white_list) and dets[i, 4] >= conf:
                    final_dets = np.concatenate((final_dets, dets[i, :]))
            if np.array(final_dets).shape != (0,):
                final_dets = final_dets.reshape([-1, 6])
                final_dets = np.concatenate((np.int_(final_dets[:, :4]), final_dets[:, 4:6]), axis=1)
        else:
            final_dets = []

        return final_dets

    ## 用于 > yolov8
    # @staticmethod
    # def postprocess(predictions, ratio, conf_threshold=0.2, nms_threshold=0.6):
    #     """
    #     后处理，将预测框从中心点格式转换为边界框，并应用 NMS
    #     """
    #     # 提取预测框信息
    #     boxes = predictions[:4, :]  # 前 4 行是锚框 [cx, cy, w, h]
    #     scores = predictions[4:, :]  # 从第 6 行开始是类别概率

    #     # 中心点、宽高 -> 边界框 [x_min, y_min, x_max, y_max]
    #     boxes_xyxy = np.zeros_like(boxes.T)
    #     boxes_xyxy[:, 0] = boxes[0, :] - boxes[2, :] / 2.0  # x_min
    #     boxes_xyxy[:, 1] = boxes[1, :] - boxes[3, :] / 2.0  # y_min
    #     boxes_xyxy[:, 2] = boxes[0, :] + boxes[2, :] / 2.0  # x_max
    #     boxes_xyxy[:, 3] = boxes[1, :] + boxes[3, :] / 2.0  # y_max

    #     # 应用缩放比例还原到原图尺寸
    #     boxes_xyxy /= ratio

    #     # print(boxes_xyxy.shape, scores.shape)

    #     # 非极大值抑制 (NMS)
    #     dets = multiclass_nms(boxes_xyxy, scores.T, nms_thr=nms_threshold, score_thr=conf_threshold)

    #     return dets
    

    # # 用于 < yolov7
    # # 对预测后的结果进行nms处理，返回处理后的dets
    # @staticmethod
    # def postprocess(predictions, ratio, conf_threshold=0.65, nms_threshold=0.5):
    #     """
    #     后处理函数，处理yolo的预测输出
    #     """
    #     # 取出预测框和置信度
    #     boxes = predictions[:, :4]
    #     scores = predictions[:, 4] * predictions[:, 5:]  # obj_conf * cls_conf

    #     # 将xywh转为xyxy
    #     boxes_xyxy = np.ones_like(boxes)
    #     boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.  # x1
    #     boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.  # y1
    #     boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.  # x2
    #     boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.  # y2

    #     # 缩放到原图尺寸
    #     boxes_xyxy /= ratio

    #     # 应用非极大值抑制
    #     dets = multiclass_nms(boxes_xyxy, scores, nms_thr=nms_threshold, score_thr=conf_threshold)

    #     return dets

    @staticmethod 
    def postprocess(predictions, ratio, conf_threshold=0.65, nms_threshold=0.3):
        """后处理函数，具有更严格的阈值和额外的过滤逻辑"""
        
        # 取出预测框和置信度
        boxes = predictions[:, :4]
        scores = predictions[:, 4:5] * predictions[:, 5:]  # obj_conf * cls_conf
        
        # 将xywh转为xyxy
        boxes_xyxy = np.ones_like(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.  # x1
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.  # y1
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.  # x2
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.  # y2
        
        # 缩放到原图尺寸
        boxes_xyxy /= ratio
        
        # # 过滤掉异常大小的框
        # width = boxes_xyxy[:, 2] - boxes_xyxy[:, 0]
        # height = boxes_xyxy[:, 3] - boxes_xyxy[:, 1]
        # aspect_ratio = width / (height + 1e-6)
        
        # # 保留合理宽高比的框 (0.2 到 5.0 之间)
        # valid_aspect_ratio = (aspect_ratio > 0.2) & (aspect_ratio < 5.0)
        # boxes_xyxy = boxes_xyxy[valid_aspect_ratio]
        # scores = scores[valid_aspect_ratio]
        
        # 应用非极大值抑制
        dets = multiclass_nms(
            boxes_xyxy, 
            scores, 
            nms_thr=nms_threshold,
            score_thr=conf_threshold
        )
    
        return dets

    def get_fps(self):
        import time
        img = np.ones((1, 3, self.imgsz[0], self.imgsz[1]))
        img = np.ascontiguousarray(img, dtype=np.float32)
        for _ in range(5):  # warmup
            _ = self.infer(img)

        t0 = time.perf_counter()
        for _ in range(100):  # calculate average time
            _ = self.infer(img)
        print(100 / (time.perf_counter() - t0), 'FPS')

# 改进后的单类别NMS实现
def nms(boxes, scores, nms_thr):
    """Single class NMS with improved filtering."""
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
            
        # 计算交集区域
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        # 使用面积比率和IoU双重过滤
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        
        # 同时满足IoU阈值和面积比例要求
        inds = np.where((ovr <= nms_thr))[0]
        order = order[inds + 1]

    return keep

def multiclass_nms(boxes, scores, nms_thr=0.45, score_thr=0.65):
    """Multiclass NMS with improved thresholds and filtering"""
    final_dets = []
    num_classes = scores.shape[1]
    
    # 对每个类别分别进行NMS
    for cls_ind in range(num_classes):
        cls_scores = scores[:, cls_ind]
        
        # 提高置信度阈值的过滤
        valid_score_mask = cls_scores > score_thr
        if valid_score_mask.sum() == 0:
            continue
        
        valid_scores = cls_scores[valid_score_mask]
        valid_boxes = boxes[valid_score_mask]
        
        # 应用NMS
        keep = nms(valid_boxes, valid_scores, nms_thr)
        if len(keep) > 0:
            cls_inds = np.ones((len(keep), 1)) * cls_ind
            dets = np.concatenate(
                [valid_boxes[keep], valid_scores[keep, None], cls_inds], 1
            )
            final_dets.append(dets)
    
    if len(final_dets) == 0:
        return None
        
    return np.concatenate(final_dets, 0)



# # 非极大值抑制，返回满足条件的框
# def nms(boxes, scores, nms_thr):
#     """Single class NMS implemented in Numpy."""
#     x1 = boxes[:, 0]
#     y1 = boxes[:, 1]
#     x2 = boxes[:, 2]
#     y2 = boxes[:, 3]

#     areas = (x2 - x1 + 1) * (y2 - y1 + 1)
#     order = scores.argsort()[::-1]

#     keep = []
#     while order.size > 0:
#         i = order[0]
#         keep.append(i)
#         xx1 = np.maximum(x1[i], x1[order[1:]])
#         yy1 = np.maximum(y1[i], y1[order[1:]])
#         xx2 = np.minimum(x2[i], x2[order[1:]])
#         yy2 = np.minimum(y2[i], y2[order[1:]])

#         w = np.maximum(0.0, xx2 - xx1 + 1)
#         h = np.maximum(0.0, yy2 - yy1 + 1)
#         inter = w * h
#         ovr = inter / (areas[i] + areas[order[1:]] - inter)

#         inds = np.where(ovr <= nms_thr)[0]
#         order = order[inds + 1]

#     return keep

# # 多目标非极大值抑制，返回满足条件的框
# def multiclass_nms(boxes, scores, nms_thr, score_thr):
#     """Multiclass NMS implemented in Numpy"""
#     final_dets = []
#     num_classes = scores.shape[1]
#     for cls_ind in range(num_classes):
#         cls_scores = scores[:, cls_ind]
#         valid_score_mask = cls_scores > score_thr
#         if valid_score_mask.sum() == 0:
#             continue
#         else:
#             valid_scores = cls_scores[valid_score_mask]
#             valid_boxes = boxes[valid_score_mask]
#             keep = nms(valid_boxes, valid_scores, nms_thr)
#             if len(keep) > 0:
#                 cls_inds = np.ones((len(keep), 1)) * cls_ind
#                 dets = np.concatenate(
#                     [valid_boxes[keep], valid_scores[keep, None], cls_inds], 1
#                 )
#                 final_dets.append(dets)
#     if len(final_dets) == 0:
#         return None
#     return np.concatenate(final_dets, 0)

# 将图片内容进行归一化处理(mean,std)   swap:表示交换纬度 将[高，宽，通道]变为[通道，高，宽]
def preproc(image, input_size, mean, std, swap=(2, 0, 1)):
    ## 表示用灰色来填补图片空缺
    if len(image.shape) == 3:
        padded_img = np.ones((input_size[0], input_size[1], 3)) * 114.0
    else:
        padded_img = np.ones(input_size) * 114.0

    img = np.array(image)
    r = min(input_size[0] / img.shape[0], input_size[1] / img.shape[1])
    resized_img = cv2.resize(
        img,
        (int(img.shape[1] * r), int(img.shape[0] * r)),
        interpolation=cv2.INTER_LINEAR,
    ).astype(np.float32)

    padded_img[: int(img.shape[0] * r), : int(img.shape[1] * r)] = resized_img
    # if use yolox set
    # padded_img = padded_img[:, :, ::-1]
    # padded_img /= 255.0
    padded_img = padded_img[:, :, ::-1]
    padded_img /= 255.0

    if mean is not None:
        padded_img -= mean
    if std is not None:
        padded_img /= std

    padded_img = padded_img.transpose(swap)
    padded_img = np.ascontiguousarray(padded_img, dtype=np.float32)
    return padded_img, r

# 返回一个(size,3)的颜色三元色数组
def rainbow_fill(size=50):  # simpler way to generate rainbow color
    cmap = plt.get_cmap('jet')
    color_list = []

    for n in range(size):
        color = cmap(n / size)
        color_list.append(color[:3])  # might need rounding? (round(x, 3) for x in color)[:3]

    return np.array(color_list)


_COLORS = rainbow_fill(100).astype(np.float32).reshape(-1, 3)

# 将img的内容上方，添加框，置信度，类别加入，返回得到的img【处理多个框目标】
def vis(img, boxes, scores, cls_ids, conf=0.2, class_names=None):
    # 如果数组不可写，创建一个新的副本
    if not img.flags.writeable:
        img = img.copy()

    for i in range(len(boxes)):
        box = boxes[i]
        cls_id = int(cls_ids[i])
        score = scores[i]
        if score < conf:
            continue
        x0 = int(box[0])
        y0 = int(box[1])
        x1 = int(box[2])
        y1 = int(box[3])

        color = (_COLORS[cls_id] * 255).astype(np.uint8).tolist()
        
        text = '{}:{:.1f}%'.format(class_names[cls_id], score * 100)
        txt_color = (0, 0, 0) if np.mean(_COLORS[cls_id]) > 0.5 else (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX

        txt_size = cv2.getTextSize(text, font, 0.4, 1)[0]
        cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)

        txt_bk_color = (_COLORS[cls_id] * 255 * 0.7).astype(np.uint8).tolist()
        cv2.rectangle(
            img,
            (x0, y0 + 1),
            (x0 + txt_size[0] + 1, y0 + int(1.5 * txt_size[1])),
            txt_bk_color,
            -1
        )
        cv2.putText(img, text, (x0, y0 + txt_size[1]), font, 0.4, txt_color, thickness=1)

    return img

# 将未排除的目标框显示出来【显示出单个框目标】【没用】
def vis_the_target(img, box, score, class_name):

    # 如果数组不可写，创建一个新的副本
    if not img.flags.writeable:
        img = img.copy()
    x0 = int(box[0])
    y0 = int(box[1])
    x1 = int(box[2])
    y1 = int(box[3])

    color = [0, 0, 255]
    text = '{}:{:.1f}%'.format(class_name, score * 100)
    txt_color = (255, 255, 255)
    font = cv2.FONT_HERSHEY_SIMPLEX

    txt_size = cv2.getTextSize(text, font, 0.4, 1)[0]
    cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)

    txt_bk_color = [0, 0, 179]
    cv2.rectangle(
        img,
        (x0, y0 + 1),
        (x0 + txt_size[0] + 1, y0 + int(1.5 * txt_size[1])),
        txt_bk_color,
        -1
    )
    cv2.putText(img, text, (x0, y0 + txt_size[1]), font, 0.4, txt_color, thickness=1)

    return img

# 将被排除的目标框显示出来【没用】
def vis_object_excepted_the_target(img, boxes, scores, cls_ids, class_names=None, target_index=-1):

    # 如果数组不可写，创建一个新的副本
    if not img.flags.writeable:
        img = img.copy()
    for i in range(len(boxes)):
        if i == target_index:
            continue

        box = boxes[i]
        cls_id = int(cls_ids[i])
        score = scores[i]

        x0 = int(box[0])
        y0 = int(box[1])
        x1 = int(box[2])
        y1 = int(box[3])

        color = [255, 0, 0]
        text = '{}:{:.1f}%'.format(class_names[cls_id], score * 100)
        txt_color = (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX

        txt_size = cv2.getTextSize(text, font, 0.4, 1)[0]
        cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)

        txt_bk_color = [179, 0, 0]
        cv2.rectangle(
            img,
            (x0, y0 + 1),
            (x0 + txt_size[0] + 1, y0 + int(1.5 * txt_size[1])),
            txt_bk_color,
            -1
        )
        cv2.putText(img, text, (x0, y0 + txt_size[1]), font, 0.4, txt_color, thickness=1)

    return img

# 检测模式的目标可视化
def vis_track_mode(img, boxes, scores, cls_ids, class_names=None, target_index=-1):
    # 如果数组不可写，创建一个新的副本
    if not img.flags.writeable:
        img = img.copy()

    for i in range(len(boxes)):
        if i == target_index:  # 将未被检测过的内容设为蓝色
            color = [0, 0, 255]
            txt_bk_color = [0, 0, 179]
        else:
            color = [255, 0, 0]  # 将要检测过的目标设为红色
            txt_bk_color = [179, 0, 0]

        box = boxes[i]
        cls_id = int(cls_ids[i])
        score = scores[i]

        x0 = int(box[0])
        y0 = int(box[1])
        x1 = int(box[2])
        y1 = int(box[3])


        text = '{}:{:.1f}%'.format(class_names[cls_id], score * 100)
        txt_color = (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX

        txt_size = cv2.getTextSize(text, font, 0.4, 1)[0]
        cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)

        cv2.rectangle(
            img,
            (x0, y0 + 1),
            (x0 + txt_size[0] + 1, y0 + int(1.5 * txt_size[1])),
            txt_bk_color,
            -1
        )
        cv2.putText(img, text, (x0, y0 + txt_size[1]), font, 0.4, txt_color, thickness=1)

    return img


# 可视化单个目标框【且可以对框自定义颜色】
def vis_single_object(img, box, score, class_name, color):
    """
    在图像中绘制单个目标的边界框和标签信息。
    :param img: 输入图像
    :param box: 目标的边界框
    :param score: 目标的置信度
    :param class_name: 目标的类名
    :param color: 目标框的颜色
    :return: 绘制了目标框的图像
    """
    if not img.flags.writeable:
        img = img.copy()

    # 提取边界框的坐标
    x0, y0, x1, y1 = map(int, box)

    text = '{}:{:.1f}%'.format(class_name, score * 100)
    txt_color = (255, 255, 255)  # 文本颜色（白色）
    font = cv2.FONT_HERSHEY_SIMPLEX

    txt_size = cv2.getTextSize(text, font, 0.4, 1)[0]

    # print("new color: ",color)

    # 绘制目标框
    cv2.rectangle(img, (x0, y0), (x1, y1), color, 2)

    # 绘制标签背景
    txt_bk_color = [int(i * 0.7) for i in color]  # 背景颜色稍微深一点
    cv2.rectangle(
        img,
        (x0, y0 + 1),
        (x0 + txt_size[0] + 1, y0 + int(1.5 * txt_size[1])),
        txt_bk_color,
        -1
    )

    # 绘制文本（类名和置信度）
    cv2.putText(img, text, (x0, y0 + txt_size[1]), font, 0.4, txt_color, thickness=1)

    return img

def vis_botsort_track_mode(frame, boxes, ids, scores, cls_id, cls_name, current_target_id, tracked_target_ids):
    """
    绘制目标框，并根据目标的状态标记不同颜色的框。
    :param frame: 输入图像（当前帧）
    :param boxes: 目标的边界框
    :param ids: 目标的ID列表
    :param scores: 目标的置信度列表
    :param current_target_id: 当前正在跟踪的目标ID
    :param tracked_target_ids: 已跟踪过的目标ID列表
    :return: 绘制了目标框的图像
    """
    online_im = frame.copy()  # 创建当前帧的副本

    for i, box in enumerate(boxes):
        target_id = ids[i]  # 获取当前目标的ID
        score = scores[i]  # 获取当前目标的置信度
        cls = cls_id[i]  # 获取当前目标的类别

        # 设置目标框的颜色
        if target_id == current_target_id:
            color = [0, 0, 255]  # 蓝色（正在跟踪的目标）
        elif target_id in tracked_target_ids:
            color = [0, 255, 0]  # 绿色（已经跟踪过的目标）
        else:
            color = [255, 0, 0]  # 红色（其他所有目标）
        
        # if color == [0, 0, 255]:
            # print("color: ",color)

        # 绘制目标框及ID
        online_im = vis_single_object(online_im, box, score, f"ID: {target_id} Class: {cls_name[cls]}", color)

    return online_im



def tlwh2xyxy(boxes):
    """
    将预测的(top, left, width, height)形式转换成(xmin, ymin, xmax, ymax)形式
    """
    # 将 tlwh 转换为 xyxy
    xyxy_boxes = np.zeros_like(boxes)
    xyxy_boxes[:, 0] = boxes[:, 0]  # x1 = tlx
    xyxy_boxes[:, 1] = boxes[:, 1]  # y1 = tly
    xyxy_boxes[:, 2] = boxes[:, 0] + boxes[:, 2]  # x2 = tlx + width
    xyxy_boxes[:, 3] = boxes[:, 1] + boxes[:, 3]  # y2 = tly + height

    return xyxy_boxes


# 用于得到先验框的内容
def get_anchors(anchors_path):
    '''loads the anchors from a file'''
    with open(anchors_path, encoding='utf-8') as f:
        anchors = f.readline()
    anchors = [float(x) for x in anchors.split(',')]
    anchors = np.array(anchors).reshape(-1, 2)
    return anchors, len(anchors)


def run_bat_file(bat_file_path):
    """运行批处理文件"""
    try:
        subprocess.Popen(bat_file_path, shell=True)
        print("批处理文件启动成功。")
    except subprocess.CalledProcessError as e:
        print(f"运行批处理文件失败: {e}")
    except PermissionError as e:
        print(f"权限错误: {e}")

def is_ue_running():
    """检查 Unreal Engine 是否在运行"""
    for process in psutil.process_iter(['name']):
        if process.info['name'] and "UE4Editor" in process.info['name']:  # Unreal Engine 的进程名称
            return True
    return False

def close_UE():
    """关闭 Unreal Engine"""
    if is_ue_running():
        run_bat_file(r"E:\UAV_temp_staging\demo_code\python\Shell\close_ue4.bat")

def wait_for_ue_shutdown(timeout=30):
    """等待 UE 完全关闭"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_ue_running():
            return True
        time.sleep(1)  # 每秒检查一次
    return False

def wait_for_ue_startup(timeout=30):
    """等待 UE 完全启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_ue_running():
            return True
        time.sleep(1)  # 每秒检查一次
    return False

def restart_UE(startup_bat_file_path):
    """重启 Unreal Engine"""
    close_UE()
    # print("1111")

    if wait_for_ue_shutdown(timeout=30):  # 等待 UE 关闭，超时时间为 30 秒
        # 如果 UE 关闭成功，运行启动批处理文件
        run_bat_file(startup_bat_file_path)
        print(2222)
        if wait_for_ue_startup(timeout=30):  # 等待 UE 启动，超时时间为 30 秒
            return True
    else:
        print("无法重启 Unreal Engine，因为未成功关闭。")

    return False

def create_directory_if_not_exists(directory):
    try:
        os.makedirs(directory, exist_ok=False)  # 当目录不存在时创建目录
    except FileExistsError:
        pass 





#################### 以下为yolov7x的相关函数 #################### 
#---------------------------------------------------------#
#   将图像转换成RGB图像，防止灰度图在预测时报错。
#   代码仅仅支持RGB图像的预测，所有其它类型的图像都会转化成RGB
#---------------------------------------------------------#
def cvtColor(image):
    if len(np.shape(image)) == 3 and np.shape(image)[2] == 3:
        return image 
    else:
        image = image.convert('RGB')
        return image 

#---------------------------------------------------#
#   对输入图像进行resize
#---------------------------------------------------#
def resize_image(image, size, letterbox_image):
    iw, ih  = image.size
    w, h    = size
    if letterbox_image:
        scale   = min(w/iw, h/ih)
        nw      = int(iw*scale)
        nh      = int(ih*scale)

        image   = image.resize((nw,nh), Image.BICUBIC)
        new_image = Image.new('RGB', size, (128,128,128))
        new_image.paste(image, ((w-nw)//2, (h-nh)//2))
    else:
        new_image = image.resize((w, h), Image.BICUBIC)
    return new_image

#---------------------------------------------------#
#   获得类
#---------------------------------------------------#
def get_classes(classes_path):
    with open(classes_path, encoding='utf-8') as f:
        class_names = f.readlines()
    class_names = [c.strip() for c in class_names]
    return class_names, len(class_names)

#---------------------------------------------------#
#   获得先验框
#---------------------------------------------------#
def get_anchors(anchors_path):
    '''loads the anchors from a file'''
    with open(anchors_path, encoding='utf-8') as f:
        anchors = f.readline()
    anchors = [float(x) for x in anchors.split(',')]
    anchors = np.array(anchors).reshape(-1, 2)
    return anchors, len(anchors)
    
#---------------------------------------------------#
#   获得学习率
#---------------------------------------------------#
def get_lr(optimizer):
    for param_group in optimizer.param_groups:
        return param_group['lr']

def preprocess_input(image):
    image /= 255.0
    return image

def show_config(**kwargs):
    print('Configurations:')
    print('-' * 70)
    print('|%25s | %40s|' % ('keys', 'values'))
    print('-' * 70)
    for key, value in kwargs.items():
        print('|%25s | %40s|' % (str(key), str(value)))
    print('-' * 70)
        
def download_weights(phi, model_dir="./model_data"):
    import os
    from torch.hub import load_state_dict_from_url
    
    download_urls = {
        "l" : 'https://github.com/bubbliiiing/yolov7-pytorch/releases/download/v1.0/yolov7_backbone_weights.pth',
        "x" : 'https://github.com/bubbliiiing/yolov7-pytorch/releases/download/v1.0/yolov7_x_backbone_weights.pth',
    }
    url = download_urls[phi]
    
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    load_state_dict_from_url(url, model_dir)