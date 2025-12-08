import logging
import os
import time

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

async def generate_audio(text: str, language: str, output_path: str, config) -> str:
    """Generate audio using Coqui TTS or stub"""
    try:
        if config.use_coqui:
            return await generate_with_coqui(text, language, output_path, config)
        else:
            return generate_with_stub(text, language, output_path)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return generate_with_stub(text, language, output_path)

async def generate_with_coqui(text: str, language: str, output_path: str, config) -> str:
    """Stub for Coqui TTS"""
    logger.info(f"Using Coqui TTS for: {language}")
    time.sleep(1.0)
    return generate_with_stub(text, language, output_path)

def generate_with_stub(text: str, language: str, output_path: str) -> str:
    """Stub audio generation for development"""
    logger.info(f"Generating stub audio: {language}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    duration = max(1.0, len(text) / 10)
    sample_rate = 22050
    samples = int(duration * sample_rate)
    
    t = np.linspace(0, duration, samples, False)
    audio_data = np.sin(440 * 2 * np.pi * t) * 0.01
    
    sf.write(output_path, audio_data, sample_rate, subtype='PCM_16')
    logger.info(f"Generated audio: {output_path}")
    
    return output_path
