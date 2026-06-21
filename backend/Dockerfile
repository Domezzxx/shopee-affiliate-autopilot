FROM python:3.11-slim

# ffmpeg = ทำคลิป/ใส่เสียง · fonts-thai = ซับไทยไม่เป็นกล่อง · adb = คุม phone farm · tzdata = เวลาไทย
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DATA_DIR=/app/data \
    TZ=Asia/Bangkok
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fonts-thai-tlwg android-tools-adb curl tzdata \
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
