# Optional Linux/dev image (the primary distribution is the .exe/.dmg desktop app).
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY . .

ENTRYPOINT ["omp"]
CMD ["--help"]
