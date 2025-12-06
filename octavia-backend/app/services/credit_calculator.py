"""Credit calculation utilities for job pricing."""
import os
from typing import Optional


# Credit costs per minute by job type
CREDIT_COSTS = {
    "transcribe": int(os.environ.get("CREDIT_COST_TRANSCRIBE", "10")),      # 10 credits/min
    "translate": int(os.environ.get("CREDIT_COST_TRANSLATE", "5")),         # 5 credits/min
    "synthesize": int(os.environ.get("CREDIT_COST_SYNTHESIZE", "8")),       # 8 credits/min
    "video_translate": int(os.environ.get("CREDIT_COST_VIDEO_TRANSLATE", "15")),  # 15 credits/min
}


def estimate_credits(
    job_type: str,
    duration_minutes: int,
) -> int:
    """
    Estimate the number of credits needed for a job.
    
    Args:
        job_type: Type of job ('transcribe', 'translate', 'synthesize', 'video_translate')
        duration_minutes: Duration of media in minutes
        
    Returns:
        Estimated credits needed (minimum 1)
    """
    if job_type not in CREDIT_COSTS:
        return 1
    
    cost_per_minute = CREDIT_COSTS[job_type]
    estimated = int(duration_minutes * cost_per_minute)
    
    # Minimum 1 credit
    return max(1, estimated)


def get_duration_from_file(file_path: str) -> Optional[int]:
    """
    Get duration of audio/video file in seconds.
    
    This is a placeholder - in production, use ffprobe or similar.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Duration in seconds, or None if unable to determine
    """
    # Placeholder: return None to indicate we can't determine
    # In production, use: ffmpeg -i file.mp3 2>&1 | grep Duration
    return None
