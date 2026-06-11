<div align="center">

# 💸 ShortsMoneyPrinter

Generate and remix short-form videos with AI from a URL or local MP4.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![React](https://img.shields.io/badge/UI-React%20%2B%20Vite-646cff)
![License](https://img.shields.io/badge/license-MIT-green)
![Local First](https://img.shields.io/badge/local-first-111827)

</div>

Give ShortsMoneyPrinter a YouTube, TikTok, Instagram URL, or local video file. It
downloads or copies the source, probes the media, splits it into model-sized blocks,
writes prompts, estimates cost before spending credits, optionally calls Seedance
through your Replicate key, preserves source audio, and exports a final MP4.

```bash
smp run <url-or-local-video> --style nursery-3d --max-total-seconds 10
smp serve
```

Open the local app:

```text
http://127.0.0.1:8080
```

## What It Does

- Turn existing short videos into new AI-generated versions.
- Plan a remix before spending provider credits.
- Run from a browser UI, CLI, or local FastAPI API.
- Use BYO Replicate for live Seedance generation.
- Preserve original source audio when possible.
- Generate block prompts without needing an LLM key.
- Resume runs by skipping completed generated blocks.
- Export local MP4 files that you own.

ShortsMoneyPrinter is the open-source, self-hosted path. If you want managed
accounts, queues, credits, storage, and cheaper direct-provider generation without
setting up BytePlus/ModelArk yourself, use the hosted product: ShortsPrinter.

## Features

| Feature | Status |
|---|---|
| URL or local MP4 input | Works |
| YouTube/TikTok/Instagram download via yt-dlp | Works, subject to platform edge cases |
| Media probing with ffprobe | Works |
| <=15 second model block splitting | Works |
| Reference clip, keyframe, and audio extraction | Works |
| Deterministic prompt generation | Works |
| Cost estimate before provider calls | Works |
| Replicate Seedance live generation | Works |
| Resume completed blocks | Works |
| Concatenate generated blocks | Works |
| Preserve/mux original audio | Works |
| Optional burned-in captions | Works |
| Browser UI | Works |
| Local FastAPI API | Works |
| Local Wan command mode | Experimental |
| Direct BytePlus/ModelArk in OSS | Not included |
| Social posting/scheduling | Hosted roadmap |

## Interfaces

### Web UI

```bash
smp serve
```

Then open:

```text
http://127.0.0.1:8080
```

The web app lets you paste a source, choose style/model settings, plan the remix,
review the estimate, then run live generation only after confirming the cost cap.

### API

Start the local server:

```bash
smp serve --no-open
```

FastAPI docs are available at:

```text
http://127.0.0.1:8080/docs
```

Important routes:

- `POST /api/runs/plan`
- `POST /api/runs/{run_id}/start`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`
- `GET /api/runs/{run_id}/final.mp4`
- `GET /api/runs`

### CLI

Dry run with no provider spend:

```bash
smp run <url-or-local-video> --style nursery-3d --max-total-seconds 10
```

Live generation with Replicate Seedance:

```bash
smp run <url-or-local-video> \
  --style nursery-3d \
  --quality standard \
  --max-total-seconds 10 \
  --live \
  --max-cost 10
```

List recent local runs:

```bash
smp runs
```

List style presets:

```bash
smp styles
```

## Requirements

- macOS, Linux, or Windows
- Python 3.11+
- ffmpeg and ffprobe on your PATH
- Node 20+ only if you want to rebuild the React UI
- Replicate API token only if you want live cloud generation

GPU is not required for the default Replicate path. Local GPU only matters if you
wire the experimental local Wan command mode.

## Quick Start

### 1. Install

```bash
git clone https://github.com/KyleQ1/ShortsMoneyPrinter.git
cd ShortsMoneyPrinter
python -m venv .venv
source .venv/bin/activate
pip install -e ".[seedance]"
cp config.example.toml config.toml
```

On Windows, activate the virtual environment with:

```powershell
.\.venv\Scripts\activate
```

### 2. Set Replicate Key For Live Runs

The open-source tool expects self-hosted users to call Replicate directly:

```bash
export REPLICATE_API_TOKEN="your-token"
```

On Windows PowerShell:

```powershell
$env:REPLICATE_API_TOKEN="your-token"
```

You can still plan runs without this key.

### 3. Build The Web UI

```bash
cd web
npm install
npm run build
cd ..
```

### 4. Start The App

```bash
smp serve
```

## Model Modes

Costs are estimates only. Check provider pricing before spending real money. These
Replicate estimates use the public billing tiers available on June 5, 2026. For
Seedance 2.0 modes, ShortsMoneyPrinter usually sends each source block as a reference
video, so the estimate uses Replicate's `video_in` tier.

| CLI value | Model | Input | Resolution | Estimate |
|---|---|---|---|---|
| `budget` | Replicate Seedance 1.5 Pro | keyframe image-to-video | 480p | $0.013/sec, around $0.13 for 10s |
| `standard` | Replicate Seedance 2.0 Fast | video-to-video | 480p | $0.08/sec, around $0.80 for 10s |
| `premium` | Replicate Seedance 2.0 | video-to-video | 720p | $0.22/sec, around $2.20 for 10s |
| `local` | External Wan command | local command | local | $0 cloud cost, uses your own setup |

The browser app defaults to a `$10.00 USD` max-cost cap and leaves Max seconds blank,
which means it plans the full source. Enter `10` for faster, cheaper tests.

## Example Workflows

### Recreate A Viral Clip In A Style

```bash
smp run "https://example.com/short" \
  --style anime \
  --quality standard \
  --max-total-seconds 10
```

### Add Custom Direction

```bash
smp run ./source.mp4 \
  --prompt "make it colorful, toy-like, and optimized for Shorts" \
  --max-total-seconds 10
```

### Burn Captions

```bash
smp run ./source.mp4 --captions --max-total-seconds 10
```

Captions are off by default because they add transcription and render time.

### Test Seedance Conditioning

```bash
smp test-seedance ./source.mp4 --seconds 12 --style nursery-3d
```

### Preview Split Blocks

```bash
smp split ./source.mp4 --max 12 --write ./blocks
```

## Output Folder

Each run writes local files:

```text
runs/<run-id>/
  source/source.mp4
  audio/source.m4a
  plan.json
  blocks/block_000_ref.mp4
  blocks/block_000_keyframe.jpg
  prompts/block_000.txt
  generated/block_000.mp4
  captions.ass
  final.mp4
```

`captions.ass`, generated blocks, and `final.mp4` appear only when those steps run.

## Configuration

Copy the example config:

```bash
cp config.example.toml config.toml
```

Use environment variables for secrets. Do not commit provider keys.

```bash
export REPLICATE_API_TOKEN="your-token"
```

## Troubleshooting

**Plan says ffmpeg or ffprobe is missing**

Install ffmpeg and make sure both `ffmpeg` and `ffprobe` are on your PATH.

**URL download fails**

Use a public YouTube, TikTok, or Instagram video URL. Private, login-protected,
age-gated, removed, or platform-blocked videos may fail. If a URL keeps failing,
download the video yourself and use the local file path.

**Run says the Replicate package is missing**

Install the Seedance extra:

```bash
pip install -e ".[seedance]"
```

**Run says the Replicate token is missing**

Set `REPLICATE_API_TOKEN`, then restart `smp serve`.

**Estimate is over your max cost**

Lower Max seconds, choose Budget, or increase the max-cost cap intentionally.

**Local Wan mode fails**

Local mode requires a command that writes the generated block to `{output}` and can use
`{input}`, `{keyframe}`, `{prompt}`, `{output}`, and `{index}` placeholders.

## Development

Backend checks:

```bash
python -m ruff check app tests
python -m pytest -q
```

Frontend build:

```bash
cd web
npm install
npm run build
```

Frontend dev server:

```bash
cd web
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8080`, so keep FastAPI running
in another terminal:

```bash
smp serve --no-open
```

## Roadmap

- Add public demo video/GIFs.
- Validate more real-world TikTok, YouTube Shorts, and Instagram Reels sources.
- Improve URL failure messages.
- Validate Budget and Premium modes end to end.
- Improve the React local app.
- Prototype consistent character and brand-kit planning.
- Keep hosted accounts, queues, billing, and managed direct-provider credits in ShortsPrinter.
