FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FORMYDJ_HOST=0.0.0.0 \
    FORMYDJ_PORT=8765 \
    FORMYDJ_NO_BROWSER=1 \
    FORMYDJ_OUTPUT_DIR=/downloads

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip yt-dlp

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /downloads "/home/appuser/Library/Application Support/ForMyDJ" \
    && chown -R appuser:appuser /app /downloads /home/appuser

USER appuser
VOLUME ["/downloads"]
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/jobs', timeout=3).read()"

CMD ["formydj", "serve", "--no-browser", "--port", "8765"]
