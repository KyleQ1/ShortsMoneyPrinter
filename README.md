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
writes prompts, estimates cost before spending credits, runs your local LTX Video
command by default, preserves source audio, and exports a final MP4.

```bash
smp run <url-or-local-video> --style nursery-3d --max-total-seconds 10
smp serve
```

Open the local app:

```text
http://127.0.0.1:8080
```

## Demo

<!--
DEMO ASSETS — fill after the first validated live run:
- docs/demo.gif        : end-to-end remix (paste URL -> plan -> run -> final MP4)
- docs/before-after.png: source clip frame beside the AI-generated frame
- docs/ui.png          : the browser app showing a plan + cost estimate
Then uncomment the block below.

<div align="center">

![ShortsMoneyPrinter demo](docs/demo.gif)

| Source | AI remix |
|---|---|
| ![source](docs/before.png) | ![after](docs/after.png) |

</div>
-->

_Demo video and before/after screenshots land here after the first validated live run._

## What It Does

- Turn existing short videos into new AI-generated versions.
- Plan a remix before spending provider credits.
- Run from a browser UI, CLI, or local FastAPI API.
- Use local LTX Video generation by default.
- Switch local runs to HunyuanVideo 1.5 or Wan 2.2 when those fit your GPU.
- Switch to BYO Replicate for direct cloud Seedance generation.
- Choose a style preset, edit the visual prompt, and save custom styles.
- Optionally use a BYO prompt API key to rewrite block prompts.
- Auto-detect language or target Chinese, Hindi, English, and more.
- Keep original audio, upload a soundtrack, or export silent video in the Web UI.
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
| Optional AI prompt writer | Works, BYO OpenAI-compatible key |
| Cost estimate before provider calls | Works |
| Custom style presets | Works |
| Language auto-detect / target language | Works |
| Source audio, uploaded audio, or no audio | Works in Web UI |
| TTS narration | CLI/API only |
| Local LTX Video command generation | Default |
| Local HunyuanVideo 1.5 command generation | Works |
| Local Wan 2.2 command generation | Works |
| Replicate Seedance live generation | Optional, experimental until validated |
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

Live generation with local LTX Video:

```bash
smp run <url-or-local-video> \
  --style nursery-3d \
  --max-total-seconds 10 \
  --live \
  --max-cost 10 \
  --local-command "python run_ltx.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

Live generation with Replicate Seedance:

```bash
smp run <url-or-local-video> \
  --style nursery-3d \
  --quality seedance-2.0-fast \
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
- A local model command for live generation
- Replicate API token only if you want direct cloud generation

Replicate is optional. The default model selector is local LTX Video; if you change
the browser app to Hunyuan, Wan, or a Replicate model, the app keeps that preference
on this machine.

Local model installs are BYO because each runner has its own CUDA, PyTorch, weight,
and workflow requirements. See the [Local Model Setup wiki](wiki/Local-Model-Setup.md)
for LTX Video, HunyuanVideo 1.5, Wan 2.2, and wrapper command examples.

## Quick Start

### 1. Install

```bash
git clone https://github.com/KyleQ1/ShortsMoneyPrinter.git
cd ShortsMoneyPrinter
python -m venv .venv
source .venv/bin/activate
pip install -e ".[seedance]"
cp .env.example .env   # optional — only needed for the cloud models
```

On Windows, activate the virtual environment with:

```powershell
.\.venv\Scripts\activate
```

### 2. Choose Local Or Remote Generation

Plan mode works without a local model install or provider key. Live generation needs
one of these paths:

**Local:** install your preferred local runner and pass a command that writes the
generated block to `{output}`. See the
[Local Model Setup wiki](wiki/Local-Model-Setup.md) for LTX Video, HunyuanVideo 1.5,
Wan 2.2, GPU notes, and wrapper examples.

