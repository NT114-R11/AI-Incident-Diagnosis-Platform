
FROM python:3.14-slim

# Prevent Python from writing bytecode and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source and Alembic configuration
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Include Telegram polling entrypoint
COPY scripts/telegram_polling.py ./scripts/telegram_polling.py

# Run as non-root user
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Default command: FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
