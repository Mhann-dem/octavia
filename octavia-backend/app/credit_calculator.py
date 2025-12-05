"""Credit cost calculator for media processing jobs."""
import json
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CreditCalculator:
    """Calculate credit costs for different job types."""
    
    # Credit costs per minute (or per job for non-duration jobs)
    CREDIT_COSTS = {
        "transcribe": 10,      # 10 credits per minute of audio
        "translate": 5,         # 5 credits per translation job
        "synthesize": 15,       # 15 credits per minute of audio
        "video_translate": 30,  # 30 credits per minute of video
    }
    
    @staticmethod
    def get_audio_duration(audio_file_path: str) -> Optional[float]:
        """
        Get duration of audio file in seconds.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Duration in seconds or None if unable to determine
        """
        try:
            import ffmpeg
            
            probe = ffmpeg.probe(str(audio_file_path))
            duration = float(probe['format'].get('duration', 0))
            return duration
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {str(e)}")
            return None
    
    @staticmethod
    def get_video_duration(video_file_path: str) -> Optional[float]:
        """
        Get duration of video file in seconds.
        
        Args:
            video_file_path: Path to video file
            
        Returns:
            Duration in seconds or None if unable to determine
        """
        try:
            import ffmpeg
            
            probe = ffmpeg.probe(str(video_file_path))
            duration = float(probe['format'].get('duration', 0))
            return duration
        except Exception as e:
            logger.warning(f"Could not determine video duration: {str(e)}")
            return None
    
    @staticmethod
    def get_text_length(json_file_path: str) -> int:
        """
        Get length of transcribed/translated text from JSON file.
        
        Args:
            json_file_path: Path to JSON file containing text data
            
        Returns:
            Number of characters or 0 if unable to determine
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Try common field names
                text = data.get('text') or data.get('translated_text') or data.get('original_text') or ""
                return len(text)
        except Exception as e:
            logger.warning(f"Could not determine text length: {str(e)}")
            return 0
    
    @classmethod
    def calculate_credits(
        cls,
        job_type: str,
        input_file_path: Optional[str] = None,
        translation_file_path: Optional[str] = None,
        duration_override: Optional[float] = None,
    ) -> int:
        """
        Calculate credit cost for a job.
        
        Args:
            job_type: Type of job ('transcribe', 'translate', 'synthesize', 'video_translate')
            input_file_path: Path to input file (for duration calculation)
            translation_file_path: Path to translation file (for synthesis)
            duration_override: Override duration calculation with explicit value
            
        Returns:
            Credit cost (integer)
        """
        base_cost = cls.CREDIT_COSTS.get(job_type, 0)
        
        if base_cost == 0:
            logger.warning(f"Unknown job type: {job_type}")
            return 0
        
        # Jobs that charge per minute
        if job_type in ("transcribe", "synthesize", "video_translate"):
            # Get duration
            duration = duration_override
            
            if duration is None and input_file_path:
                if job_type == "video_translate":
                    duration = cls.get_video_duration(input_file_path)
                else:
                    duration = cls.get_audio_duration(input_file_path)
            
            if duration is None:
                logger.warning(f"Could not determine duration for {job_type}, using default 1 minute")
                duration = 60  # Default to 1 minute
            
            # Convert to minutes and calculate cost
            minutes = duration / 60
            cost = max(1, int(base_cost * minutes))  # Minimum 1 credit
            
            logger.info(f"Calculated {job_type} cost: {cost} credits ({minutes:.2f} minutes × {base_cost} credits/min)")
            return cost
        
        # Jobs with flat rate
        else:  # translate
            logger.info(f"Calculated {job_type} cost: {base_cost} credits")
            return base_cost
    
    @classmethod
    def estimate_credits(
        cls,
        job_type: str,
        duration_seconds: float,
    ) -> int:
        """
        Estimate credit cost based on duration.
        
        Args:
            job_type: Type of job
            duration_seconds: Duration in seconds
            
        Returns:
            Estimated credit cost
        """
        return cls.calculate_credits(
            job_type=job_type,
            duration_override=duration_seconds
        )


def get_credit_calculator() -> CreditCalculator:
    """Get CreditCalculator instance."""
    return CreditCalculator()
