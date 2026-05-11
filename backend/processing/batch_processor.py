"""
Batch Processor — manages queue of videos for parallel processing.

Status flow per video:
    Pending → Processing → Completed
                         → Failed

Design:
- Uses concurrent.futures for parallel processing
- Single shared detector instance (avoids model duplication)
- Dynamic worker count from GPU manager
- Thread-safe status tracking
"""

import logging
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

from backend.detection.detector import VehicleDetector
from backend.processing.video_processor import VideoProcessor, ProcessingResult
from backend.processing.gpu_manager import get_optimal_workers, get_device_string
from backend.exports.excel_exporter import export_to_excel, export_to_csv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
VIDEOS_DIR = PROJECT_ROOT / "videos"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


class VideoStatus(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass
class VideoJob:
    """Represents a single video processing job."""
    job_id: str
    video_name: str
    video_path: str
    status: VideoStatus = VideoStatus.PENDING
    line_start: Optional[tuple] = None
    line_end: Optional[tuple] = None
    result: Optional[ProcessingResult] = None
    excel_path: Optional[str] = None
    csv_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_frames: int = 0
    total_frames: int = 0

    def to_dict(self) -> dict:
        """Convert to API-friendly dict."""
        result_dict = None
        if self.result:
            result_dict = {
                "counts": self.result.counts,
                "total_count": sum(self.result.counts.values()),
                "processing_time": round(self.result.processing_time, 2),
                "fps_processing": round(self.result.fps_processing, 1),
                "processed_frames": self.result.processed_frames,
                "total_frames": self.result.total_frames,
            }

        return {
            "job_id": self.job_id,
            "video_name": self.video_name,
            "status": self.status.value,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "result": result_dict,
            "excel_path": self.excel_path,
            "csv_path": self.csv_path,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress_frames": self.progress_frames,
            "total_frames": self.total_frames,
        }


class BatchProcessor:
    """
    Manages a queue of video processing jobs with parallel execution.

    Usage:
        processor = BatchProcessor()
        job_id = processor.add_video("road1.mp4")
        processor.set_line(job_id, (100, 300), (800, 300))
        processor.start_processing(job_id)
        status = processor.get_status(job_id)
    """

    def __init__(self, max_workers: Optional[int] = None):
        self._lock = threading.Lock()
        self._jobs: dict[str, VideoJob] = {}
        self._futures: dict[str, Future] = {}

        # Determine worker count
        self._max_workers = max_workers or get_optimal_workers()

        # Shared detector (loaded once, reused)
        self._detector: Optional[VehicleDetector] = None
        self._detector_lock = threading.Lock()

        # Thread pool
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="video_worker",
        )

        # Ensure directories exist
        for subdir in ["pending", "processing", "completed"]:
            (VIDEOS_DIR / subdir).mkdir(parents=True, exist_ok=True)
        (OUTPUTS_DIR / "excel").mkdir(parents=True, exist_ok=True)
        (OUTPUTS_DIR / "snapshots").mkdir(parents=True, exist_ok=True)

        logger.info(f"BatchProcessor initialized with {self._max_workers} workers")

    def _get_detector(self) -> VehicleDetector:
        """Lazy-load and return the shared detector instance."""
        with self._detector_lock:
            if self._detector is None:
                device = get_device_string()
                logger.info(f"Loading YOLOv8m model on {device}...")
                self._detector = VehicleDetector(device=device)
                logger.info("Model loaded successfully")
            return self._detector

    def add_video(self, video_path: str, video_name: Optional[str] = None) -> str:
        """
        Add a video to the processing queue.

        Args:
            video_path: Path to the video file.
            video_name: Optional display name.

        Returns:
            Job ID string.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        job_id = str(uuid.uuid4())[:8]
        name = video_name or path.name

        # Copy to pending directory
        pending_path = VIDEOS_DIR / "pending" / f"{job_id}_{path.name}"
        shutil.copy2(str(path), str(pending_path))

        job = VideoJob(
            job_id=job_id,
            video_name=name,
            video_path=str(pending_path),
        )

        with self._lock:
            self._jobs[job_id] = job

        logger.info(f"Video added: {name} (job_id={job_id})")
        return job_id

    def add_video_from_upload(self, filename: str, file_bytes: bytes) -> str:
        """
        Add a video from an uploaded file.

        Args:
            filename: Original filename.
            file_bytes: File content as bytes.

        Returns:
            Job ID string.
        """
        job_id = str(uuid.uuid4())[:8]
        pending_path = VIDEOS_DIR / "pending" / f"{job_id}_{filename}"
        pending_path.parent.mkdir(parents=True, exist_ok=True)

        with open(str(pending_path), "wb") as f:
            f.write(file_bytes)

        job = VideoJob(
            job_id=job_id,
            video_name=filename,
            video_path=str(pending_path),
        )

        with self._lock:
            self._jobs[job_id] = job

        logger.info(f"Video uploaded: {filename} (job_id={job_id})")
        return job_id

    def set_line(self, job_id: str, line_start: tuple, line_end: tuple):
        """Set counting line coordinates for a job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            job.line_start = line_start
            job.line_end = line_end
            logger.info(f"Line set for {job_id}: {line_start} -> {line_end}")

    def start_processing(self, job_id: str):
        """Start processing a video (async)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            if job.status != VideoStatus.PENDING:
                raise ValueError(f"Job {job_id} is {job.status.value}, expected Pending")
            if job.line_start is None or job.line_end is None:
                raise ValueError(f"Counting line not set for job {job_id}")

        future = self._executor.submit(self._process_job, job_id)
        self._futures[job_id] = future

    def _process_job(self, job_id: str):
        """Process a single video job (runs in thread pool)."""
        with self._lock:
            job = self._jobs[job_id]
            job.status = VideoStatus.PROCESSING
            job.started_at = datetime.now().isoformat()

        # Move to processing directory
        proc_path = VIDEOS_DIR / "processing" / Path(job.video_path).name
        try:
            shutil.move(job.video_path, str(proc_path))
            job.video_path = str(proc_path)
        except Exception:
            pass  # Keep original path if move fails

        try:
            detector = self._get_detector()

            # Create a fresh processor for this video
            processor = VideoProcessor(detector=detector, frame_skip=1)

            def progress_cb(current, total, counts):
                with self._lock:
                    job.progress_frames = current
                    job.total_frames = total

            result = processor.process_video(
                video_path=job.video_path,
                line_start=job.line_start,
                line_end=job.line_end,
                progress_callback=progress_cb,
            )

            if not result.success:
                raise RuntimeError(result.error or "Processing failed")

            # Export results
            video_metadata = {
                "video_name": job.video_name,
                "duration": f"{result.video_duration:.1f}s",
                "resolution": f"{result.video_width}x{result.video_height}",
                "fps": f"{result.video_fps:.1f}",
                "frames_processed": f"{result.processed_frames}/{result.total_frames}",
                "processing_time": f"{result.processing_time:.1f}s",
            }

            excel_path = export_to_excel(
                counts=result.counts,
                video_name=job.video_name,
                crossing_log=result.crossing_log,
                video_metadata=video_metadata,
            )

            csv_path = export_to_csv(
                counts=result.counts,
                video_name=job.video_name,
            )

            # Move video to completed
            comp_path = VIDEOS_DIR / "completed" / Path(job.video_path).name
            try:
                shutil.move(job.video_path, str(comp_path))
                job.video_path = str(comp_path)
            except Exception:
                pass

            with self._lock:
                job.result = result
                job.excel_path = excel_path
                job.csv_path = csv_path
                job.status = VideoStatus.COMPLETED
                job.completed_at = datetime.now().isoformat()
                job.progress_frames = result.total_frames
                job.total_frames = result.total_frames

            logger.info(f"Job {job_id} completed: {sum(result.counts.values())} vehicles counted")

        except Exception as e:
            with self._lock:
                job.status = VideoStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.now().isoformat()
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)

    def get_status(self, job_id: str) -> dict:
        """Get status of a single job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            return job.to_dict()

    def get_all_jobs(self) -> list[dict]:
        """Get status of all jobs."""
        with self._lock:
            return [job.to_dict() for job in self._jobs.values()]

    def delete_job(self, job_id: str):
        """Delete a job and its files."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
            if job.status == VideoStatus.PROCESSING:
                raise ValueError("Cannot delete a job that is currently processing")

            # Clean up files
            for path_str in [job.video_path, job.excel_path, job.csv_path]:
                if path_str:
                    p = Path(path_str)
                    if p.exists():
                        p.unlink()

            del self._jobs[job_id]
        logger.info(f"Job {job_id} deleted")

    def shutdown(self):
        """Shut down the thread pool."""
        self._executor.shutdown(wait=False)
        logger.info("BatchProcessor shut down")
