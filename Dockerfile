FROM python:3.12-slim

# Non-root user for security
RUN groupadd -r dkg && useradd -r -g dkg dkg

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY data/ ./data/

# Ownership
RUN chown -R dkg:dkg /app
USER dkg

EXPOSE 8000

ENV PYTHONPATH=/app
ENV LOG_LEVEL=info

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
