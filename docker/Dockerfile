# NLS Fine-tune SciX - Local Inference Server
# Provides both pipeline and vLLM endpoints for nectar integration
#
# Build: docker build -t nls-server -f docker/Dockerfile .
# Run:   docker run --gpus all -p 8000:8000 nls-server
#
# For CPU-only (slower): docker run -p 8000:8000 -e DEVICE=cpu nls-server

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY docker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY packages/finetune/src/finetune /app/finetune
COPY docker/server.py /app/server.py
COPY data/datasets/raw/gold_examples.json /app/data/gold_examples.json

# Copy data files needed at runtime
COPY data/model/institution_synonyms.json /app/data/model/institution_synonyms.json
COPY data/model/bibstem_synonyms.json /app/data/model/bibstem_synonyms.json
COPY data/model/uat_synonyms.json /app/data/model/uat_synonyms.json
COPY data/model/planetary_feature_synonyms.json /app/data/model/planetary_feature_synonyms.json
COPY data/datasets/raw/gold_examples_intent.json /app/data/gold_examples_intent.json

# Environment variables
ENV MODEL_NAME=adsabs/NLQT-Qwen3-1.7B
ENV DEVICE=cuda
ENV PORT=8000
ENV HYBRID_MODE=true
ENV RAG_ENABLED=true
ENV RAG_NUM_EXAMPLES=3
ENV RAG_MAX_CARDS=2
ENV GOLD_EXAMPLES_INTENT_PATH=/app/data/gold_examples_intent.json

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE 8000

CMD ["python", "server.py"]
