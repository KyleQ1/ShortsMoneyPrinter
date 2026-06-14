# Linux/dev image for running ShortsMoneyPrinter (CLI + web server).
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY . .

ENTRYPOINT ["smp"]
CMD ["--help"]
