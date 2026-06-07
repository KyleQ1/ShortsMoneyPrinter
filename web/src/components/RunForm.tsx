import type { FormEvent } from "react";
import { modelInfo } from "../modelInfo";
import type { Quality, RemixRequest, StyleOption } from "../types";
import { classNames, parseUsd } from "../lib";

export type RunFormState = {
  source: string;
  style: string;
  prompt: string;
  quality: Quality;
  maxCost: string;
  maxSeconds: string;
  captions: boolean;
  wanCommand: string;
};

type RunFormProps = {
  state: RunFormState;
  styles: StyleOption[];
  sourceInvalid: boolean;
  planning: boolean;
  running: boolean;
  onChange: (next: RunFormState) => void;
  onPlan: () => void;
  onRun: () => void;
};

export function toRequest(state: RunFormState): RemixRequest {
  return {
    source: state.source.trim(),
    style: state.style,
    prompt: state.prompt.trim() || null,
    quality: state.quality,
    max_cost: parseUsd(state.maxCost),
    captions: state.captions,
    max_total_seconds: state.maxSeconds ? Number(state.maxSeconds) : null,
    wan_command: state.wanCommand.trim() || null,
  };
}

export function requestFingerprint(body: RemixRequest): string {
  return JSON.stringify({
    source: body.source,
    style: body.style,
    prompt: body.prompt,
    quality: body.quality,
    captions: body.captions,
    max_total_seconds: body.max_total_seconds,
    wan_command: body.wan_command,
  });
}

export function RunForm({
  state,
  styles,
  sourceInvalid,
  planning,
  running,
  onChange,
  onPlan,
  onRun,
}: RunFormProps) {
  const model = modelInfo[state.quality];

  function update<K extends keyof RunFormState>(key: K, value: RunFormState[K]) {
    onChange({ ...state, [key]: value });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    onPlan();
  }

  return (
    <section className="panel">
      <h2 className="text-sm font-extrabold text-ink">Run</h2>
      <form className="mt-4 space-y-4" onSubmit={submit}>
        <div>
          <label className="label" htmlFor="source">
            Source video
          </label>
          <input
            id="source"
            className={classNames("field", sourceInvalid && "field-invalid")}
            value={state.source}
            onChange={(event) => update("source", event.target.value)}
            placeholder="YouTube, Instagram, TikTok URL, or /path/to/video.mp4"
            aria-invalid={sourceInvalid}
          />
          <p className="hint">Use a public YouTube, Instagram, or TikTok URL, or a local MP4 path on this machine.</p>
        </div>

        <div>
          <label className="label" htmlFor="style">
            Style
          </label>
          <select id="style" className="field" value={state.style} onChange={(event) => update("style", event.target.value)}>
            {styles.map((style) => (
              <option key={style.key} value={style.key}>
                {style.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label" htmlFor="prompt">
            Prompt <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id="prompt"
            className="field min-h-24 resize-y"
            value={state.prompt}
            onChange={(event) => update("prompt", event.target.value)}
            placeholder="Optional direction, e.g. make it playful, keep the same beat, use toy-like characters."
          />
        </div>

        <div>
          <label className="label" htmlFor="quality">
            Model
          </label>
          <select
            id="quality"
            className="field"
            value={state.quality}
            onChange={(event) => update("quality", event.target.value as Quality)}
          >
            <option value="budget">API key - Replicate Seedance 1.5 Pro</option>
            <option value="standard">API key - Replicate Seedance 2.0 Fast</option>
            <option value="premium">API key - Replicate Seedance 2.0</option>
            <option value="local">Local - Wan 2.2 TI2V-5B</option>
          </select>
          <div className="mt-2 rounded-md border border-line bg-teal-50/60 p-3">
            <b className="block text-sm text-ink">{model.title}</b>
            <span className="mt-1 block text-xs text-muted">{model.detail}</span>
            <span className="mt-2 block text-xs font-bold text-accent">{model.cost}</span>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="maxCost">
              Max cost (USD)
            </label>
            <input
              id="maxCost"
              className="field"
              inputMode="decimal"
              value={state.maxCost}
              onChange={(event) => update("maxCost", event.target.value)}
              placeholder="$10.00 USD"
            />
            <p className="hint">Default cap is $10.00 USD. Run stops before provider calls if the estimate is higher.</p>
          </div>
          <div>
            <label className="label" htmlFor="maxSeconds">
              Max seconds
            </label>
            <input
              id="maxSeconds"
              className="field"
              min="1"
              step="1"
              type="number"
              value={state.maxSeconds}
              onChange={(event) => update("maxSeconds", event.target.value)}
              placeholder="unlimited"
            />
            <p className="hint">Blank means unlimited and plans the full source.</p>
          </div>
        </div>

        {state.quality === "local" ? (
          <div>
            <label className="label" htmlFor="wanCommand">
              Wan command
            </label>
            <input
              id="wanCommand"
              className="field"
              value={state.wanCommand}
              onChange={(event) => update("wanCommand", event.target.value)}
              placeholder="optional for local mode"
            />
            <p className="hint">Can include {"{input}"}, {"{keyframe}"}, {"{prompt}"}, {"{output}"}, and {"{index}"} placeholders.</p>
          </div>
        ) : null}

        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={state.captions}
            onChange={(event) => update("captions", event.target.checked)}
            className="h-4 w-4 rounded border-line text-accent focus:ring-accent"
          />
          Add burned-in captions
        </label>
        <p className="hint">Optional and off by default. Adds transcription/render time and requires local Whisper plus ffmpeg subtitle support.</p>

        <div className="flex gap-3 pt-1">
          <button className="btn btn-secondary flex-1" disabled={planning || running} type="submit">
            {planning ? "Planning..." : "Plan"}
          </button>
          <button className="btn flex-1" disabled={planning || running} type="button" onClick={onRun}>
            {running ? "Running..." : "Run"}
          </button>
        </div>
        <p className="hint">
          <b>Plan</b> creates a dry-run timeline and cost estimate without spending credits. <b>Run</b> only calls the provider after
          the estimate is under your max cost and you confirm.
        </p>
      </form>
    </section>
  );
}
