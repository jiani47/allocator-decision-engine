# Stage 1: Build frontend
FROM node:22-slim AS frontend-builder
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY --from=frontend-builder /build/dist ./static

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.api.app:app --host 0.0.0.0 --port ${PORT}"]
