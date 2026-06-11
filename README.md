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
writes prompts, estimates cost before spending credits, runs your local Wan command
by default, preserves source audio, and exports a final MP4.

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
- Use local Wan generation by default.
- Switch to BYO Replicate for direct cloud Seedance generation.
- Add optional subject and script prompts.
- Auto-detect language or target Chinese, Hindi, English, and more.
- Keep original audio, generate TTS narration, or export silent video.
- Preserve original source audio when possible.
- Generate block prompts without needing an LLM key.
- Resume runs by skipping completed generated blocks.
- Export local MP4 files that you own.

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
| Optional subject prompt | Works |
| Optional script prompt | Works |
| Language auto-detect / target language | Works |
| Source audio, TTS, or no audio | Works |
| Local Wan command generation | Default |
| Replicate Seedance live generation | Optional |
| Resume completed blocks | Works |
| Concatenate generated blocks | Works |
| Preserve/mux original audio | Works |
| Optional burned-in captions | Works |
| Browser UI | Works |
| Local FastAPI API | Works |
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

Live generation with local Wan:

```bash
smp run <url-or-local-video> \
  --style nursery-3d \
  --max-total-seconds 10 \
  --live \
  --max-cost 10 \
  --wan-command "python run_wan.py --input {input} --prompt {prompt} --output {output}"
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
- A Wan command for default local live generation
- Replicate API token only if you want direct cloud generation

Replicate is optional. The default model selector is local Wan; if you change the
browser app to a Replicate model, the app keeps that preference on this machine.

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

### 2. Configure Local Wan For Live Runs

Plan mode works without a Wan command. Live local generation needs a command that
writes the generated block to `{output}`. The command can use these placeholders:
`{input}`, `{keyframe}`, `{prompt}`, `{output}`, and `{index}`.

Example:

```bash
smp run ./source.mp4 \
  --live \
  --max-cost 10 \
  --wan-command "python run_wan.py --input {input} --prompt {prompt} --output {output}"
```

### 3. Optional: Use Replicate Directly

If you prefer cloud generation, choose a Replicate model in the app or pass
`--quality standard`, `--quality budget`, or `--quality premium` in the CLI. Then set
your Replicate key:

```bash
export REPLICATE_API_TOKEN="your-token"
```

On Windows PowerShell:

```powershell
$env:REPLICATE_API_TOKEN="your-token"
```

You can still plan runs without this key.

### 4. Build The Web UI

```bash
cd web
npm install
npm run build
cd ..
```

### 5. Start The App

```bash
smp serve
```

## Model Modes

Local Wan is the default. Replicate models are optional direct-cloud modes. Costs are
estimates only; check provider pricing before spending real money. Replicate estimates
use the public billing tiers available on June 5, 2026. For Seedance 2.0 modes,
ShortsMoneyPrinter usually sends each source block as a reference video, so the
estimate uses Replicate's `video_in` tier.

| CLI value | Model | Input | Resolution | Estimate |
|---|---|---|---|---|
| `local` | External Wan command | local command | local | $0 cloud cost, uses your own setup |
| `budget` | Replicate Seedance 1.5 Pro | keyframe image-to-video | 480p | $0.013/sec, around $0.13 for 10s |
| `standard` | Replicate Seedance 2.0 Fast | video-to-video | 480p | $0.08/sec, around $0.80 for 10s |
| `premium` | Replicate Seedance 2.0 | video-to-video | 720p | $0.22/sec, around $2.20 for 10s |

The browser app defaults to a `$10.00 USD` max-cost cap and leaves Max seconds blank,
which means it plans the full source. Enter `10` for faster, cheaper tests.

## Example Workflows

### Recreate A Viral Clip With Local Wan

```bash
smp run "https://example.com/short" \
  --style anime \
  --max-total-seconds 10 \
  --live \
  --max-cost 10 \
  --wan-command "python run_wan.py --input {input} --prompt {prompt} --output {output}"
```

### Add Custom Direction

```bash
smp run ./source.mp4 \
  --prompt "make it colorful, toy-like, and optimized for Shorts" \
  --max-total-seconds 10
```

### Use Replicate Directly

```bash
export REPLICATE_API_TOKEN="your-token"

smp run ./source.mp4 \
  --quality standard \
  --live \
  --max-cost 10 \
  --max-total-seconds 10
```

### Generate TTS And Subtitles

```bash
smp run ./source.mp4 \
  --audio-mode tts \
  --video-script-prompt "Narrate this in Hindi with a fast hook." \
  --language hi \
  --tts-voice hi-IN-SwaraNeural \
  --captions \
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
