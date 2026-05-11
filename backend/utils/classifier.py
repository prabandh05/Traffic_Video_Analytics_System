"""
Vehicle Classifier — maps YOLO COCO class IDs to traffic categories.

IMPORTANT NOTE ON AUTO-RICKSHAWS:
Standard YOLO COCO models do NOT detect Indian auto-rickshaws.
For now, unrecognized vehicles default to "Unknown".
Phase 6 will add custom fine-tuning for auto-rickshaw detection.
"""

import logging

logger = logging.getLogger(__name__)

# COCO class ID → traffic category mapping
CATEGORY_MAP: dict[int, str] = {
    1: "Two Wheeler",   # bicycle
    3: "Two Wheeler",   # motorcycle
    2: "Four Wheeler",  # car
    5: "Commercial",    # bus
    7: "Commercial",    # truck
}

CATEGORY_CLASSES: dict[str, list[str]] = {
    "Two Wheeler": ["bicycle", "motorcycle"],
    "Four Wheeler": ["car"],
    "Commercial": ["bus", "truck"],
    "Auto": [],  # No COCO class — requires custom model (Phase 6)
}


def classify_vehicle(class_id: int, class_name: str = "") -> str:
    """Map a YOLO COCO class ID to a traffic vehicle category."""
    category = CATEGORY_MAP.get(class_id, "Unknown")
    if category == "Unknown" and class_name:
        logger.debug(f"Unrecognized vehicle class: id={class_id}, name={class_name}")
    return category


def get_all_categories() -> list[str]:
    """Return all possible vehicle categories."""
    return ["Two Wheeler", "Four Wheeler", "Commercial", "Auto", "Unknown"]


def get_category_description() -> dict[str, list[str]]:
    """Return what COCO classes map to each category."""
    return CATEGORY_CLASSES.copy()
