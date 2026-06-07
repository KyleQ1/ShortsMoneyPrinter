# ShortsMoneyPrinter

ShortsMoneyPrinter is an open-source local engine for remixing short-form videos with
AI video models.

Paste a YouTube, TikTok, Instagram URL, or local MP4. The app downloads or copies the
source, splits it into model-sized blocks, writes deterministic prompts, estimates
cost before spending credits, optionally calls Seedance, preserves the original audio,
and exports a final MP4.

This repo is for power users: developers, technical creators, agencies, and AI video
experimenters who are comfortable with local setup, API keys, ffmpeg, and model costs.

```bash
smp run <url-or-local-video> --style nursery-3d --max-total-seconds 10
smp serve
```

Open the local app at:

```text
http://127.0.0.1:8080
```

## Why This Exists

Short-form AI video tools are usually either expensive hosted products or messy local
scripts. ShortsMoneyPrinter aims for the middle:

- local and inspectable
- cost-aware before provider calls
- useful from both CLI and browser
- BYO API key for cloud models
- ready to become a hosted all-in-one product later

The hosted version should live outside this public OSS repo in a separate private
website/product codebase.

## What Works Today

- Plan a remix from a public URL or local video file.
- Probe duration, resolution, aspect ratio, and source audio.
- Split the source into blocks of 15 seconds or less.
- Extract reference clips, keyframes, and source audio.
- Generate deterministic prompts without an LLM key.
- Estimate model cost before any provider call.
- Run live generation through Replicate Seedance.
- Resume live runs by skipping completed generated blocks.
- Concatenate generated blocks and mux preserved source audio.
- Optionally burn captions into the final MP4.
- Use the same runner from the CLI and FastAPI React app.

## Not Done Yet

- Real-world hardening across many YouTube/TikTok/Instagram edge cases.
- Direct Seedance/BytePlus integration.
- Fully validated local Wan GPU workflow.
- Automatic hook/script rewriting.
- Social posting, scheduling, and analytics.
- Managed hosted credits.
- Consistent character/brand kits.

## Quickstart

Requirements:

- Python 3.11+
- ffmpeg and ffprobe on your PATH
- Node 20+ if you want to rebuild the React UI
- Replicate API token for live cloud generation

Install:

```bash
git clone <repo>
cd ShortsMoneyPrinter
python -m venv .venv
source .venv/bin/activate
pip install -e ".[seedance]"
cp config.example.toml config.toml
```

Set your Replicate key for live runs:

```bash
export REPLICATE_API_TOKEN="your-token"
```

Build the React UI once:

```bash
cd web
npm install
npm run build
cd ..
```

Start the local server:

```bash
smp serve
```

Use `http://127.0.0.1:8080` for the local remix app.

## CLI Examples

Dry-run only. This does not spend credits:

```bash
smp run <url-or-local-video> --style nursery-3d --max-total-seconds 10
```

Live Standard run. This can spend Replicate credits and refuses to start if the
estimate exceeds your cap:

```bash
smp run <url-or-local-video> \
  --style nursery-3d \
  --quality standard \
  --max-total-seconds 10 \
  --live \
  --max-cost 10
```

Optional prompt:

```bash
smp run <url-or-local-video> \
  --prompt "make it playful, toy-like, and colorful" \
  --max-total-seconds 10
```

Optional captions:

```bash
smp run <url-or-local-video> --captions --max-total-seconds 10
```

Captions are off by default because they add local transcription/render time and
require Whisper plus ffmpeg subtitle support.

## Browser Flow

The React app has two main buttons:

**Plan** creates the dry-run timeline and cost estimate. It downloads or copies the
source, probes metadata, splits blocks, extracts audio/keyframes, writes prompts, and
writes `plan.json`. It does not call Replicate and does not spend credits.

**Run** reuses the current plan when possible, checks the estimate against your max
cost, asks for confirmation, and only then starts live generation.

If the estimate is higher than your max cost, the app stops before provider calls and
tells you the estimated amount.

## Model Modes

Costs are estimates only. Check provider pricing before spending real money. These
Replicate estimates use the public billing tiers available on June 5, 2026. For
Seedance 2.0 modes, this app usually sends each source block as a reference video, so
the estimate uses Replicate's `video_in` tier instead of the cheaper non-video-input
tier.

| CLI value | Visible model | Input | Resolution | What to expect |
|---|---|---|---|---|
| `budget` | Replicate Seedance 1.5 Pro | keyframe image-to-video | 480p | $0.013/sec without generated audio, around $0.13 for 10s or $0.39 for 30s. Does not take direct video input, so the app uses a keyframe. |
| `standard` | Replicate Seedance 2.0 Fast | video-to-video | 480p | $0.08/sec using the video-input tier, around $0.80 for 10s or $2.40 for 30s. Best default for faithful source motion. |
| `premium` | Replicate Seedance 2.0 | video-to-video | 720p | $0.22/sec using the video-input tier, around $2.20 for 10s or $6.60 for 30s. Highest cloud quality, most expensive. |
| `local` | External Wan 2.2 TI2V-5B command | local command | local | $0 cloud cost, but requires your own hardware and command. Not validated here yet. |

The browser app defaults to a `$10.00 USD` max-cost cap and leaves Max seconds blank,
which means it plans the full source. Enter `10` for faster, cheaper tests.

## Run Folder

Each run writes a local folder:

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

Set:

```bash
export REPLICATE_API_TOKEN="your-token"
```

Then restart `smp serve`.

**Estimate is over your max cost**

Lower Max seconds, choose Budget, or increase the max-cost cap intentionally.

**Local Wan mode fails**

Local mode requires a command that writes the generated block to `{output}` and can use
`{input}`, `{keyframe}`, `{prompt}`, `{output}`, and `{index}` placeholders. This path
is experimental and has not been validated on this machine.

## Roadmap

Near-term priorities:

- Validate one real Replicate Seedance 2.0 Fast live run end to end.
- Improve URL failure messages based on real test cases.
- Add a public demo video/GIF.
- Validate Budget and Premium modes.
- Keep polishing the React local app.
- Prototype consistent character and brand-kit planning.

## Legal

ShortsMoneyPrinter is a creator tool that produces a local file. You choose the source,
you approve the output, and you decide where to publish it. You are responsible for
having the rights to what you publish and for complying with each platform's terms.

## License

Source-available. Free for self-hosted personal and commercial creation; the hosted
multi-tenant service is the commercial offering.
