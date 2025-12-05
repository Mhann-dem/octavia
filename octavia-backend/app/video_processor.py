"""
Video processing module for Octavia.
Handles video upload, audio extraction, and video reassembly.
"""
import logging
import ffmpeg
from pathlib import Path
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles all video processing operations using FFmpeg."""
    
    def __init__(self):
        """Initialize the video processor."""
        self.supported_formats = [
            '.mp4', '.avi', '.mov', '.mkv', '.flv', 
            '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'
        ]
    
    def validate_video_file(self, file_path: str) -> bool:
        """
        Validate that the file is a supported video format.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            bool: True if valid video file
        """
        try:
            path = Path(file_path)
            
            # Check file exists
            if not path.exists():
                logger.error(f"Video file not found: {file_path}")
                return False
            
            # Check extension
            if path.suffix.lower() not in self.supported_formats:
                logger.error(f"Unsupported video format: {path.suffix}")
                return False
            
            # Try to probe the file with ffmpeg
            probe = ffmpeg.probe(str(path))
            
            # Check if file has video stream
            video_streams = [s for s in probe['streams'] if s['codec_type'] == 'video']
            if not video_streams:
                logger.error(f"No video stream found in file: {file_path}")
                return False
            
            logger.info(f"Video file validated: {file_path}")
            return True
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error validating video: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Error validating video file: {str(e)}")
            return False
    
    def get_video_metadata(self, file_path: str) -> Optional[Dict]:
        """
        Extract metadata from video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dict with video metadata or None if failed
        """
        try:
            probe = ffmpeg.probe(str(file_path))
            
            video_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'),
                None
            )
            audio_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'audio'),
                None
            )
            
            if not video_stream:
                return None
            
            metadata = {
                'duration': float(probe['format'].get('duration', 0)),
                'size_bytes': int(probe['format'].get('size', 0)),
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                'bitrate': int(probe['format'].get('bit_rate', 0)),
                'has_audio': audio_stream is not None,
            }
            
            if audio_stream:
                metadata['audio_codec'] = audio_stream.get('codec_name', 'unknown')
                metadata['audio_channels'] = int(audio_stream.get('channels', 0))
                metadata['audio_sample_rate'] = int(audio_stream.get('sample_rate', 0))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting video metadata: {str(e)}")
            return None
    
    def extract_audio(
        self, 
        video_path: str, 
        output_audio_path: Optional[str] = None,
        audio_format: str = 'wav',
        sample_rate: int = 16000
    ) -> Optional[str]:
        """
        Extract audio track from video file.
        
        Args:
            video_path: Path to input video file
            output_audio_path: Path for output audio file (auto-generated if None)
            audio_format: Output audio format ('wav', 'mp3', 'flac')
            sample_rate: Audio sample rate in Hz (16000 for Whisper)
            
        Returns:
            Path to extracted audio file or None if failed
        """
        try:
            video_path = Path(video_path)
            
            # Auto-generate output path if not provided
            if output_audio_path is None:
                output_audio_path = video_path.parent / f"{video_path.stem}_audio.{audio_format}"
            else:
                output_audio_path = Path(output_audio_path)
            
            logger.info(f"Extracting audio from {video_path} to {output_audio_path}")
            
            # Extract audio with ffmpeg
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream.audio,
                str(output_audio_path),
                acodec='pcm_s16le' if audio_format == 'wav' else audio_format,
                ac=1,  # Mono
                ar=sample_rate,
                loglevel='error'
            )
            
            # Overwrite output file if it exists
            stream = ffmpeg.overwrite_output(stream)
            
            # Run the command
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            if not output_audio_path.exists():
                logger.error(f"Audio extraction failed: output file not created")
                return None
            
            logger.info(f"Audio extracted successfully: {output_audio_path} ({output_audio_path.stat().st_size} bytes)")
            return str(output_audio_path)
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error during audio extraction: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            return None
    
    def merge_audio_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: Optional[str] = None,
        video_codec: str = 'copy',
        audio_codec: str = 'aac'
    ) -> Optional[str]:
        """
        Merge new audio track with original video.
        
        Args:
            video_path: Path to original video file
            audio_path: Path to new audio file
            output_path: Path for output video (auto-generated if None)
            video_codec: Video codec ('copy' to avoid re-encoding)
            audio_codec: Audio codec ('aac' recommended)
            
        Returns:
            Path to merged video file or None if failed
        """
        try:
            video_path = Path(video_path)
            audio_path = Path(audio_path)
            
            # Auto-generate output path if not provided
            if output_path is None:
                output_path = video_path.parent / f"{video_path.stem}_dubbed{video_path.suffix}"
            else:
                output_path = Path(output_path)
            
            logger.info(f"Merging audio {audio_path} with video {video_path}")
            
            # Create ffmpeg streams
            video_stream = ffmpeg.input(str(video_path)).video
            audio_stream = ffmpeg.input(str(audio_path)).audio
            
            # Merge streams
            stream = ffmpeg.output(
                video_stream,
                audio_stream,
                str(output_path),
                vcodec=video_codec,
                acodec=audio_codec,
                shortest=None,  # Use shortest stream duration
                loglevel='error'
            )
            
            # Overwrite output file if it exists
            stream = ffmpeg.overwrite_output(stream)
            
            # Run the command
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            if not output_path.exists():
                logger.error(f"Video merge failed: output file not created")
                return None
            
            logger.info(f"Video merged successfully: {output_path} ({output_path.stat().st_size} bytes)")
            return str(output_path)
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error during video merge: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"Error merging video: {str(e)}")
            return None
    
    def get_video_duration(self, file_path: str) -> Optional[float]:
        """
        Get duration of video file in seconds.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Duration in seconds or None if failed
        """
        try:
            probe = ffmpeg.probe(str(file_path))
            duration = float(probe['format'].get('duration', 0))
            return duration
        except Exception as e:
            logger.error(f"Error getting video duration: {str(e)}")
            return None


# Convenience functions for use in workers.py
def extract_audio_from_video(video_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Extract audio from video file.
    Convenience wrapper for VideoProcessor.extract_audio()
    
    Args:
        video_path: Path to video file
        output_path: Optional output path for audio file
        
    Returns:
        Path to extracted audio file or None if failed
    """
    processor = VideoProcessor()
    return processor.extract_audio(video_path, output_path)


def merge_dubbed_audio(video_path: str, audio_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Merge dubbed audio with original video.
    Convenience wrapper for VideoProcessor.merge_audio_video()
    
    Args:
        video_path: Path to original video
        audio_path: Path to dubbed audio
        output_path: Optional output path for merged video
        
    Returns:
        Path to merged video or None if failed
    """
    processor = VideoProcessor()
    return processor.merge_audio_video(video_path, audio_path, output_path)


def validate_video(file_path: str) -> bool:
    """
    Validate video file.
    Convenience wrapper for VideoProcessor.validate_video_file()
    
    Args:
        file_path: Path to video file
        
    Returns:
        True if valid video file
    """
    processor = VideoProcessor()
    return processor.validate_video_file(file_path)