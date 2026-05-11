"""
Line Crossing Counter — the TRUE core logic of the system.

This module determines when a tracked vehicle crosses the user-defined
counting line. It uses vector cross-product geometry to detect when a
vehicle's centroid moves from one side of the line to the other.

The counting guarantee:
- Each track_id is counted AT MOST once
- A vehicle must physically cross the line (not just appear near it)
- Direction of crossing is tracked (can filter by direction if needed)

Math explanation:
Given line segment AB and point P, the cross product of (AB × AP)
determines which side of the line P is on:
    cross > 0 → left side
    cross < 0 → right side
    cross = 0 → on the line

When the sign changes between consecutive frames, a crossing occurred.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LineCrossingCounter:
    """
    Counts vehicles crossing a user-defined line.

    Usage:
        counter = LineCrossingCounter(line_start=(100, 300), line_end=(800, 300))

        # For each frame:
        for track in active_tracks:
            if counter.check_crossing(track.track_id, track.prev_position, track.last_position):
                # Vehicle crossed! It's automatically counted.
                pass

        # Get results:
        print(counter.counts)  # {"Two Wheeler": 5, "Four Wheeler": 12, ...}
    """

    def __init__(self, line_start: tuple, line_end: tuple):
        """
        Initialize with the counting line coordinates.

        Args:
            line_start: (x, y) tuple for line start point
            line_end: (x, y) tuple for line end point
        """
        self.line_start = line_start
        self.line_end = line_end
        self.counted_ids: set[int] = set()
        self.counts: dict[str, int] = {
            "Two Wheeler": 0,
            "Four Wheeler": 0,
            "Commercial": 0,
            "Auto": 0,
            "Unknown": 0,
        }
        self.crossing_log: list[dict] = []  # Detailed crossing records

        logger.info(
            f"Line counter initialized: ({line_start}) -> ({line_end})"
        )

    def _cross_product_sign(self, point: tuple) -> float:
        """
        Compute the cross product sign to determine which side of the line a point is on.

        Returns:
            Positive if point is on the left side,
            Negative if on the right side,
            Zero if on the line.
        """
        # Vector from line_start to line_end
        dx_line = self.line_end[0] - self.line_start[0]
        dy_line = self.line_end[1] - self.line_start[1]

        # Vector from line_start to point
        dx_point = point[0] - self.line_start[0]
        dy_point = point[1] - self.line_start[1]

        # Cross product
        return dx_line * dy_point - dy_line * dx_point

    def check_crossing(
        self,
        track_id: int,
        prev_center: Optional[tuple],
        curr_center: Optional[tuple],
        vehicle_category: str = "Unknown",
        timestamp: float = 0.0,
    ) -> bool:
        """
        Check if a vehicle's centroid crossed the counting line.

        Args:
            track_id: Unique tracking ID for this vehicle.
            prev_center: Previous frame's center position (x, y).
            curr_center: Current frame's center position (x, y).
            vehicle_category: Classified vehicle type.
            timestamp: Video timestamp in seconds.

        Returns:
            True if the vehicle just crossed the line (first time).
        """
        # Already counted this track — skip
        if track_id in self.counted_ids:
            return False

        # Need both positions to detect crossing
        if prev_center is None or curr_center is None:
            return False

        # Check which side of line each position is on
        prev_sign = self._cross_product_sign(prev_center)
        curr_sign = self._cross_product_sign(curr_center)

        # Crossing occurs when sign changes (point moved from one side to the other)
        # We also check that neither sign is zero (avoid counting vehicles sitting on the line)
        if prev_sign * curr_sign < 0:
            # Crossing detected!
            self.counted_ids.add(track_id)
            self.counts[vehicle_category] = self.counts.get(vehicle_category, 0) + 1

            # Log the crossing
            crossing_record = {
                "track_id": track_id,
                "vehicle_type": vehicle_category,
                "timestamp": timestamp,
                "position": curr_center,
                "direction": "forward" if curr_sign > 0 else "backward",
            }
            self.crossing_log.append(crossing_record)

            logger.info(
                f"CROSSING: Track {track_id} ({vehicle_category}) at t={timestamp:.2f}s"
            )
            return True

        return False

    def get_total_count(self) -> int:
        """Total vehicles counted across all categories."""
        return sum(self.counts.values())

    def get_counts(self) -> dict[str, int]:
        """Get counts by vehicle category."""
        return self.counts.copy()

    def get_crossing_log(self) -> list[dict]:
        """Get detailed log of all crossings."""
        return self.crossing_log.copy()

    def reset(self):
        """Reset all counts. Call between videos."""
        self.counted_ids.clear()
        for key in self.counts:
            self.counts[key] = 0
        self.crossing_log.clear()
        logger.info("Line counter reset")
