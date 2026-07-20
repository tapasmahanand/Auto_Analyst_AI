# Optional Docker image for the backend. The default Render deploy (render.yaml)
# uses the native Python runtime, where WeasyPrint's system libraries (pango)
# cannot be installed — so PDF export is unavailable there (Markdown/HTML reports
# still work). Use this image instead if you need PDF export, or to deploy on
# any other container host (Railway, Fly.io, Cloud Run, a VPS).
#
# For Render: set runtime: docker, dockerfilePath: ./backend/Dockerfile,
# dockerContext: ./backend, and drop buildCommand/startCommand/PYTHON_VERSION.
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
