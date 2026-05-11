"""
API Routes — FastAPI endpoints for the Traffic Video Analytics System.

Endpoints:
    POST   /api/videos/upload         — Upload a video file
    POST   /api/videos/{id}/line      — Set counting line coordinates
    POST   /api/videos/{id}/process   — Start processing
    GET    /api/videos                — List all videos with status
    GET    /api/videos/{id}           — Get single video status + results
    GET    /api/videos/{id}/frame     — Get first frame as JPEG (for line drawing)
    GET    /api/videos/{id}/export/excel — Download Excel report
    GET    /api/videos/{id}/export/csv   — Download CSV report
    DELETE /api/videos/{id}           — Remove video and files
    GET    /api/system/info           — GPU info + worker capacity
"""

import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response

from backend.api.models import (
    LineCoordinates,
    VideoUploadResponse,
    MessageResponse,
)
from backend.processing.batch_processor import BatchProcessor
from backend.processing.gpu_manager import get_system_info
from backend.utils.line_drawer import extract_first_frame, frame_to_jpeg_bytes, get_video_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Traffic Analytics"])

# Singleton batch processor — initialized in main.py lifespan
_batch_processor: BatchProcessor | None = None


def get_processor() -> BatchProcessor:
    """Get the batch processor instance."""
    if _batch_processor is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    return _batch_processor


def set_processor(processor: BatchProcessor):
    """Set the batch processor instance (called from main.py)."""
    global _batch_processor
    _batch_processor = processor


# ── Video Upload ──

@router.post("/videos/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """Upload a traffic video for processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    allowed = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Allowed: {', '.join(allowed)}"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    processor = get_processor()
    job_id = processor.add_video_from_upload(file.filename, content)

    return VideoUploadResponse(
        job_id=job_id,
        video_name=file.filename,
        status="Pending",
        message=f"Video uploaded successfully. Set counting line next.",
    )


# ── Line Drawing ──

@router.get("/videos/{job_id}/frame")
async def get_first_frame(job_id: str):
    """Get the first frame of a video as JPEG for line drawing in the UI."""
    processor = get_processor()

    try:
        status = processor.get_status(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    video_path = status.get("video_name", "")
    # Get actual file path from the job
    with processor._lock:
        job = processor._jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        video_path = job.video_path

    try:
        frame = extract_first_frame(video_path)
        jpeg_bytes = frame_to_jpeg_bytes(frame)
        return Response(content=jpeg_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot extract frame: {str(e)}")


@router.post("/videos/{job_id}/line", response_model=MessageResponse)
async def set_counting_line(job_id: str, coords: LineCoordinates):
    """Set the counting line coordinates for a video."""
    processor = get_processor()

    try:
        processor.set_line(
            job_id,
            line_start=(coords.x1, coords.y1),
            line_end=(coords.x2, coords.y2),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MessageResponse(
        message=f"Counting line set: ({coords.x1},{coords.y1}) -> ({coords.x2},{coords.y2})"
    )


# ── Processing ──

@router.post("/videos/{job_id}/process", response_model=MessageResponse)
async def start_processing(job_id: str):
    """Start processing a video (requires line to be set first)."""
    processor = get_processor()

    try:
        processor.start_processing(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MessageResponse(message=f"Processing started for job {job_id}")


# ── Status ──

@router.get("/videos")
async def list_videos():
    """List all videos with their current status."""
    processor = get_processor()
    return {"videos": processor.get_all_jobs()}


@router.get("/videos/{job_id}")
async def get_video_status(job_id: str):
    """Get detailed status of a single video job."""
    processor = get_processor()

    try:
        return processor.get_status(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


# ── Export ──

@router.get("/videos/{job_id}/export/excel")
async def download_excel(job_id: str):
    """Download the Excel report for a completed video."""
    processor = get_processor()

    try:
        status = processor.get_status(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")

    if status["status"] != "Completed":
        raise HTTPException(status_code=400, detail="Video not yet processed")

    excel_path = status.get("excel_path")
    if not excel_path or not Path(excel_path).exists():
        raise HTTPException(status_code=404, detail="Excel file not found")

    return FileResponse(
        path=excel_path,
        filename=Path(excel_path).name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/videos/{job_id}/export/csv")
async def download_csv(job_id: str):
    """Download the CSV report for a completed video."""
    processor = get_processor()

    try:
        status = processor.get_status(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")

    if status["status"] != "Completed":
        raise HTTPException(status_code=400, detail="Video not yet processed")

    csv_path = status.get("csv_path")
    if not csv_path or not Path(csv_path).exists():
        raise HTTPException(status_code=404, detail="CSV file not found")

    return FileResponse(
        path=csv_path,
        filename=Path(csv_path).name,
        media_type="text/csv",
    )


# ── Video Info ──

@router.get("/videos/{job_id}/info")
async def get_video_metadata(job_id: str):
    """Get video metadata (dimensions, fps, duration)."""
    processor = get_processor()

    with processor._lock:
        job = processor._jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        video_path = job.video_path

    try:
        info = get_video_info(video_path)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Delete ──

@router.delete("/videos/{job_id}", response_model=MessageResponse)
async def delete_video(job_id: str):
    """Delete a video job and its files."""
    processor = get_processor()

    try:
        processor.delete_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MessageResponse(message=f"Job {job_id} deleted")


# ── System ──

@router.get("/system/info")
async def system_info():
    """Get system GPU info and worker capacity."""
    return get_system_info()
