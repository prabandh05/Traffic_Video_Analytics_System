"""
Vehicle Detector using YOLOv8m with built-in ByteTrack tracking.

This is the core detection module. It loads a single YOLOv8m model instance
and provides detection + tracking in a single call via ultralytics' built-in
ByteTrack integration.

Key design decisions:
- YOLOv8m (not nano) for better accuracy on traffic scenarios
- Model loaded ONCE and reused across all frames
- Only vehicle COCO classes are retained (car, motorcycle, bus, truck, bicycle)
- ByteTrack tracking is integrated via model.track() — no separate library needed
"""

import os
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# COCO class IDs for vehicles
VEHICLE_CLASS_IDS = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# Project root for model storage
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
BYTETRACK_CONFIG = Path(__file__).parent / "bytetrack.yaml"


class VehicleDetector:
    """
    Detects and tracks vehicles in video frames using YOLOv8m + ByteTrack.
    
    Usage:
        detector = VehicleDetector()
        detections = detector.detect_and_track(frame)
        # detections = [{"track_id": 1, "bbox": [x1,y1,x2,y2], "class_id": 2, "class_name": "car", "confidence": 0.87}, ...]
    """

    def __init__(
        self,
        model_name: str = "yolov8m.pt",
        confidence_threshold: float = 0.4,
        device: Optional[str] = None,
    ):
        """
        Initialize the vehicle detector.

        Args:
            model_name: YOLO model file name. Downloads automatically if not present.
            confidence_threshold: Minimum confidence for detections (0.0-1.0).
            device: Device to run on ('cuda', 'cpu', or None for auto-detect).
        """
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model = None
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        """Load YOLOv8m model. Downloads if not cached."""
        try:
            from ultralytics import YOLO

            # Ensure models directory exists
            MODELS_DIR.mkdir(parents=True, exist_ok=True)

            model_path = MODELS_DIR / self.model_name

            # If model exists locally, load from there; otherwise ultralytics downloads it
            if model_path.exists():
                self.model = YOLO(str(model_path))
                logger.info(f"Loaded model from {model_path}")
            else:
                self.model = YOLO(self.model_name)
                logger.info(f"Loaded model {self.model_name} (will download if needed)")

            # Set device
            if self.device:
                logger.info(f"Using device: {self.device}")

            logger.info("Vehicle detector initialized successfully")

        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise RuntimeError(f"Cannot initialize vehicle detector: {e}")

    def detect_and_track(self, frame: np.ndarray, persist: bool = True) -> list[dict]:
        """
        Run detection + tracking on a single frame.

        Uses model.track() which combines YOLOv8 detection with ByteTrack
        in a single call. The 'persist' flag maintains track IDs across frames.

        Args:
            frame: BGR image as numpy array (from OpenCV).
            persist: If True, maintains tracking state across calls.

        Returns:
            List of detection dicts:
            [
                {
                    "track_id": int,        # Unique track ID (from ByteTrack)
                    "bbox": [x1, y1, x2, y2],  # Bounding box coordinates
                    "center": (cx, cy),     # Center point of bbox
                    "class_id": int,        # COCO class ID
                    "class_name": str,      # Human-readable class name
                    "confidence": float,    # Detection confidence
                },
                ...
            ]
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        # Run tracking with ByteTrack
        tracker_config = str(BYTETRACK_CONFIG) if BYTETRACK_CONFIG.exists() else "bytetrack.yaml"

        results = self.model.track(
            source=frame,
            persist=persist,
            tracker=tracker_config,
            conf=self.confidence_threshold,
            classes=list(VEHICLE_CLASS_IDS.keys()),  # Filter to vehicles only
            device=self.device,
            verbose=False,
        )

        detections = []

        if results and len(results) > 0:
            result = results[0]

            if result.boxes is not None and result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                track_ids = result.boxes.id.cpu().numpy().astype(int)
                class_ids = result.boxes.cls.cpu().numpy().astype(int)
                confidences = result.boxes.conf.cpu().numpy()

                for bbox, track_id, class_id, conf in zip(
                    boxes, track_ids, class_ids, confidences
                ):
                    x1, y1, x2, y2 = bbox
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2

                    detections.append(
                        {
                            "track_id": int(track_id),
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "center": (float(cx), float(cy)),
                            "class_id": int(class_id),
                            "class_name": VEHICLE_CLASS_IDS.get(
                                int(class_id), "unknown"
                            ),
                            "confidence": float(conf),
                        }
                    )

        return detections

    def detect_only(self, frame: np.ndarray) -> list[dict]:
        """
        Run detection WITHOUT tracking (for single-frame analysis).

        Args:
            frame: BGR image as numpy array.

        Returns:
            List of detection dicts (without track_id).
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        results = self.model(
            frame,
            conf=self.confidence_threshold,
            classes=list(VEHICLE_CLASS_IDS.keys()),
            device=self.device,
            verbose=False,
        )

        detections = []

        if results and len(results) > 0:
            result = results[0]

            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy().astype(int)
                confidences = result.boxes.conf.cpu().numpy()

                for bbox, class_id, conf in zip(boxes, class_ids, confidences):
                    x1, y1, x2, y2 = bbox
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2

                    detections.append(
                        {
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "center": (float(cx), float(cy)),
                            "class_id": int(class_id),
                            "class_name": VEHICLE_CLASS_IDS.get(
                                int(class_id), "unknown"
                            ),
                            "confidence": float(conf),
                        }
                    )

        return detections

    def reset_tracker(self):
        """Reset ByteTrack state. Call between different videos."""
        if self.model is not None:
            self.model.predictor = None
            logger.info("Tracker state reset")

    def get_model_info(self) -> dict:
        """Return model metadata."""
        return {
            "model_name": self.model_name,
            "confidence_threshold": self.confidence_threshold,
            "device": self.device or "auto",
            "vehicle_classes": VEHICLE_CLASS_IDS,
        }
