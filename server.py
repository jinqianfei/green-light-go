"""
绿灯行 - 红绿灯识别服务器
部署方式：
  1. pip install flask flask-cors ultralytics opencv-python-headless --break-system-packages
  2. python server.py
  3. 浏览器打开 http://localhost:5000

云部署（Render/Railway）：
  - 设置环境变量 YOLO_MODEL_PATH=yolov8n.pt（或上传模型文件）
  - 端口由平台自动注入（PORT 环境变量）
"""

import os
import io
import json
import base64
import numpy as np
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from ultralytics import YOLO
import cv2

app = Flask(__name__)

# CORS：允许前端跨域访问
CORS(app)

# ===== 配置 =====
PORT = int(os.environ.get('PORT', 5000))
MODEL_PATH = os.environ.get('YOLO_MODEL_PATH', 'yolov8n.pt')

# ===== 加载YOLOv8模型 =====
print("正在加载YOLOv8n模型: {} ...".format(MODEL_PATH))
model = YOLO(MODEL_PATH)
print("模型加载完成！")

# COCO数据集中交通灯的class ID是9
TRAFFIC_LIGHT_CLASS_ID = 9


def analyze_traffic_light_color(image, box):
    """
    分析检测到的红绿灯区域的颜色
    box格式: [x1, y1, x2, y2]
    返回: "red" / "green" / "yellow" / "unknown"
    """
    x1, y1, x2, y2 = map(int, box)

    # 裁剪红绿灯区域
    h, w = image.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    if x2 - x1 < 5 or y2 - y1 < 5:
        return "unknown", 0.0

    roi = image[y1:y2, x1:x2]

    # 转换到HSV颜色空间（更适合颜色判断）
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # 定义颜色范围
    # 红色（在HSV中红色分两段：低H和高H）
    red_lower1 = np.array([0, 100, 100])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 100, 100])
    red_upper2 = np.array([180, 255, 255])

    # 绿色
    green_lower = np.array([35, 100, 100])
    green_upper = np.array([85, 255, 255])

    # 黄色
    yellow_lower = np.array([15, 100, 100])
    yellow_upper = np.array([35, 255, 255])

    # 计算各颜色像素数量
    mask_red1 = cv2.inRange(hsv, red_lower1, red_upper1)
    mask_red2 = cv2.inRange(hsv, red_lower2, red_upper2)
    mask_red = mask_red1 + mask_red2

    mask_green = cv2.inRange(hsv, green_lower, green_upper)
    mask_yellow = cv2.inRange(hsv, yellow_lower, yellow_upper)

    total_pixels = roi.shape[0] * roi.shape[1]
    red_ratio = np.count_nonzero(mask_red) / total_pixels
    green_ratio = np.count_nonzero(mask_green) / total_pixels
    yellow_ratio = np.count_nonzero(mask_yellow) / total_pixels

    # 判断主色调
    ratios = {
        "red": red_ratio,
        "green": green_ratio,
        "yellow": yellow_ratio,
    }

    max_color = max(ratios, key=ratios.get)
    max_ratio = ratios[max_color]

    # 置信度：基于主色调占比
    confidence = min(max_ratio * 5, 1.0)  # 放大5倍，上限1.0

    # 如果最大占比太小，认为无法判断
    if max_ratio < 0.02:
        return "unknown", round(confidence, 2)

    return max_color, round(confidence, 2)


@app.route("/")
def index():
    """返回主页面"""
    return send_file("绿灯行真实版.html")


@app.route("/api/detect", methods=["POST"])
def detect():
    """
    接收摄像头截图，识别红绿灯
    请求体: { "image": "base64编码的JPEG图片" }
    返回: { "detected": bool, "color": str, "confidence": float, "boxes": list }
    """
    try:
        data = request.get_json()

        if not data or "image" not in data:
            return jsonify({"error": "缺少image参数"}), 400

        # 解码base64图片
        image_data = base64.b64decode(data["image"])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return jsonify({"error": "图片解码失败"}), 400

        # YOLO检测
        results = model(image, verbose=False)

        # 查找交通灯
        boxes = []
        detected = False
        best_color = "unknown"
        best_confidence = 0.0

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id == TRAFFIC_LIGHT_CLASS_ID:
                    detected = True
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    det_confidence = float(box.conf[0])

                    # 分析颜色
                    color, color_conf = analyze_traffic_light_color(image, [x1, y1, x2, y2])

                    boxes.append({
                        "x1": round(x1, 1),
                        "y1": round(y1, 1),
                        "x2": round(x2, 1),
                        "y2": round(y2, 1),
                        "detection_confidence": round(det_confidence, 2),
                        "color": color,
                        "color_confidence": color_conf,
                    })

                    # 取置信度最高的结果
                    combined_conf = det_confidence * color_conf
                    if combined_conf > best_confidence:
                        best_confidence = combined_conf
                        best_color = color

        return jsonify({
            "detected": detected,
            "color": best_color,
            "confidence": round(best_confidence, 2),
            "boxes": boxes,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    """健康检查接口"""
    return jsonify({"status": "ok", "model": "yolov8n"})


if __name__ == "__main__":
    print("=" * 50)
    print("  绿灯行 - 红绿灯识别服务器")
    print("=" * 50)
    print()
    print("  本机访问: http://localhost:{}".format(PORT))
    print("  手机访问: http://<电脑IP>:{}".format(PORT))
    print()
    print("  确保手机和电脑在同一个WiFi下")
    print("  按 Ctrl+C 停止服务器")
    print("=" * 50)

    app.run(host="0.0.0.0", port=PORT, debug=False)
