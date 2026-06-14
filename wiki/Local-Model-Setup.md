# Local Model Setup

ShortsMoneyPrinter does not install local video models for you. Local video stacks
change quickly, and installs depend on your GPU, CUDA/PyTorch version, operating
system, chosen runner, and model weights.

Instead, ShortsMoneyPrinter gives each local model a simple contract:

```bash
--local-command "your_runner --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

The command must write the generated MP4 block to `{output}`. It can use:

- `{input}`: prepared reference video block
- `{keyframe}`: representative image from the source block
- `{prompt}`: text file containing the generated prompt
- `{output}`: path where your runner must write the generated MP4
- `{index}`: zero-based block index

Plan mode does not need local models installed. Local model setup is only required
when you click Run or pass `--live`.

## Recommended Path

Use a separate folder for model runners, outside this repo:

```bash
mkdir -p ~/ai-video-runners
cd ~/ai-video-runners
```

Install and test the model runner directly first. After it can generate a short MP4,
wrap it with a command that accepts ShortsMoneyPrinter's placeholders.

## LTX Video

LTX Video is the default local model option because it is a good fit for local,
reference-driven remix workflows.

Official resources:

- GitHub: <https://github.com/Lightricks/LTX-Video>
- Docs: <https://docs.ltx.video>

The official repo lists LTX Video / LTX-2 capabilities including image-to-video,
multi-keyframe conditioning, video extension, video-to-video transformations, and
ComfyUI integration. The repo also lists multiple model variants and workflows,
including distilled and FP8 variants.

Typical setup shape:

```bash
cd ~/ai-video-runners
git clone https://github.com/Lightricks/LTX-Video.git
cd LTX-Video
# Follow the current official README/docs for Python, CUDA, weights, and workflow setup.
```

Example ShortsMoneyPrinter command shape:

```bash
smp run ./source.mp4 \
  --quality local \
  --live \
  --max-cost 10 \
  --max-total-seconds 10 \
  --local-command "python ~/ai-video-runners/run_ltx_smp.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

The `run_ltx_smp.py` wrapper is your adapter around whichever LTX runner you choose:
native scripts, Diffusers, ComfyUI, or another workflow.

## HunyuanVideo 1.5

HunyuanVideo 1.5 is the higher-quality local option in the current catalog.

Official resources:

- GitHub: <https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5>

The official repo lists Linux, Python 3.10+, CUDA-compatible PyTorch, and an NVIDIA
GPU with CUDA support. It also lists 14 GB GPU memory as the minimum with model
offloading enabled. More VRAM is strongly preferred for speed and 720p workflows.

Typical setup shape:

```bash
cd ~/ai-video-runners
git clone https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5.git
cd HunyuanVideo-1.5
# Follow the official README for dependencies, attention libraries, and checkpoint download.
```

Example ShortsMoneyPrinter command shape:

```bash
smp run ./source.mp4 \
  --quality hunyuan \
  --live \
  --max-cost 10 \
  --max-total-seconds 10 \
  --local-command "python ~/ai-video-runners/run_hunyuan_smp.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

For remixing, prefer an image-to-video or video-conditioned workflow when available.
Your wrapper should choose the Hunyuan checkpoint and resolution that fit your GPU.

## Wan 2.2

Wan 2.2 remains available as an explicit local option.

Official resources:

- GitHub: <https://github.com/Wan-Video/Wan2.2>
- TI2V-5B weights: <https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B>

The official repo includes installation instructions, model download links, and
variants for text-to-video, image-to-video, TI2V, speech-to-video, and animation.
For ShortsMoneyPrinter, the catalog points at Wan 2.2 TI2V-5B because it can work
with text/image-to-video style local workflows.

Typical setup shape:

```bash
cd ~/ai-video-runners
git clone https://github.com/Wan-Video/Wan2.2.git
cd Wan2.2
# Follow the official README for torch, requirements, and model download.
```

Example ShortsMoneyPrinter command shape:

```bash
smp run ./source.mp4 \
  --quality wan \
  --live \
  --max-cost 10 \
  --max-total-seconds 10 \
  --local-command "python ~/ai-video-runners/run_wan_smp.py --input {input} --keyframe {keyframe} --prompt {prompt} --output {output}"
```

Wan is useful when you already have a working Wan pipeline or want a separate
text/image-to-video path from LTX.

## Wrapper Script Checklist

Each wrapper should:

- Read the prompt text from the `{prompt}` file.
- Use `{input}` when the runner supports video reference input.
- Use `{keyframe}` when the runner supports image-to-video input.
- Write exactly one playable MP4 to `{output}`.
- Exit with a non-zero code when generation fails.
- Avoid writing secrets or large model files into the ShortsMoneyPrinter repo.

Minimal wrapper shape:

```python
from pathlib import Path
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--keyframe", required=True)
parser.add_argument("--prompt", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

prompt = Path(args.prompt).read_text(encoding="utf-8").strip()

subprocess.run(
    [
        "python",
        "your_model_inference.py",
        "--video",
        args.input,
        "--image",
        args.keyframe,
        "--prompt",
        prompt,
        "--output",
        args.output,
    ],
    check=True,
)
```

## Adding Another Local Model

Add a new `[[models]]` entry to `models.toml`:

```toml
[[models]]
key = "my-local-model"
provider_mode = "local"
provider = "local"
model_id = "my-local-model"
label = "My Local Model"
mode = "local-video-conditioning"
resolution = "local"
input_kind = "local-command"
estimated_cost_per_second = 0
detail = "Uses my installed local runner."
cost_note = ""
```

Restart `smp serve`. The model appears under Local automatically because the browser
loads `GET /api/models`.
