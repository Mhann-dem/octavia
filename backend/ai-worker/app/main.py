import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from app.worker import Worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    config = Config()
    worker = Worker(config)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()
    except Exception as e:
        logger.error(f"Worker error: {e}")
        await worker.stop()

if __name__ == "__main__":
    asyncio.run(main())
