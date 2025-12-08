FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
RUN mkdir -p storage/uploads storage/results

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "app.main"]
