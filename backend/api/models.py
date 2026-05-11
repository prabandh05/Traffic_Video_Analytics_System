"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LineCoordinates(BaseModel):
    """Counting line coordinates from frontend."""
    x1: float = Field(..., description="Line start X")
    y1: float = Field(..., description="Line start Y")
    x2: float = Field(..., description="Line end X")
    y2: float = Field(..., description="Line end Y")


class VideoUploadResponse(BaseModel):
    """Response after uploading a video."""
    job_id: str
    video_name: str
    status: str
    message: str


class VideoStatusResponse(BaseModel):
    """Status of a single video job."""
    job_id: str
    video_name: str
    status: str
    line_start: Optional[list] = None
    line_end: Optional[list] = None
    result: Optional[dict] = None
    excel_path: Optional[str] = None
    csv_path: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_frames: int = 0
    total_frames: int = 0


class ProcessRequest(BaseModel):
    """Request to start video processing (line must be set first)."""
    frame_skip: int = Field(default=1, ge=1, le=10, description="Process every Nth frame")


class SystemInfoResponse(BaseModel):
    """System GPU and worker information."""
    gpu: Optional[dict] = None
    optimal_workers: int
    device: str
    has_gpu: bool


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True
