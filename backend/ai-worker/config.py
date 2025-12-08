import os

class Config:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.rabbitmq_queue = os.getenv("RABBITMQ_QUEUE", "jobs.queue")
        self.rabbitmq_dlq = os.getenv("RABBITMQ_DLQ", "jobs.dlq")
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8080")
        self.service_api_key = os.getenv("SERVICE_API_KEY", "dev_key")
        self.storage_path = os.getenv("STORAGE_PATH", "./storage")
        self.upload_path = os.getenv("UPLOAD_PATH", "./storage/uploads")
        self.results_path = os.getenv("RESULTS_PATH", "./storage/results")
        self.use_openai = os.getenv("USE_OPENAI", "false").lower() == "true"
        self.use_helsinki = os.getenv("USE_HELSINKI", "false").lower() == "true"
        self.use_coqui = os.getenv("USE_COQUI", "false").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.internal_api_key = os.getenv("INTERNAL_API_KEY", "internal_key_change_in_production")
        
        for path in [self.storage_path, self.upload_path, self.results_path]:
            os.makedirs(path, exist_ok=True)
