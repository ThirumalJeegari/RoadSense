from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image


def analyze_road_image(image_bytes: bytes) -> dict:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    original_width, original_height = image.size
    image.thumbnail((960, 960))
    processed_width, processed_height = image.size
    rgb = np.array(image)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 45, 135)
    dark_threshold = np.percentile(gray, 38)
    dark_regions = (gray < dark_threshold).astype(np.uint8) * 255
    candidate = cv2.bitwise_and(edges, dark_regions)

    kernel = np.ones((3, 3), np.uint8)
    candidate = cv2.dilate(candidate, kernel, iterations=1)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(candidate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections = []
    damaged_pixels = 0
    annotated = bgr.copy()

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 35:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        aspect = max(w / max(h, 1), h / max(w, 1))
        if area < 80 and aspect < 2.5:
            continue
        start_point, end_point = _damage_endpoints(contour, x, y, w, h)
        original_start = _scale_point(start_point, processed_width, processed_height, original_width, original_height)
        original_end = _scale_point(end_point, processed_width, processed_height, original_width, original_height)
        from_zone = _human_zone(start_point, processed_width, processed_height)
        to_zone = _human_zone(end_point, processed_width, processed_height)
        damaged_pixels += int(area)
        detections.append(
            {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "x_start": int(start_point[0]),
                "y_start": int(start_point[1]),
                "x_end": int(end_point[0]),
                "y_end": int(end_point[1]),
                "from_point": f"({int(start_point[0])}, {int(start_point[1])})",
                "to_point": f"({int(end_point[0])}, {int(end_point[1])})",
                "original_from_point": f"({original_start[0]}, {original_start[1]})",
                "original_to_point": f"({original_end[0]}, {original_end[1]})",
                "damage_location": f"{from_zone} to {to_zone}",
                "bbox_from": f"({int(x)}, {int(y)})",
                "bbox_to": f"({int(x + w)}, {int(y + h)})",
                "area": round(area, 1),
                "type": "linear crack" if aspect >= 2.5 else "surface distress",
            }
        )

    detections = sorted(detections, key=lambda item: item["area"], reverse=True)[:25]
    for index, detection in enumerate(detections, start=1):
        detection["id"] = f"D{index}"
        color = (35, 90, 245) if detection["type"] == "linear crack" else (0, 170, 255)
        x = detection["x"]
        y = detection["y"]
        w = detection["width"]
        h = detection["height"]
        start_point = (detection["x_start"], detection["y_start"])
        end_point = (detection["x_end"], detection["y_end"])
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        cv2.line(annotated, start_point, end_point, color, 2)
        cv2.circle(annotated, start_point, 4, (15, 220, 70), -1)
        cv2.circle(annotated, end_point, 4, (15, 70, 240), -1)
        cv2.putText(
            annotated,
            detection["id"],
            (x, max(18, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    area_ratio = damaged_pixels / max(gray.shape[0] * gray.shape[1], 1)
    score = min(100, int(area_ratio * 1200 + len(detections) * 3.2))
    severity = _severity(score)

    annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
    output = Image.fromarray(annotated_rgb)
    buffer = io.BytesIO()
    output.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return {
        "score": score,
        "severity": severity,
        "damage_area_percent": round(area_ratio * 100, 2),
        "detections": detections,
        "damage_locations": [
            f"{item['id']}: {item['damage_location']} ({item['from_point']} to {item['to_point']})"
            for item in detections
        ],
        "detection_count": len(detections),
        "original_width": original_width,
        "original_height": original_height,
        "processed_width": processed_width,
        "processed_height": processed_height,
        "annotated_image": f"data:image/png;base64,{encoded}",
        "recommendation": _recommendation(score),
        "model": "OpenCV baseline detector",
        "location_note": "Damage locations are image coordinates. Add road segment start/end in the frontend for street-level reporting.",
    }


def _severity(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 35:
        return "Moderate"
    return "Low"


def _damage_endpoints(contour: np.ndarray, x: int, y: int, w: int, h: int) -> tuple[tuple[int, int], tuple[int, int]]:
    points = contour.reshape(-1, 2)
    if len(points) == 0:
        return (int(x), int(y)), (int(x + w), int(y + h))
    if w >= h:
        start = points[np.argmin(points[:, 0])]
        end = points[np.argmax(points[:, 0])]
    else:
        start = points[np.argmin(points[:, 1])]
        end = points[np.argmax(points[:, 1])]
    return (int(start[0]), int(start[1])), (int(end[0]), int(end[1]))


def _scale_point(
    point: tuple[int, int],
    processed_width: int,
    processed_height: int,
    original_width: int,
    original_height: int,
) -> tuple[int, int]:
    scale_x = original_width / max(processed_width, 1)
    scale_y = original_height / max(processed_height, 1)
    return int(round(point[0] * scale_x)), int(round(point[1] * scale_y))


def _human_zone(point: tuple[int, int], width: int, height: int) -> str:
    x, y = point
    horizontal = "left" if x < width / 3 else "right" if x > (width * 2) / 3 else "middle"
    vertical = "upper" if y < height / 3 else "lower" if y > (height * 2) / 3 else "middle"
    return f"{vertical}-{horizontal}"


def _recommendation(score: int) -> str:
    if score >= 70:
        return "Dispatch inspection crew and flag lane for urgent maintenance review."
    if score >= 35:
        return "Schedule field validation and add the segment to the maintenance queue."
    return "Low visible distress. Keep monitoring through periodic surveys."