```bash
smp run ./source.mp4 \
  --live \
  --max-cost 10 \
  --local-command "python run_ltx.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

**Remote:** choose a Replicate model in the app or pass `--quality
seedance-2.0-fast`, `--quality seedance-2.0`, or `--quality seedance-1.5-pro` in
the CLI. Then set your Replicate key:

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

Local LTX Video is the default. HunyuanVideo 1.5 and Wan 2.2 are available as local
command modes. Replicate models are optional direct-cloud modes, and the Replicate
live-generation paths are marked experimental until a validated end-to-end run is
published. Model metadata lives in `models.toml`, which feeds the API, CLI, and
browser model picker.

Costs are estimates only; check provider pricing before spending real money.
Replicate estimates use the public billing tiers available on June 5, 2026. Seedance
pricing changes by input type: image/keyframe input is cheaper than video reference
input. ShortsMoneyPrinter sends each source block as a reference video for Seedance
2.0 modes, so those estimates use the video-reference rate.

| CLI value | Model | Input | GPU guidance | Estimate |
|---|---|---|---|---|
| `local` | LTX Video | local command | Try 2B/distilled on 8-12GB VRAM; use 13B/FP8 on 16-24GB+ | $0 cloud cost |
| `hunyuan` | HunyuanVideo 1.5 | local command | Upstream minimum is 14GB VRAM with offload; 24GB+ NVIDIA is the practical target | $0 cloud cost |
| `wan` | Wan 2.2 TI2V-5B | local command | 4090-class NVIDIA GPU recommended for 720p local runs | $0 cloud cost |
| `seedance-1.5-pro` | Replicate Seedance 1.5 Pro | keyframe image-to-video | Cloud/BYO key | $0.013/sec, around $0.13 for 10s |
| `seedance-2.0-fast` | Replicate Seedance 2.0 Fast | video-to-video | Cloud/BYO key | $0.08/sec with video input; $0.04/sec with image/keyframe input |
| `seedance-2.0` | Replicate Seedance 2.0 | video-to-video | Cloud/BYO key | $0.22/sec with video input; $0.11/sec with image/keyframe input |

Local GPU notes are practical starting points, not hard limits. Exact VRAM depends on
the runner, quantization, offloading, resolution, frame count, and whether you enable
upscaling. For local models, NVIDIA CUDA is the safest path today; Apple Silicon and
CPU/offload paths may work only for specific runners and will be much slower.

For install notes and wrapper examples, see the
[Local Model Setup wiki](wiki/Local-Model-Setup.md).

The browser app defaults to a `$10.00 USD` max-cost cap and leaves Duration at the
full source length when the source is under 60 seconds. Longer sources are capped at
60 seconds by default. Move the slider lower for faster, cheaper tests.

### Adding More Models

ShortsMoneyPrinter keeps model selection intentionally simple. To add another model:

1. Add a `[[models]]` entry in `models.toml` with the model key, provider,
   `provider_mode`, label, mode, resolution, input kind, and cost estimate.
2. Use `provider_mode = "local"` for local command models or `provider_mode =
   "remote"` for cloud/BYO-key models. The browser Local/Remote switch and dropdown
   are generated from this field.
3. For Seedance-style pricing, set both `cost_per_second_image` and
   `cost_per_second_video`, then set `input_kind` to the path this app actually uses
   for estimation.
4. For local models, keep using `--local-command` unless the model needs custom
   backend code. The command receives `{input}`, `{keyframe}`, `{prompt}`, `{output}`,
   and `{index}` placeholders.

The API exposes the loaded catalog at `GET /api/models`, and the browser renders that
response directly. Adding another UI option no longer requires editing the form
component.

## Example Workflows

### Recreate A Viral Clip With Local LTX Video

```bash
smp run "https://example.com/short" \
  --style anime \
  --max-total-seconds 10 \
  --live \
  --max-cost 10 \
  --local-command "python run_ltx.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

### Use HunyuanVideo 1.5 Locally

```bash
smp run ./source.mp4 \
  --quality hunyuan \
  --live \
  --max-cost 10 \
  --max-total-seconds 10 \
  --local-command "python run_hunyuan.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

### Use Wan 2.2 Locally

```bash
smp run ./source.mp4 \
  --quality wan \
  --live \
  --max-cost 10 \
  --max-total-seconds 10 \
  --local-command "python run_wan.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
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
  --quality seedance-2.0-fast \
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

ShortsMoneyPrinter is configured entirely through environment variables — there is no
config file to manage, and it runs on sensible defaults out of the box. Override anything
in a `.env` file (copy `.env.example`) or in your shell. Never commit provider keys.

```bash
export REPLICATE_API_TOKEN="your-token"   # only for the cloud Seedance models
export VIDEO_ENDPOINT="replicate"          # replicate | fal
export TTS_VOICE="en-US-AriaNeural"        # voice when a run's audio mode is "tts"
export WHISPER_MODEL="large-v3"            # caption model: tiny | base | small | medium | large-v3
```

## Troubleshooting

**Plan says ffmpeg or ffprobe is missing**

Install ffmpeg and make sure both `ffmpeg` and `ffprobe` are on your PATH.

**URL download fails**

Use a public YouTube, TikTok, or Instagram video URL. Private, login-protected,
age-gated, removed, or platform-blocked videos may fail. If a URL keeps failing,
download the video yourself and use the local file path.

YouTube can also block yt-dlp extraction for a Short even when the page still embeds.
Update yt-dlp first. If the video needs a logged-in session, export YouTube cookies in
Netscape `cookies.txt` format and set `YTDLP_COOKIES_FILE=/absolute/path/to/cookies.txt`
in `.env`, then restart `smp serve`. Do not paste cookies into issues, commits, or
terminal logs.

**Run says the Replicate package is missing**

Install the Seedance extra:

```bash
pip install -e ".[seedance]"
```

**Run says the Replicate token is missing**

Set `REPLICATE_API_TOKEN`, then restart `smp serve`.

**Estimate is over your max cost**

Lower Max seconds, choose Budget, or increase the max-cost cap intentionally.

**Local model mode fails**

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
