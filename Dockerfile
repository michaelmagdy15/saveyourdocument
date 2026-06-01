# ==============================================
# SAVEYOURDOCUMENT - Production Dockerfile
# Single container: FastAPI + React static build
# Optimized for Google Cloud Run
# By Mitrixo Systems
# ==============================================

# ---- Stage 1: Build React Frontend ----
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Production Python Runtime ----
FROM python:3.11-slim AS production

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies (python-docx needs lxml C extensions)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libxml2-dev libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Copy built React frontend into a static directory the backend will serve
COPY --from=frontend-builder /app/frontend/dist ./static/

# Create temp_uploads directory
RUN mkdir -p /app/backend/temp_uploads

# Expose Cloud Run's default port
EXPOSE 8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1

# Run with uvicorn on Cloud Run's PORT
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--timeout-keep-alive", "120"]
