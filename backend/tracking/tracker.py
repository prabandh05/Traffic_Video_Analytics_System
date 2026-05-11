"""
Vehicle Tracker — manages per-vehicle track state.

This module sits between the detector and the line counter.
It maintains a history of positions for each tracked vehicle,
which is essential for determining line crossings (we need
the previous position to detect when a vehicle crosses the line).

Design decisions:
- Uses deque with maxlen to bound memory (we only need recent positions)
- Tracks are marked as "counted" once they cross the line (prevents double counting)
- Stale tracks are cleaned up automatically
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum position history per track (avoids memory buildup)
MAX_POSITION_HISTORY = 30

# Frames after which a lost track is removed
STALE_TRACK_FRAMES = 60


@dataclass
class TrackInfo:
    """State for a single tracked vehicle."""

    track_id: int
    class_id: int
    class_name: str
    positions: deque = field(default_factory=lambda: deque(maxlen=MAX_POSITION_HISTORY))
    counted: bool = False
    last_seen_frame: int = 0
    crossing_timestamp: Optional[float] = None
    confidence_sum: float = 0.0
    detection_count: int = 0

    @property
    def avg_confidence(self) -> float:
        """Average detection confidence across all sightings."""
        if self.detection_count == 0:
            return 0.0
        return self.confidence_sum / self.detection_count

    @property
    def last_position(self) -> Optional[tuple]:
        """Most recent center position."""
        if self.positions:
            return self.positions[-1]
        return None

    @property
    def prev_position(self) -> Optional[tuple]:
        """Second most recent center position (needed for line crossing)."""
        if len(self.positions) >= 2:
            return self.positions[-2]
        return None


class VehicleTracker:
    """
    Manages tracking state for all vehicles across frames.

    This does NOT perform the actual tracking (ByteTrack does that inside
    the detector). This class maintains per-vehicle state that the
    line crossing logic needs.

    Usage:
        tracker = VehicleTracker()
        
        for frame_num, detections in enumerate(all_detections):
            tracker.update(detections, frame_num)
            active = tracker.get_active_tracks()
            # check line crossings for each active track...
    """

    def __init__(self):
        self.tracks: dict[int, TrackInfo] = {}
        self.total_tracks_seen = 0

    def update(self, detections: list[dict], frame_number: int):
        """
        Update track state with new detections from the current frame.

        Args:
            detections: List of detection dicts from VehicleDetector.detect_and_track()
            frame_number: Current frame number (for stale track cleanup)
        """
        seen_ids = set()

        for det in detections:
            track_id = det["track_id"]
            center = det["center"]
            class_id = det["class_id"]
            class_name = det["class_name"]
            confidence = det["confidence"]

            seen_ids.add(track_id)

            if track_id not in self.tracks:
                # New track
                self.tracks[track_id] = TrackInfo(
                    track_id=track_id,
                    class_id=class_id,
                    class_name=class_name,
                )
                self.total_tracks_seen += 1
                logger.debug(f"New track: ID={track_id}, class={class_name}")

            track = self.tracks[track_id]
            track.positions.append(center)
            track.last_seen_frame = frame_number
            track.confidence_sum += confidence
            track.detection_count += 1

        # Clean up stale tracks (not seen for too long)
        self._cleanup_stale_tracks(frame_number)

    def _cleanup_stale_tracks(self, current_frame: int):
        """Remove tracks that haven't been seen for STALE_TRACK_FRAMES."""
        stale_ids = [
            tid
            for tid, track in self.tracks.items()
            if (current_frame - track.last_seen_frame) > STALE_TRACK_FRAMES
            and track.counted  # Only remove if already counted (or very stale)
        ]

        # For uncounted stale tracks, keep them a bit longer
        very_stale_ids = [
            tid
            for tid, track in self.tracks.items()
            if (current_frame - track.last_seen_frame) > STALE_TRACK_FRAMES * 3
            and not track.counted
        ]

        for tid in stale_ids + very_stale_ids:
            del self.tracks[tid]

    def get_active_tracks(self) -> list[TrackInfo]:
        """Return all currently active (non-stale) tracks."""
        return list(self.tracks.values())

    def get_uncounted_tracks(self) -> list[TrackInfo]:
        """Return tracks that haven't crossed the counting line yet."""
        return [t for t in self.tracks.values() if not t.counted]

    def mark_counted(self, track_id: int, timestamp: float = 0.0):
        """Mark a track as having crossed the counting line."""
        if track_id in self.tracks:
            self.tracks[track_id].counted = True
            self.tracks[track_id].crossing_timestamp = timestamp
            logger.debug(f"Track {track_id} marked as counted at t={timestamp:.2f}s")

    def get_track(self, track_id: int) -> Optional[TrackInfo]:
        """Get a specific track by ID."""
        return self.tracks.get(track_id)

    def reset(self):
        """Reset all tracking state. Call between videos."""
        self.tracks.clear()
        self.total_tracks_seen = 0
        logger.info("Tracker state reset")

    def get_stats(self) -> dict:
        """Return tracker statistics."""
        counted = sum(1 for t in self.tracks.values() if t.counted)
        return {
            "active_tracks": len(self.tracks),
            "total_tracks_seen": self.total_tracks_seen,
            "counted_tracks": counted,
            "uncounted_tracks": len(self.tracks) - counted,
        }
