"""
Line Drawing Utility — lets user define counting line on the first frame.

Provides both:
1. OpenCV-based interactive drawing (for CLI/local use)
2. Frame extraction for web-based drawing (for React frontend)
"""

import logging
import cv2
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_first_frame(video_path: str) -> np.ndarray:
    """
    Extract the first frame of a video for line drawing.

    Args:
        video_path: Path to the video file.

    Returns:
        First frame as BGR numpy array.

    Raises:
        FileNotFoundError: If video file doesn't exist.
        RuntimeError: If video can't be opened or read.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError(f"Cannot read first frame from: {video_path}")

    logger.info(f"Extracted first frame: {frame.shape[1]}x{frame.shape[0]}")
    return frame


def frame_to_jpeg_bytes(frame: np.ndarray, quality: int = 85) -> bytes:
    """
    Encode a frame as JPEG bytes (for API response).

    Args:
        frame: BGR numpy array.
        quality: JPEG quality (0-100).

    Returns:
        JPEG encoded bytes.
    """
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode(".jpg", frame, encode_params)
    return buffer.tobytes()


def draw_line_interactive(video_path: str) -> tuple:
    """
    Open first frame in OpenCV window, let user click two points.

    This is the CLI/local version. For web UI, use extract_first_frame()
    and handle line drawing in the React frontend.

    Args:
        video_path: Path to the video file.

    Returns:
        Tuple of ((x1, y1), (x2, y2)) representing the counting line.
    """
    frame = extract_first_frame(video_path)
    points = []
    drawing_frame = frame.copy()

    def mouse_callback(event, x, y, flags, param):
        nonlocal drawing_frame
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            points.append((x, y))
            cv2.circle(drawing_frame, (x, y), 5, (0, 255, 0), -1)

            if len(points) == 2:
                cv2.line(
                    drawing_frame, points[0], points[1], (0, 0, 255), 2
                )
                cv2.putText(
                    drawing_frame,
                    "Press ENTER to confirm, R to reset",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            cv2.imshow("Draw Counting Line", drawing_frame)

    cv2.namedWindow("Draw Counting Line", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("Draw Counting Line", mouse_callback)

    cv2.putText(
        drawing_frame,
        "Click TWO points to define counting line",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2,
    )
    cv2.imshow("Draw Counting Line", drawing_frame)

    while True:
        key = cv2.waitKey(1) & 0xFF

        if key == 13 and len(points) == 2:  # Enter
            break
        elif key == ord("r"):  # Reset
            points.clear()
            drawing_frame = frame.copy()
            cv2.putText(
                drawing_frame,
                "Click TWO points to define counting line",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            cv2.imshow("Draw Counting Line", drawing_frame)
        elif key == 27:  # ESC
            cv2.destroyAllWindows()
            raise RuntimeError("Line drawing cancelled by user")

    cv2.destroyAllWindows()
    logger.info(f"Counting line defined: {points[0]} -> {points[1]}")
    return (points[0], points[1])


def get_video_info(video_path: str) -> dict:
    """Get video metadata (dimensions, fps, frame count, duration)."""
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration_seconds": 0.0,
    }
    if info["fps"] > 0:
        info["duration_seconds"] = info["total_frames"] / info["fps"]

    cap.release()
    return info
