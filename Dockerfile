# ---- Stage 1: build the React frontend (throwaway build tooling) ----
FROM node:22-slim AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- Stage 2: final runtime image (no Node, npm, or build tools) ----
FROM python:3.14-slim AS app
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# app package (incl. app/demo_data) + the built frontend at the path app/main.py
# expects: Path(__file__).parent.parent / "web" / "dist" == /app/web/dist
COPY app/ ./app/
COPY --from=frontend /web/dist ./web/dist

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
