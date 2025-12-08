import asyncio
import json
import logging
import os

import aio_pika
import httpx
from aio_pika import Message, DeliveryMode

from app.tasks.transcribe import transcribe_audio
from app.tasks.translate import translate_text
from app.tasks.tts import generate_audio

logger = logging.getLogger(__name__)

class Worker:
    def __init__(self, config):
        self.config = config
        self.connection = None
        self.channel = None
        self.queue = None
        self.is_running = False
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.config.rabbitmq_url)
        self.channel = await self.connection.channel()
        self.queue = await self.channel.declare_queue(
            self.config.rabbitmq_queue,
            durable=True
        )
        logger.info(f"Connected to RabbitMQ queue: {self.config.rabbitmq_queue}")
    
    async def start(self):
        self.is_running = True
        try:
            await self.connect()
            await self.queue.consume(self.process_message, no_ack=False)
            logger.info("Worker started consuming messages")
            
            while self.is_running:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        self.is_running = False
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Worker stopped")
    
    async def process_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                job_data = json.loads(message.body.decode())
                logger.info(f"Processing job: {job_data.get('job_id')}")
                await self.process_job(job_data)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def process_job(self, job_data):
        job_id = job_data["job_id"]
        
        try:
            await self.update_job_status(job_id, "processing")
            
            source_path = job_data["source_file"]
            source_lang = job_data["source_lang"]
            target_lang = job_data["target_lang"]
            result_path = os.path.join(self.config.results_path, f"{job_id}.wav")
            
            transcription = await transcribe_audio(source_path, source_lang, self.config)
            translation = await translate_text(transcription, source_lang, target_lang, self.config)
            audio_path = await generate_audio(translation, target_lang, result_path, self.config)
            
            result_url = f"/results/{os.path.basename(audio_path)}"
            await self.update_job_status(job_id, "succeeded", result_url=result_url)
            logger.info(f"Job {job_id} completed")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await self.update_job_status(job_id, "failed", error=str(e))
    


    async def update_job_status(self, job_id, status, result_url=None, error=None):
        url = f"{self.config.api_base_url}/api/internal/jobs/{job_id}"  # ✅ Changed path
        headers = {"X-Internal-API-Key": self.config.internal_api_key}

        payload = {"status": status}
        if result_url:
            payload["result_url"] = result_url
        if error:
            payload["error"] = error
        
        try:
            response = await self.http_client.patch(url, json=payload, headers=headers)
            logger.info(f"Updated job {job_id} to {status}")
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")