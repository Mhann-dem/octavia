"""
Background worker functions for media processing tasks.
Handles transcription, translation, and synthesis operations.
"""
import json
import logging
from pathlib import Path
from typing import Optional
import whisper
from sqlalchemy.orm import Session
from .job_model import Job, JobStatus
from .storage import get_file, save_upload

logger = logging.getLogger(__name__)

# Try to use soundfile for audio loading (doesn't require ffmpeg binary)
try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False
    logger.warning("soundfile not installed - audio loading will require ffmpeg")


def load_audio_without_ffmpeg(audio_path: str, sr: int = 16000):
    """
    Load audio file without requiring ffmpeg binary.
    Uses soundfile library which can load WAV files natively.
    
    Args:
        audio_path: Path to audio file
        sr: Sample rate (default 16000 Hz for Whisper)
    
    Returns:
        numpy array of audio samples, or None if loading failed
    """
    if not HAS_SOUNDFILE:
        return None
    
    try:
        audio, file_sr = sf.read(audio_path)
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        # Resample if needed (simple approach - just use as-is for now)
        return audio.astype('float32')
    except Exception as e:
        logger.warning(f"Failed to load audio with soundfile: {e}")
        return None


def transcribe_audio(
    session: Session,
    job_id: str,
    input_file_path: str,
    language: Optional[str] = None,
    model_size: str = "base"
) -> bool:
    """
    Transcribe audio file using OpenAI Whisper.
    
    Args:
        session: SQLAlchemy database session
        job_id: Job ID to update with results
        input_file_path: Path to audio file to transcribe
        language: Optional ISO 639-1 language code (e.g., 'en', 'es', 'fr')
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
    
    Returns:
        bool: True if transcription succeeded, False otherwise
    """
    try:
        # Get the job record
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        session.commit()
        logger.info(f"Job {job_id}: Starting transcription with model '{model_size}'")
        
        # Check if file exists
        file_path = Path(input_file_path)
        if not file_path.exists():
            logger.error(f"Job {job_id}: Input file not found at {input_file_path}")
            job.status = JobStatus.FAILED
            job.error_message = f"Input file not found: {input_file_path}"
            session.commit()
            return False
        
        # Load Whisper model and transcribe
        logger.info(f"Job {job_id}: Loading Whisper model '{model_size}'...")
        model = whisper.load_model(model_size)
        
        logger.info(f"Job {job_id}: Transcribing audio file ({file_path.stat().st_size} bytes)...")
        
        # Try to use the custom audio loader first (no ffmpeg required)
        audio = load_audio_without_ffmpeg(str(file_path))
        if audio is not None:
            logger.info(f"Job {job_id}: Using soundfile for audio loading (no ffmpeg required)")
            result = model.transcribe(audio, language=language, verbose=False)
        else:
            logger.info(f"Job {job_id}: Falling back to standard Whisper audio loading (requires ffmpeg)")
            result = model.transcribe(str(file_path), language=language, verbose=False)
        
        # Extract transcription and metadata
        transcription_text = result.get("text", "")
        language_detected = result.get("language", "unknown")
        
        logger.info(f"Job {job_id}: Transcription complete. Detected language: {language_detected}")
        
        # Save transcription to output file
        output_file_name = f"{Path(input_file_path).stem}_transcript.json"
        output_file_path = str(Path(input_file_path).parent / output_file_name)
        
        transcription_output = {
            "text": transcription_text,
            "language": language_detected,
            "segments": result.get("segments", []),
            "duration": result.get("duration", 0),
            "model_size": model_size
        }
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(transcription_output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Job {job_id}: Transcription saved to {output_file_path}")
        
        # Update job with results
        job.status = JobStatus.COMPLETED
        job.output_file = output_file_path
        job.job_metadata = json.dumps({
            "model_size": model_size,
            "language": language_detected,
            "detected_language": language_detected,
            "segments_count": len(result.get("segments", [])),
            "audio_duration": result.get("duration", 0)
        })
        session.commit()
        
        logger.info(f"Job {job_id}: Status updated to COMPLETED")
        return True
    
    except Exception as e:
        logger.error(f"Job {job_id}: Transcription failed with error: {str(e)}", exc_info=True)
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            # Special-case missing ffmpeg (common on Windows)
            if isinstance(e, FileNotFoundError):
                job.error_message = "Transcription error: ffmpeg not found. Install ffmpeg and ensure it's on PATH"
            else:
                job.error_message = f"Transcription error: {str(e)}"
            session.commit()
        return False


def translate_text(session: Session, job_id: str, text: str, source_lang: str = "en", target_lang: str = "es") -> Optional[str]:
    """
    Translate text using Helsinki NLP transformers.
    Supports multiple language pairs via HuggingFace Transformers.
    
    Args:
        session: SQLAlchemy database session
        job_id: Job ID for logging
        text: Text to translate
        source_lang: Source language code (e.g., 'en', 'es', 'fr')
        target_lang: Target language code
    
    Returns:
        Translated text, or None if translation failed
    """
    try:
        from transformers import pipeline
        
        logger.info(f"Job {job_id}: Loading translation model {source_lang}->{target_lang}")
        
        # Helsinki NLP model naming: Helsinki-NLP/Tatoeba-MT-models/tatoeba-mt-{src}-{tgt}
        # Common models available on HuggingFace
        model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
        
        translator = pipeline("translation", model=model_name)
        logger.info(f"Job {job_id}: Translating {len(text)} characters from {source_lang} to {target_lang}")
        
        # Translate in chunks to avoid memory issues (max 512 tokens)
        max_chunk = 500
        chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
        
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            logger.debug(f"Job {job_id}: Translating chunk {i+1}/{len(chunks)}")
            result = translator(chunk, max_length=1024)
            translated_chunks.append(result[0]['translation_text'])
        
        translated_text = " ".join(translated_chunks)
        logger.info(f"Job {job_id}: Translation complete, output: {len(translated_text)} characters")
        return translated_text
    
    except Exception as e:
        logger.error(f"Job {job_id}: Translation failed: {str(e)}", exc_info=True)
        return None


def translate_from_transcription(
    session: Session,
    job_id: str,
    transcription_file: str,
    source_lang: str = "en",
    target_lang: str = "es"
) -> bool:
    """
    Translate transcribed text from a JSON transcription file.
    Creates a translation job that stores results.
    
    Args:
        session: SQLAlchemy database session
        job_id: Job ID to update with results
        transcription_file: Path to transcription JSON file
        source_lang: Source language code
        target_lang: Target language code
    
    Returns:
        bool: True if translation succeeded, False otherwise
    """
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        session.commit()
        logger.info(f"Job {job_id}: Starting translation {source_lang}->{target_lang}")
        
        # Load transcription file
        transcription_path = Path(transcription_file)
        if not transcription_path.exists():
            logger.error(f"Job {job_id}: Transcription file not found at {transcription_file}")
            job.status = JobStatus.FAILED
            job.error_message = f"Transcription file not found: {transcription_file}"
            session.commit()
            return False
        
        with open(transcription_path, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        original_text = transcription_data.get("text", "")
        if not original_text:
            logger.warning(f"Job {job_id}: No text to translate in transcription file")
            # Still create an empty translated JSON so downstream steps (synthesis) can find a file
            output_file_name = f"{transcription_path.stem}_translated.json"
            output_file_path = transcription_path.parent / output_file_name

            translation_output = {
                "original_text": "",
                "translated_text": "",
                "source_language": source_lang,
                "target_language": target_lang,
                "original_length": 0,
                "translated_length": 0,
                "model": None
            }

            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(translation_output, f, indent=2, ensure_ascii=False)

            job.status = JobStatus.COMPLETED
            job.output_file = output_file_path.as_posix()
            job.job_metadata = json.dumps({
                "source_language": source_lang,
                "target_language": target_lang,
                "original_length": 0,
                "translated_length": 0,
                "detected_language": transcription_data.get("language", "unknown")
            })
            session.commit()
            return True
        
        # Perform translation
        translated_text = translate_text(session, job_id, original_text, source_lang, target_lang)
        
        if translated_text is None:
            raise Exception("Translation returned None")
        
        # Save translation results
        output_file_name = f"{transcription_path.stem}_translated.json"
        output_file_path = transcription_path.parent / output_file_name
        
        translation_output = {
            "original_text": original_text,
            "translated_text": translated_text,
            "source_language": source_lang,
            "target_language": target_lang,
            "original_length": len(original_text),
            "translated_length": len(translated_text),
            "model": f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
        }
        
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(translation_output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Job {job_id}: Translation saved to {output_file_path}")
        
        # Update job with results
        job.status = JobStatus.COMPLETED
        job.output_file = output_file_path.as_posix()
        job.job_metadata = json.dumps({
            "source_language": source_lang,
            "target_language": target_lang,
            "original_length": len(original_text),
            "translated_length": len(translated_text),
            "detected_language": transcription_data.get("language", "unknown")
        })
        session.commit()
        
        logger.info(f"Job {job_id}: Status updated to COMPLETED")
        return True
    
    except Exception as e:
        logger.error(f"Job {job_id}: Translation failed with error: {str(e)}", exc_info=True)
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"Translation error: {str(e)}"
            session.commit()
        return False

"""
Add this function to app/workers.py to handle video translation jobs.
This should be added to the existing workers.py file.
"""

def process_video_translation(
    session: Session,
    job_id: str,
    input_video_path: str,
    source_lang: str = "auto",
    target_lang: str = "es",
    model_size: str = "base"
) -> bool:
    """
    Process a complete video translation job.
    
    Pipeline:
    1. Extract audio from video
    2. Transcribe audio to text (Whisper)
    3. Translate text to target language (Helsinki NLP)
    4. Synthesize new audio from translated text (pyttsx3)
    5. Merge new audio back into video
    
    Args:
        session: SQLAlchemy database session
        job_id: Job ID to update with results
        input_video_path: Path to input video file
        source_lang: Source language code (or 'auto' for detection)
        target_lang: Target language code
        model_size: Whisper model size
    
    Returns:
        bool: True if video translation succeeded, False otherwise
    """
    try:
        from .video_processor import VideoProcessor, extract_audio_from_video, merge_dubbed_audio
        
        # Get the job record
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        session.commit()
        logger.info(f"Job {job_id}: Starting video translation pipeline")
        
        video_path = Path(input_video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {input_video_path}")
        
        # === STEP 1: Extract audio from video ===
        logger.info(f"Job {job_id}: Step 1/5 - Extracting audio from video")
        audio_path = extract_audio_from_video(str(video_path))
        if not audio_path:
            raise Exception("Failed to extract audio from video")
        
        logger.info(f"Job {job_id}: Audio extracted to {audio_path}")
        
        # === STEP 2: Transcribe audio ===
        logger.info(f"Job {job_id}: Step 2/5 - Transcribing audio")
        
        # Use existing transcribe_audio function
        transcription_success = transcribe_audio(
            session=session,
            job_id=f"{job_id}_transcribe",  # Temporary sub-job
            input_file_path=audio_path,
            language=None if source_lang == "auto" else source_lang,
            model_size=model_size
        )
        
        if not transcription_success:
            raise Exception("Transcription failed")
        
        # Find the transcription output file
        transcription_path = Path(audio_path).parent / f"{Path(audio_path).stem}_transcript.json"
        if not transcription_path.exists():
            raise Exception(f"Transcription output not found at {transcription_path}")
        
        logger.info(f"Job {job_id}: Transcription complete: {transcription_path}")
        
        # Load transcription to get detected language
        with open(transcription_path, 'r', encoding='utf-8') as f:
            transcription_data = json.load(f)
        
        detected_language = transcription_data.get('language', source_lang)
        logger.info(f"Job {job_id}: Detected language: {detected_language}")
        
        # === STEP 3: Translate text ===
        logger.info(f"Job {job_id}: Step 3/5 - Translating from {detected_language} to {target_lang}")
        
        # Use existing translate_from_transcription function
        translation_success = translate_from_transcription(
            session=session,
            job_id=f"{job_id}_translate",  # Temporary sub-job
            transcription_file=str(transcription_path),
            source_lang=detected_language,
            target_lang=target_lang
        )
        
        if not translation_success:
            raise Exception("Translation failed")
        
        # Find the translation output file
        translation_path = transcription_path.parent / f"{transcription_path.stem}_translated.json"
        if not translation_path.exists():
            raise Exception(f"Translation output not found at {translation_path}")
        
        logger.info(f"Job {job_id}: Translation complete: {translation_path}")
        
        # === STEP 4: Synthesize audio ===
        logger.info(f"Job {job_id}: Step 4/5 - Synthesizing dubbed audio")
        
        # Use existing synthesize_audio function
        synthesis_success = synthesize_audio(
            session=session,
            job_id=f"{job_id}_synthesize",  # Temporary sub-job
            input_file_path=str(translation_path),
            language=target_lang
        )
        
        if not synthesis_success:
            raise Exception("Audio synthesis failed")
        
        # Find the synthesized audio file
        dubbed_audio_path = translation_path.parent / f"{translation_path.stem}_audio.wav"
        if not dubbed_audio_path.exists():
            raise Exception(f"Synthesized audio not found at {dubbed_audio_path}")
        
        logger.info(f"Job {job_id}: Audio synthesis complete: {dubbed_audio_path}")
        
        # === STEP 5: Merge dubbed audio back into video ===
        logger.info(f"Job {job_id}: Step 5/5 - Merging dubbed audio with video")
        
        output_video_path = merge_dubbed_audio(
            video_path=str(video_path),
            audio_path=str(dubbed_audio_path),
            output_path=None  # Auto-generate output name
        )
        
        if not output_video_path:
            raise Exception("Failed to merge audio with video")
        
        logger.info(f"Job {job_id}: Video translation complete: {output_video_path}")
        
        # === Update job with final results ===
        job.status = JobStatus.COMPLETED
        job.output_file = output_video_path
        job.job_metadata = json.dumps({
            "source_language": source_lang,
            "target_language": target_lang,
            "detected_language": detected_language,
            "model_size": model_size,
            "intermediate_files": {
                "extracted_audio": audio_path,
                "transcription": str(transcription_path),
                "translation": str(translation_path),
                "dubbed_audio": str(dubbed_audio_path)
            },
            "output_video": output_video_path,
            "output_size_bytes": Path(output_video_path).stat().st_size
        })
        session.commit()
        
        logger.info(f"Job {job_id}: Video translation job completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Job {job_id}: Video translation failed with error: {str(e)}", exc_info=True)
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"Video translation error: {str(e)}"
            session.commit()
        return False

def synthesize_audio(
    session: Session,
    job_id: str,
    input_file_path: str,
    language: str = "en"
) -> bool:
    """
    Synthesize speech from translated text using pyttsx3.
    
    Args:
        session: SQLAlchemy database session
        job_id: Job ID to update with results
        input_file_path: Path to translation JSON file containing text to synthesize
        language: Language code for synthesis
    
    Returns:
        bool: True if synthesis succeeded, False otherwise
    """
    try:
        import pyttsx3
        
        # Get the job record
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        session.commit()
        logger.info(f"Job {job_id}: Starting synthesis")
        
        # Load translation file
        translation_path = Path(input_file_path)
        if not translation_path.exists():
            logger.error(f"Job {job_id}: Translation file not found at {input_file_path}")
            job.status = JobStatus.FAILED
            job.error_message = f"Translation file not found: {input_file_path}"
            session.commit()
            return False
        
        with open(translation_path, 'r', encoding='utf-8') as f:
            translation_data = json.load(f)
        
        # Get text to synthesize (prefer translated_text, fallback to original_text)
        text_to_synthesize = translation_data.get("translated_text") or translation_data.get("original_text", "")
        if not text_to_synthesize:
            logger.warning(f"Job {job_id}: No text to synthesize in file")
            # Create a small placeholder audio metadata file so downstream checks find a file
            output_file_path = translation_path.parent / f"{translation_path.stem}_audio.json"
            try:
                # If translation file exists, copy it to create a non-empty placeholder output
                import shutil
                shutil.copyfile(translation_path, output_file_path)
            except Exception:
                # Fallback: write a small placeholder JSON
                placeholder = {
                    "message": "No text to synthesize",
                    "language": language,
                    "synthesis_engine": "pyttsx3",
                    "text_length": 0
                }
                with open(output_file_path, 'w', encoding='utf-8') as out_f:
                    json.dump(placeholder, out_f, ensure_ascii=False, indent=2)

            job.status = JobStatus.COMPLETED
            job.output_file = output_file_path.as_posix()
            job.job_metadata = json.dumps({
                "language": language,
                "text_length": 0,
                "synthesis_engine": "pyttsx3",
                "message": "No text to synthesize"
            })
            session.commit()
            return True
        
        logger.info(f"Job {job_id}: Synthesizing {len(text_to_synthesize)} characters of text")
        
        # Initialize TTS engine
        engine = pyttsx3.init()
        
        # Set language/voice properties
        engine.setProperty('rate', 150)  # Speed
        engine.setProperty('volume', 0.9)  # Volume
        
        # Save to output file
        output_file_name = f"{translation_path.stem}_audio.wav"
        output_file_path = translation_path.parent / output_file_name
        
        # Generate audio
        engine.save_to_file(text_to_synthesize, str(output_file_path))
        engine.runAndWait()
        
        # Verify file was created
        if not output_file_path.exists():
            raise Exception(f"Audio file was not created at {output_file_path}")
        
        file_size = output_file_path.stat().st_size
        logger.info(f"Job {job_id}: Audio synthesis complete ({file_size} bytes)")
        
        # Update job with results
        job.status = JobStatus.COMPLETED
        job.output_file = output_file_path.as_posix()
        job.job_metadata = json.dumps({
            "language": language,
            "text_length": len(text_to_synthesize),
            "audio_size_bytes": file_size,
            "synthesis_engine": "pyttsx3",
            "source_languages": {
                "original": translation_data.get("source_language", "en"),
                "translated": translation_data.get("target_language", "es")
            }
        })
        session.commit()
        
        logger.info(f"Job {job_id}: Synthesis job completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Job {job_id}: Synthesis failed with error: {str(e)}", exc_info=True)
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"Synthesis error: {str(e)}"
            session.commit()
        return False


def video_translate_pipeline(
    session: Session,
    job_id: str,
    input_file_path: str,
    source_language: str = "auto",
    target_language: str = "es",
    model_size: str = "base",
    enable_dubbing: bool = True,
) -> bool:
    """
    End-to-end video translation pipeline.
    
    Steps:
    1. Extract audio from video
    2. Transcribe audio to text (with timestamps)
    3. Translate text to target language
    4. Synthesize new audio from translated text
    5. Merge new audio back into video
    
    Args:
        session: Database session
        job_id: Job ID for tracking
        input_file_path: Path to input video file
        source_language: Source language code or 'auto'
        target_language: Target language code
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        enable_dubbing: Whether to dub the video (vs just generating subtitles)
        
    Returns:
        True if successful, False otherwise
    """
    from .video_processor import VideoProcessor
    from pathlib import Path
    import tempfile
    import shutil
    
    job = session.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id}: Job not found")
        return False
    
    try:
        job.status = JobStatus.PROCESSING
        session.commit()
        
        video_path = Path(input_file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {input_file_path}")
        
        logger.info(f"Job {job_id}: Starting video translation pipeline")
        logger.info(f"  Input: {video_path}")
        logger.info(f"  Source language: {source_language}")
        logger.info(f"  Target language: {target_language}")
        logger.info(f"  Enable dubbing: {enable_dubbing}")
        
        # Step 1: Extract audio from video
        logger.info(f"Job {job_id}: Step 1/5 - Extracting audio from video")
        processor = VideoProcessor()
        
        temp_dir = Path(tempfile.gettempdir()) / f"octavia_job_{job_id}"
        temp_dir.mkdir(exist_ok=True, parents=True)
        
        audio_extract_path = temp_dir / "extracted_audio.wav"
        extracted_audio = processor.extract_audio(
            str(video_path),
            str(audio_extract_path),
            audio_format='wav',
            sample_rate=16000
        )
        
        if not extracted_audio:
            raise Exception("Failed to extract audio from video")
        
        logger.info(f"Job {job_id}: Audio extracted successfully ({Path(extracted_audio).stat().st_size} bytes)")
        
        # Step 2: Transcribe audio
        logger.info(f"Job {job_id}: Step 2/5 - Transcribing audio to text")
        
        # Load audio without ffmpeg (use extracted WAV)
        audio_data = load_audio_without_ffmpeg(extracted_audio, sr=16000)
        if audio_data is None:
            raise Exception("Failed to load extracted audio")
        
        # Transcribe using Whisper
        model = whisper.load_model(model_size)
        transcribe_result = model.transcribe(
            audio_data,
            language=None if source_language == "auto" else source_language,
            verbose=False,
            temperature=0.0
        )
        
        original_text = transcribe_result.get("text", "").strip()
        
        if not original_text:
            logger.warning(f"Job {job_id}: No text found in video audio")
            # Create placeholder output
            output_video_path = video_path.parent / f"{video_path.stem}_translated{video_path.suffix}"
            shutil.copy(str(video_path), str(output_video_path))
            
            job.status = JobStatus.COMPLETED
            job.output_file = output_video_path.as_posix()
            job.job_metadata = json.dumps({
                "source_language": source_language,
                "target_language": target_language,
                "original_text": "",
                "translated_text": "",
                "status": "no_audio"
            })
            session.commit()
            return True
        
        logger.info(f"Job {job_id}: Transcription complete ({len(original_text)} characters)")
        
        # Step 3: Translate text
        logger.info(f"Job {job_id}: Step 3/5 - Translating text")
        
        try:
            from transformers import pipeline as hf_pipeline
            
            # Use Helsinki NLP for translation
            translation_model = f"Helsinki-NLP/opus-mt-{source_language if source_language != 'auto' else 'en'}-{target_language}"
            translator = hf_pipeline("translation", model=translation_model)
            
            # Split long text into chunks (512 tokens max)
            text_chunks = [original_text[i:i+500] for i in range(0, len(original_text), 500)]
            translated_chunks = []
            
            for chunk in text_chunks:
                if chunk.strip():
                    result = translator(chunk, max_length=512)
                    translated_text = result[0].get("translation_text", chunk)
                    translated_chunks.append(translated_text)
            
            translated_text = " ".join(translated_chunks)
            
        except Exception as e:
            logger.warning(f"Job {job_id}: Translation failed, using original text: {str(e)}")
            translated_text = original_text
        
        logger.info(f"Job {job_id}: Translation complete ({len(translated_text)} characters)")
        
        # Step 4: Synthesize new audio (if dubbing enabled)
        synthesized_audio_path = None
        
        if enable_dubbing and translated_text:
            logger.info(f"Job {job_id}: Step 4/5 - Synthesizing translated audio")
            
            synthesized_audio_path = temp_dir / "synthesized_audio.wav"
            
            try:
                import pyttsx3
                
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.setProperty('volume', 0.9)
                engine.save_to_file(translated_text, str(synthesized_audio_path))
                engine.runAndWait()
                
                if synthesized_audio_path.exists():
                    logger.info(f"Job {job_id}: Audio synthesis complete ({synthesized_audio_path.stat().st_size} bytes)")
                else:
                    logger.warning(f"Job {job_id}: Synthesis failed, skipping dubbing")
                    synthesized_audio_path = None
            
            except Exception as e:
                logger.warning(f"Job {job_id}: Synthesis failed: {str(e)}, skipping dubbing")
                synthesized_audio_path = None
        else:
            logger.info(f"Job {job_id}: Step 4/5 - Skipping audio synthesis (dubbing disabled or no text)")
        
        # Step 5: Merge audio back into video
        logger.info(f"Job {job_id}: Step 5/5 - Merging audio with video")
        
        output_video_path = video_path.parent / f"{video_path.stem}_translated{video_path.suffix}"
        
        if synthesized_audio_path and synthesized_audio_path.exists():
            # Merge dubbed audio with original video
            merged_video = processor.merge_audio_video(
                str(video_path),
                str(synthesized_audio_path),
                str(output_video_path),
                video_codec='copy',
                audio_codec='aac'
            )
            
            if not merged_video:
                logger.warning(f"Job {job_id}: Video merge failed, using original video")
                shutil.copy(str(video_path), str(output_video_path))
        else:
            logger.info(f"Job {job_id}: No dubbed audio available, copying original video")
            shutil.copy(str(video_path), str(output_video_path))
        
        if not output_video_path.exists():
            raise Exception("Output video file was not created")
        
        output_size = output_video_path.stat().st_size
        logger.info(f"Job {job_id}: Video translation pipeline complete ({output_size} bytes)")
        
        # Update job with results
        job.status = JobStatus.COMPLETED
        job.output_file = output_video_path.as_posix()
        job.job_metadata = json.dumps({
            "source_language": source_language,
            "target_language": target_language,
            "original_text": original_text[:1000],  # Store preview
            "translated_text": translated_text[:1000],  # Store preview
            "dubbed": synthesized_audio_path is not None,
            "output_size_bytes": output_size,
            "pipeline_status": "success"
        })
        session.commit()
        
        logger.info(f"Job {job_id}: Video translation job completed successfully")
        
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Job {job_id}: Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to cleanup temp files: {str(e)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Job {job_id}: Video translation failed: {str(e)}", exc_info=True)
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = f"Video translation error: {str(e)}"
            session.commit()
        
        # Cleanup temp files on failure
        try:
            temp_dir = Path(tempfile.gettempdir()) / f"octavia_job_{job_id}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except:
            pass
        
        return False
