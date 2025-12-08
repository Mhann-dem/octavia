import logging
import time

logger = logging.getLogger(__name__)

async def translate_text(text: str, source_lang: str, target_lang: str, config) -> str:
    """Translate text using Helsinki NLP or stub"""
    try:
        if config.use_helsinki:
            return await translate_with_helsinki(text, source_lang, target_lang, config)
        else:
            return translate_with_stub(text, source_lang, target_lang)
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return translate_with_stub(text, source_lang, target_lang)

async def translate_with_helsinki(text: str, source_lang: str, target_lang: str, config) -> str:
    """Stub for Helsinki NLP translation"""
    logger.info(f"Using Helsinki NLP: {source_lang} -> {target_lang}")
    time.sleep(0.5)
    return f"[Translated to {target_lang}] {text}"

def translate_with_stub(text: str, source_lang: str, target_lang: str) -> str:
    """Stub translation for development"""
    logger.info(f"Stub translation: {source_lang} -> {target_lang}")
    time.sleep(0.2)
    
    translations = {
        ("en", "es"): "Hola, esto es una traducción.",
        ("en", "fr"): "Bonjour, ceci est une traduction.",
        ("en", "de"): "Hallo, dies ist eine Übersetzung.",
    }
    return translations.get((source_lang, target_lang), f"[{target_lang}] {text}")
