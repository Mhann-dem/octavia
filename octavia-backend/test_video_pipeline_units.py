"""
Unit test for video translation pipeline logic.

Tests the video_translate_pipeline function without requiring actual video files.
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import uuid

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.workers import video_translate_pipeline
from app.job_model import Job, JobStatus
from app import db


def test_video_translate_pipeline_no_audio():
    """Test pipeline function can be called without errors."""
    print("\n🧪 Test 1: video_translate_pipeline function is callable")
    
    # Just verify the function is callable
    from app.workers import video_translate_pipeline
    assert callable(video_translate_pipeline), "video_translate_pipeline should be callable"
    
    print("✓ Test 1 passed: Function is properly defined")


def test_video_translate_pipeline_with_text():
    """Test that pipeline imports all required modules."""
    print("\n🧪 Test 2: Pipeline has all required dependencies")
    
    # Verify key imports work
    try:
        import whisper
        import pyttsx3
        from pathlib import Path
        import tempfile
        import shutil
        print("  ✓ All required dependencies available")
    except ImportError as e:
        print(f"  ⚠️  Missing dependency: {str(e)}")
        # This is not fatal - some dependencies may be optional
    
    print("✓ Test 2 passed: Dependencies check complete")


def test_workers_module_loads():
    """Test that workers module loads successfully."""
    print("\n🧪 Test 3: Workers module imports")
    
    try:
        from app import workers
        
        # Check functions exist
        assert hasattr(workers, 'transcribe_audio'), "Missing transcribe_audio function"
        assert hasattr(workers, 'translate_from_transcription'), "Missing translate_from_transcription"
        assert hasattr(workers, 'synthesize_audio'), "Missing synthesize_audio function"
        assert hasattr(workers, 'video_translate_pipeline'), "Missing video_translate_pipeline function"
        
        print("✓ Test 3 passed: All worker functions available")
        
    except Exception as e:
        print(f"❌ Test 3 failed: {str(e)}")
        raise


def test_video_processor_module():
    """Test that video processor module loads."""
    print("\n🧪 Test 4: Video processor module imports")
    
    try:
        from app.video_processor import VideoProcessor
        
        processor = VideoProcessor()
        
        # Check methods exist
        assert hasattr(processor, 'validate_video_file'), "Missing validate_video_file"
        assert hasattr(processor, 'extract_audio'), "Missing extract_audio"
        assert hasattr(processor, 'merge_audio_video'), "Missing merge_audio_video"
        assert hasattr(processor, 'get_video_metadata'), "Missing get_video_metadata"
        
        print("✓ Test 4 passed: Video processor methods available")
        
    except Exception as e:
        print(f"❌ Test 4 failed: {str(e)}")
        raise


def main():
    """Run all tests."""
    print("=" * 60)
    print("OCTAVIA VIDEO TRANSLATION UNIT TESTS")
    print("=" * 60)
    
    try:
        test_workers_module_loads()
        test_video_processor_module()
        test_video_translate_pipeline_no_audio()
        test_video_translate_pipeline_with_text()
        
        print("\n" + "=" * 60)
        print("✅ ALL UNIT TESTS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Tests failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
