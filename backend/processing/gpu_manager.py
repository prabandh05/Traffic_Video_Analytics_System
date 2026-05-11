"""
GPU Manager — detects GPU capabilities and allocates workers accordingly.

Rules:
- Detect available GPU via torch.cuda
- Allocate parallel video workers based on VRAM
- Fall back to CPU gracefully
- Do NOT load separate YOLO models per worker (VRAM killer)

VRAM-based allocation:
    4 GB  → 1 worker
    8 GB  → 2 workers
    16 GB → 4 workers
    No GPU → 1 worker (CPU)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def detect_gpu() -> Optional[dict]:
    """
    Detect available GPU and return info.

    Returns:
        Dict with GPU info or None if no GPU available.
        {
            "name": "NVIDIA GeForce RTX 3060",
            "vram_total_mb": 12288,
            "vram_free_mb": 10240,
            "cuda_version": "11.8",
            "device_count": 1,
        }
    """
    try:
        import torch

        if not torch.cuda.is_available():
            logger.info("CUDA not available — will use CPU")
            return None

        device_count = torch.cuda.device_count()
        device = torch.cuda.get_device_properties(0)

        vram_total_mb = device.total_mem // (1024 * 1024)

        # Get free memory
        vram_free_mb = 0
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            vram_free_mb = free_bytes // (1024 * 1024)
        except Exception:
            vram_free_mb = vram_total_mb  # Assume all free if can't query

        info = {
            "name": device.name,
            "vram_total_mb": vram_total_mb,
            "vram_free_mb": vram_free_mb,
            "cuda_version": torch.version.cuda or "unknown",
            "device_count": device_count,
        }

        logger.info(f"GPU detected: {info['name']} ({vram_total_mb}MB VRAM)")
        return info

    except ImportError:
        logger.info("PyTorch not installed — will use CPU")
        return None
    except Exception as e:
        logger.warning(f"GPU detection failed: {e}")
        return None


def get_optimal_workers(gpu_info: Optional[dict] = None) -> int:
    """
    Determine optimal number of parallel video workers.

    Based on available VRAM:
        < 4 GB   → 1 worker
        4-8 GB   → 1 worker
        8-16 GB  → 2 workers
        16+ GB   → 4 workers
        No GPU   → 1 worker (CPU mode)

    Args:
        gpu_info: GPU info dict from detect_gpu(). If None, detects automatically.

    Returns:
        Number of workers to use for parallel processing.
    """
    if gpu_info is None:
        gpu_info = detect_gpu()

    if gpu_info is None:
        logger.info("No GPU — using 1 CPU worker")
        return 1

    vram_mb = gpu_info.get("vram_total_mb", 0)

    if vram_mb >= 16384:  # 16 GB+
        workers = 4
    elif vram_mb >= 8192:  # 8 GB+
        workers = 2
    else:  # < 8 GB
        workers = 1

    logger.info(f"Optimal workers: {workers} (based on {vram_mb}MB VRAM)")
    return workers


def get_device_string() -> str:
    """
    Get the device string for PyTorch/YOLO.

    Returns:
        "cuda" if GPU available, "cpu" otherwise.
    """
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass

    return "cpu"


def get_system_info() -> dict:
    """Get complete system info for the API."""
    gpu_info = detect_gpu()
    workers = get_optimal_workers(gpu_info)
    device = get_device_string()

    return {
        "gpu": gpu_info,
        "optimal_workers": workers,
        "device": device,
        "has_gpu": gpu_info is not None,
    }
