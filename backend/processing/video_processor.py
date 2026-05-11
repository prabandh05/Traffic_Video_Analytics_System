"""
Video Processor — the main pipeline orchestrator.

This is the backbone of the system. It ties together:
    Frame Reader → Detection → Tracking → Line Crossing → Counting

Pipeline per frame:
    1. Read frame from video (OpenCV)
    2. Run model.track() → detections with track IDs (YOLO + ByteTrack)
    3. Update tracker state (position history)
    4. Classify each detected vehicle
    5. Check line crossings for all active tracks
    6. Accumulate counts

Design decisions:
    - Processes frames sequentially (tracking requires temporal ordering)
    - Optional frame skipping for speed (process every Nth frame)
    - Progress callback for status updates
    - No frame storage — only counts and crossing logs are kept
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import cv2

from backend.detection.detector import VehicleDetector
from backend.tracking.tracker import VehicleTracker
from backend.processing.line_counter import LineCrossingCounter
from backend.utils.classifier import classify_vehicle

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Results from processing a single video."""

    video_path: str
    video_name: str
    counts: dict[str, int] = field(default_factory=dict)
    crossing_log: list[dict] = field(default_factory=list)
    total_frames: int = 0
    processed_frames: int = 0
    processing_time: float = 0.0
    fps_processing: float = 0.0
    video_duration: float = 0.0
    video_fps: float = 0.0
    video_width: int = 0
    video_height: int = 0
    line_coords: tuple = ()
    error: Optional[str] = None
    success: bool = True


class VideoProcessor:
    """
    Orchestrates the complete video processing pipeline.

    Usage:
        detector = VehicleDetector()
        processor = VideoProcessor(detector)

        result = processor.process_video(
            video_path="road1.mp4",
            line_start=(100, 300),
            line_end=(800, 300),
        )

        print(result.counts)
        # {"Two Wheeler": 12, "Four Wheeler": 45, "Commercial": 3, ...}
    """

    def __init__(
        self,
        detector: VehicleDetector,
        frame_skip: int = 1,
    ):
        """
        Initialize the video processor.

        Args:
            detector: Shared VehicleDetector instance (reuse across videos).
            frame_skip: Process every Nth frame (1 = all frames, 2 = every other, etc.)
        """
        self.detector = detector
        self.frame_skip = max(1, frame_skip)

    def process_video(
        self,
        video_path: str,
        line_start: tuple,
        line_end: tuple,
        progress_callback: Optional[Callable[[int, int, dict], None]] = None,
    ) -> ProcessingResult:
        """
        Process a single video through the complete pipeline.

        Args:
            video_path: Path to the video file.
            line_start: (x, y) start of counting line.
            line_end: (x, y) end of counting line.
            progress_callback: Optional function(current_frame, total_frames, counts)
                               called periodically to report progress.

        Returns:
            ProcessingResult with counts, timing, and metadata.
        """
        video_path = str(Path(video_path).resolve())
        video_name = Path(video_path).name

        result = ProcessingResult(
            video_path=video_path,
            video_name=video_name,
            line_coords=(line_start, line_end),
        )

        logger.info(f"Starting processing: {video_name}")
        logger.info(f"Counting line: {line_start} -> {line_end}")
        logger.info(f"Frame skip: {self.frame_skip}")

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            result.error = f"Cannot open video: {video_path}"
            result.success = False
            logger.error(result.error)
            return result

        # Video metadata
        result.video_fps = cap.get(cv2.CAP_PROP_FPS)
        result.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        result.video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        result.video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if result.video_fps > 0:
            result.video_duration = result.total_frames / result.video_fps

        logger.info(
            f"Video: {result.video_width}x{result.video_height}, "
            f"{result.video_fps:.1f}fps, {result.total_frames} frames, "
            f"{result.video_duration:.1f}s"
        )

        # Initialize tracking and counting
        tracker = VehicleTracker()
        counter = LineCrossingCounter(line_start, line_end)

        # Reset detector tracking state (fresh tracking for new video)
        self.detector.reset_tracker()

        start_time = time.time()
        frame_number = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_number += 1

                # Frame skipping for performance
                if frame_number % self.frame_skip != 0:
                    continue

                result.processed_frames += 1

                # Calculate video timestamp
                timestamp = frame_number / result.video_fps if result.video_fps > 0 else 0.0

                # Step 1: Detect + Track (single YOLO call with ByteTrack)
                detections = self.detector.detect_and_track(frame)

                # Step 2: Update tracker state
                tracker.update(detections, frame_number)

                # Step 3: Check line crossings for all active tracks
                for track in tracker.get_uncounted_tracks():
                    if track.prev_position is not None and track.last_position is not None:
                        # Classify the vehicle
                        category = classify_vehicle(track.class_id, track.class_name)

                        # Check if this track crossed the line
                        crossed = counter.check_crossing(
                            track_id=track.track_id,
                            prev_center=track.prev_position,
                            curr_center=track.last_position,
                            vehicle_category=category,
                            timestamp=timestamp,
                        )

                        if crossed:
                            tracker.mark_counted(track.track_id, timestamp)

                # Progress callback (every 100 frames)
                if progress_callback and frame_number % 100 == 0:
                    progress_callback(
                        frame_number, result.total_frames, counter.get_counts()
                    )

        except Exception as e:
            result.error = f"Error processing frame {frame_number}: {str(e)}"
            result.success = False
            logger.error(result.error, exc_info=True)

        finally:
            cap.release()

        # Finalize results
        result.processing_time = time.time() - start_time
        result.counts = counter.get_counts()
        result.crossing_log = counter.get_crossing_log()

        if result.processing_time > 0:
            result.fps_processing = result.processed_frames / result.processing_time

        tracker_stats = tracker.get_stats()

        logger.info(f"Processing complete: {video_name}")
        logger.info(f"  Time: {result.processing_time:.1f}s")
        logger.info(f"  Processing FPS: {result.fps_processing:.1f}")
        logger.info(f"  Frames processed: {result.processed_frames}/{result.total_frames}")
        logger.info(f"  Total tracks seen: {tracker_stats['total_tracks_seen']}")
        logger.info(f"  Vehicles counted: {counter.get_total_count()}")
        logger.info(f"  Counts: {result.counts}")

        return result
