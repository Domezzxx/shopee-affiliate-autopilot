FROM python:3.11-slim

# ffmpeg = เผื่อ post-process วีดีโอ / android-tools-adb = คุม phone farm
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg android-tools-adb curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /app/data /app/data/media

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8088/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
