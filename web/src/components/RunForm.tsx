import type { FormEvent } from "react";
import { modelInfo } from "../modelInfo";
import type { AudioMode, Language, Quality, RemixRequest, StyleOption } from "../types";
import { classNames, parseUsd } from "../lib";

export type RunFormState = {
  source: string;
  style: string;
  prompt: string;
  videoSubjectPrompt: string;
  videoScriptPrompt: string;
  language: Language;
  audioMode: AudioMode;
  ttsVoice: string;
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
    video_subject_prompt: state.videoSubjectPrompt.trim() || null,
    video_script_prompt: state.videoScriptPrompt.trim() || null,
    language: state.language,
    audio_mode: state.audioMode,
    tts_voice: state.ttsVoice.trim() || null,
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
    video_subject_prompt: body.video_subject_prompt,
    video_script_prompt: body.video_script_prompt,
    language: body.language,
    audio_mode: body.audio_mode,
    tts_voice: body.tts_voice,
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
          <label className="label" htmlFor="videoSubjectPrompt">
            Video subject prompt <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id="videoSubjectPrompt"
            className="field min-h-20 resize-y"
            value={state.videoSubjectPrompt}
            onChange={(event) => update("videoSubjectPrompt", event.target.value)}
            placeholder="Optional niche or subject, e.g. satisfying finance facts for Shorts."
          />
        </div>

        <div>
          <label className="label" htmlFor="videoScriptPrompt">
            Video script prompt <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id="videoScriptPrompt"
            className="field min-h-24 resize-y"
            value={state.videoScriptPrompt}
            onChange={(event) => update("videoScriptPrompt", event.target.value)}
            placeholder="Optional narration/script direction. Required only if Audio is set to TTS."
          />
        </div>

        <div>
          <label className="label" htmlFor="prompt">
            Visual prompt <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id="prompt"
            className="field min-h-24 resize-y"
            value={state.prompt}
            onChange={(event) => update("prompt", event.target.value)}
            placeholder="Optional direction, e.g. make it playful, keep the same beat, use toy-like characters."
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="language">
              Language
            </label>
            <select id="language" className="field" value={state.language} onChange={(event) => update("language", event.target.value as Language)}>
              <option value="auto">Auto detect</option>
              <option value="en">English</option>
              <option value="zh">Chinese</option>
              <option value="hi">Hindi</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="pt">Portuguese</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="audioMode">
              Audio
            </label>
            <select id="audioMode" className="field" value={state.audioMode} onChange={(event) => update("audioMode", event.target.value as AudioMode)}>
              <option value="source">Use original video audio</option>
              <option value="tts">Generate TTS from script</option>
              <option value="none">No audio</option>
            </select>
          </div>
        </div>

        {state.audioMode === "tts" ? (
          <div>
            <label className="label" htmlFor="ttsVoice">
              TTS voice
            </label>
            <input
              id="ttsVoice"
              className="field"
              value={state.ttsVoice}
              onChange={(event) => update("ttsVoice", event.target.value)}
              placeholder="en-US-AriaNeural"
            />
            <p className="hint">Uses Edge TTS by default. MoneyPrinterTurbo-style Azure TTS V1 naming can be added later.</p>
          </div>
        ) : null}

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
            <option value="local">Local - Wan 2.2 TI2V-5B</option>
            <option value="budget">API key - Replicate Seedance 1.5 Pro</option>
            <option value="standard">API key - Replicate Seedance 2.0 Fast</option>
            <option value="premium">API key - Replicate Seedance 2.0</option>
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
              placeholder="python run_wan.py --input {input} --prompt {prompt} --output {output}"
            />
            <p className="hint">Required for local Run. Can include {"{input}"}, {"{keyframe}"}, {"{prompt}"}, {"{output}"}, and {"{index}"} placeholders.</p>
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
