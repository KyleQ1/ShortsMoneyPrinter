import type { FormEvent, ReactNode } from "react";
import { useRef, useState } from "react";
import { uploadFile } from "../api";
import {
  defaultQualityForMode,
  modelInfoMap,
  modelOptionsForMode,
  providerModeForQuality,
  type ProviderMode,
} from "../modelInfo";
import { classNames, formatSeconds, parseUsd } from "../lib";
import type {
  AudioMode,
  CaptionPosition,
  Language,
  ModelInfo,
  Quality,
  RemixRequest,
  StyleOption,
  UploadResult,
} from "../types";

export type RunFormState = {
  source: string;
  style: string;
  prompt: string;
  language: Language;
  audioMode: AudioMode;
  quality: Quality;
  maxCost: string;
  maxSeconds: string;
  captions: boolean;
  captionPosition: CaptionPosition;
  localCommand: string;
  resolution: string;
  aspectRatio: string;
  advanced: boolean;
  promptEnhance: boolean;
  promptApiKey: string;
  promptModel: string;
  imageUpload?: UploadResult | null;
  audioUpload?: UploadResult | null;
  videoUpload?: UploadResult | null;
  sourceDuration?: number | null;
};

type RunFormProps = {
  state: RunFormState;
  styles: StyleOption[];
  models: ModelInfo[];
  sourceInvalid: boolean;
  planning: boolean;
  running: boolean;
  planReady: boolean;
  onChange: (next: RunFormState) => void;
  onManageStyles: () => void;
  onAddStyle: (label: string, prompt: string) => Promise<void>;
  onPlan: () => void;
  onRun: () => void;
};

export function toRequest(state: RunFormState): RemixRequest {
  const hasAdvancedAudio = state.advanced && Boolean(state.audioUpload?.path);
  return {
    source: state.source.trim(),
    style: state.style,
    prompt: state.prompt.trim() || null,
    video_subject_prompt: null,
    video_script_prompt: null,
    language: state.language,
    audio_mode: hasAdvancedAudio ? "upload" : state.audioMode,
    tts_voice: null,
    quality: state.quality,
    max_cost: parseUsd(state.maxCost),
    captions: state.captions,
    caption_position: state.captionPosition,
    max_total_seconds: state.maxSeconds ? Number(state.maxSeconds) : state.imageUpload ? null : 60,
    local_command: state.localCommand.trim() || null,
    resolution: state.resolution || null,
    aspect_ratio: state.advanced && state.aspectRatio !== "auto" ? state.aspectRatio : null,
    image_path: state.advanced ? state.imageUpload?.path || null : null,
    audio_upload: hasAdvancedAudio ? state.audioUpload?.path || null : null,
    prompt_enhance: state.promptEnhance,
    prompt_api_key: state.promptEnhance ? state.promptApiKey.trim() || null : null,
    prompt_model: state.promptEnhance ? state.promptModel.trim() || null : null,
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
    caption_position: body.caption_position,
    max_total_seconds: body.max_total_seconds,
    local_command: body.local_command,
    resolution: body.resolution,
    aspect_ratio: body.aspect_ratio,
    image_path: body.image_path,
    audio_upload: body.audio_upload,
    prompt_enhance: body.prompt_enhance,
    prompt_api_key_present: Boolean(body.prompt_api_key),
    prompt_model: body.prompt_model,
  });
}

function Section({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="grid gap-3 border-t border-line/70 pt-5 first:border-t-0 first:pt-0">
      <div className="flex items-center gap-2">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-accent-soft/50 text-accent">{icon}</span>
        <span className="section-title">{title}</span>
      </div>
      {children}
    </div>
  );
}

const ICON = {
  film: (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" />
    </svg>
  ),
  wand: (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m15 4 .9 2.1L18 7l-2.1.9L15 10l-.9-2.1L12 7l2.1-.9zM4 14l6 6M14.5 9.5 4 20" />
    </svg>
  ),
  audio: (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 10v4M7 7v10M11 4v16M15 8v8M19 11v2" />
    </svg>
  ),
  sliders: (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h7M15 18h5M14 4v4M6 10v4M11 16v4" />
    </svg>
  ),
  cpu: (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="6" y="6" width="12" height="12" rx="2" /><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3" />
    </svg>
  ),
};

export function RunForm({
  state,
  styles,
  models,
  sourceInvalid,
  planning,
  running,
  planReady,
  onChange,
  onManageStyles,
  onAddStyle,
  onPlan,
  onRun,
}: RunFormProps) {
  const model = modelInfoMap(models)[state.quality] || models[0];
  const providerMode = providerModeForQuality(models, state.quality);
  const visibleModelOptions = modelOptionsForMode(models, providerMode);
  const busy = planning || running;
  const [uploading, setUploading] = useState<"video" | "image" | "audio" | null>(null);
  const [addingStyle, setAddingStyle] = useState(false);
  const [newStyleTitle, setNewStyleTitle] = useState("");
  const [styleSaveMessage, setStyleSaveMessage] = useState("");
  const [savingStyle, setSavingStyle] = useState(false);
  const autoPromptRef = useRef<string>("");
  const currentStyle = styles.find((style) => style.key === state.style);
  const promptChangedFromStyle = Boolean(state.prompt.trim()) && state.prompt !== (currentStyle?.prompt || "");

  function update(next: Partial<RunFormState>) {
    onChange({ ...state, ...next });
  }

  function updateProviderMode(nextMode: ProviderMode) {
    if (nextMode === providerMode) return;
    update({ quality: defaultQualityForMode(models, nextMode) });
  }

  function updateStyle(styleKey: string) {
    const currentStyle = styles.find((style) => style.key === state.style);
    const nextStyle = styles.find((style) => style.key === styleKey);
    const canAutofill =
      !state.prompt.trim()
      || state.prompt === currentStyle?.prompt
      || state.prompt === autoPromptRef.current;
    const nextPrompt = canAutofill ? nextStyle?.prompt || "" : state.prompt;
    if (canAutofill) autoPromptRef.current = nextPrompt;
    update({ style: styleKey, prompt: nextPrompt });
  }

  async function handleUpload(kind: "video" | "image" | "audio", file: File | undefined) {
    if (!file) return;
    setUploading(kind);
    try {
      const sourceDuration = kind === "video" ? await readVideoDuration(file) : state.sourceDuration;
      const uploaded = await uploadFile(kind, file);
      if (kind === "video") update({ source: uploaded.path, videoUpload: uploaded, sourceDuration });
      if (kind === "image") update({ advanced: true, imageUpload: uploaded });
      if (kind === "audio") update({ advanced: true, audioUpload: uploaded, audioMode: "upload" });
    } finally {
      setUploading(null);
    }
  }

  async function savePromptAsStyle() {
    if (!state.prompt.trim() || !newStyleTitle.trim()) return;
    setSavingStyle(true);
    setStyleSaveMessage("");
    try {
      await onAddStyle(newStyleTitle.trim(), state.prompt.trim());
      setAddingStyle(false);
      setNewStyleTitle("");
      setStyleSaveMessage("New style added.");
    } catch (error) {
      setStyleSaveMessage(error instanceof Error ? error.message : "Could not add style.");
    } finally {
      setSavingStyle(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    onPlan();
  }

  const knownSourceDuration = state.sourceDuration && Number.isFinite(state.sourceDuration) && state.sourceDuration > 0
    ? state.sourceDuration
    : null;
  const videoDurationMax = knownSourceDuration ? Math.max(1, Math.ceil(Math.min(60, knownSourceDuration))) : 60;
  const imageDefaultDuration = 5;
  const imageDurationMax = 15;
  const durationMax = state.imageUpload ? imageDurationMax : videoDurationMax;
  const durationDefault = state.imageUpload ? imageDefaultDuration : durationMax;
  const explicitDuration = state.maxSeconds ? Math.max(1, Math.min(durationMax, Number(state.maxSeconds))) : null;
  const durationValue = explicitDuration || durationDefault;
  const durationLabel = explicitDuration
    ? formatSeconds(explicitDuration)
    : state.imageUpload
      ? "Default image duration"
      : knownSourceDuration
        ? knownSourceDuration <= 60
          ? `Full source (${formatSeconds(knownSourceDuration)})`
          : "60s max"
        : "Full source, max 60s";

  return (
    <section className="panel animate-fade-up">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-extrabold tracking-tight text-ink">Create a Short</h2>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-line bg-surface-2/80 px-2.5 py-1 text-xs font-semibold text-muted">
          <input
            type="checkbox"
            className="h-4 w-4 accent-accent"
            checked={state.advanced}
            onChange={(event) => update({ advanced: event.target.checked })}
          />
          Advanced
        </label>
      </div>

      <form className="mt-5 space-y-5" onSubmit={submit}>
        <Section icon={ICON.film} title="Source">
          <div>
            <label className="label" htmlFor="source">Source video</label>
            <input
              id="source"
              className={classNames("field", sourceInvalid && "field-invalid")}
              value={state.source}
              onChange={(event) => update({ source: event.target.value, videoUpload: null, sourceDuration: null })}
              placeholder="https://youtube.com/…  or  /path/to/video.mp4"
              aria-invalid={sourceInvalid}
            />
            <p className="hint">Public YouTube, Instagram, or TikTok URL — or a local MP4 path on this machine.</p>
          </div>
          {state.advanced ? (
            <UploadButton
              kind="video"
              label="Upload source video"
              accept="video/*"
              uploading={uploading === "video"}
              upload={state.videoUpload}
              onUpload={handleUpload}
              onClear={() => update({ videoUpload: null, source: "", sourceDuration: null })}
            />
          ) : null}
        </Section>

        <Section icon={ICON.cpu} title="Engine">
          <div>
            <span className="label">Generation</span>
            <div className="mt-1.5 grid grid-cols-2 gap-1 rounded-lg border border-line bg-surface-2/60 p-1">
              {(["local", "remote"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={classNames(
                    "min-h-9 rounded-md px-3 text-sm font-bold transition",
                    providerMode === mode ? "bg-accent-gradient text-white shadow-glow-soft" : "text-muted hover:text-ink",
                  )}
                  onClick={() => updateProviderMode(mode)}
                >
                  {mode === "local" ? "Local · free" : "Cloud · BYO key"}
                </button>
              ))}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="quality">{providerMode === "local" ? "Local model" : "Remote model"}</label>
              <select id="quality" className="field" value={state.quality} onChange={(event) => update({ quality: event.target.value as Quality })}>
                {visibleModelOptions.map((option) => (
                  <option key={option.quality} value={option.quality}>
                    {option.label}{option.recommended ? " — Recommended" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="resolution">Resolution</label>
              <select id="resolution" className="field" value={state.resolution} onChange={(event) => update({ resolution: event.target.value })}>
                <option value="480p">480p</option>
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
              </select>
            </div>
          </div>
          <div className="rounded-xl border border-line bg-surface-2/40 p-3.5">
            <div className="flex items-center gap-2">
              <b className="text-sm text-ink">{model?.title || "Model loading"}</b>
              {model?.recommended ? (
                <span className="rounded-full border border-accent/40 bg-accent-soft/50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent">Recommended</span>
              ) : null}
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted">{model?.detail || "Loading model catalog."}</p>
            {model?.cost ? <p className="mt-2.5 text-xs font-semibold leading-relaxed text-accent">{model.cost}</p> : null}
          </div>
          {providerMode === "local" ? (
            <div>
              <label className="label" htmlFor="localCommand">Local command</label>
              <input
                id="localCommand"
                className="field font-mono text-xs"
                value={state.localCommand}
                onChange={(event) => update({ localCommand: event.target.value })}
                placeholder="python run_ltx.py --input {input} --prompt {prompt} --output {output}"
              />
              <p className="hint">Required for local Run. Placeholders: {"{input}"}, {"{keyframe}"}, {"{prompt}"}, {"{output}"}, {"{index}"}.</p>
            </div>
          ) : null}
        </Section>

        <Section icon={ICON.wand} title="Style & prompts">
          <div>
            <div className="flex items-center justify-between gap-3">
              <label className="label" htmlFor="style">Style</label>
              <button className="btn-secondary min-h-8 px-3 py-1 text-xs" type="button" onClick={onManageStyles}>Manage styles</button>
            </div>
            <select id="style" className="field" value={state.style} onChange={(event) => updateStyle(event.target.value)}>
              {styles.map((style) => (
                <option key={style.key} value={style.key}>
                  {style.label}{style.overridden ? " — edited" : style.custom ? " — custom" : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <div className="flex items-center justify-between gap-3">
              <label className="label" htmlFor="prompt">Visual prompt <span className="font-normal text-faint">· optional</span></label>
              {promptChangedFromStyle ? (
                <button
                  className="text-xs font-bold text-accent hover:text-accent-strong"
                  type="button"
                  onClick={() => {
                    setAddingStyle((current) => !current);
                    setStyleSaveMessage("");
                  }}
                >
                  Add a new one
                </button>
              ) : null}
            </div>
            <textarea
              id="prompt"
              className="field min-h-20 resize-y"
              value={state.prompt}
              onChange={(event) => {
                update({ prompt: event.target.value });
                setStyleSaveMessage("");
              }}
              placeholder="Direction, e.g. make it playful, keep the same beat, toy-like characters."
            />
            {addingStyle ? (
              <div className="mt-3 rounded-xl border border-line bg-surface-2/40 p-3">
                <label className="label" htmlFor="newStyleTitle">New style title</label>
                <div className="mt-1.5 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                  <input
                    id="newStyleTitle"
                    className="field mt-0"
                    value={newStyleTitle}
                    onChange={(event) => setNewStyleTitle(event.target.value)}
                    placeholder="My cinematic cartoon style"
                  />
                  <button
                    className="btn min-h-10 px-3 py-1 text-xs"
                    disabled={savingStyle || !newStyleTitle.trim() || !state.prompt.trim()}
                    type="button"
                    onClick={() => void savePromptAsStyle()}
                  >
                    {savingStyle ? "Saving..." : "Save"}
                  </button>
                </div>
                <p className="hint">Saves the current visual prompt as a reusable style.</p>
              </div>
            ) : null}
            {styleSaveMessage ? <p className="mt-2 text-xs text-muted">{styleSaveMessage}</p> : null}
          </div>
          {state.advanced ? (
            <div className="rounded-xl border border-line bg-surface-2/40 p-3.5">
              <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-ink">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-accent"
                  checked={state.promptEnhance}
                  onChange={(event) => update({ promptEnhance: event.target.checked })}
                />
                AI prompt writer
              </label>
              {state.promptEnhance ? (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="label" htmlFor="promptApiKey">Prompt API key</label>
                    <input
                      id="promptApiKey"
                      className="field"
                      type="password"
                      autoComplete="off"
                      value={state.promptApiKey}
                      onChange={(event) => update({ promptApiKey: event.target.value })}
                      placeholder="Uses PROMPT_API_KEY if blank"
                    />
                  </div>
                  <div>
                    <label className="label" htmlFor="promptModel">Prompt model</label>
                    <input
                      id="promptModel"
                      className="field"
                      value={state.promptModel}
                      onChange={(event) => update({ promptModel: event.target.value })}
                      placeholder="gpt-4o-mini"
                    />
                  </div>
                  <p className="hint sm:col-span-2">Rewrites each block prompt during Plan. The key is not saved to browser settings or run files.</p>
                </div>
              ) : null}
            </div>
          ) : null}
        </Section>

        <Section icon={ICON.audio} title="Audio & language">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="language">Language</label>
              <select id="language" className="field" value={state.language} onChange={(event) => update({ language: event.target.value as Language })}>
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
              <label className="label" htmlFor="audioMode">Audio</label>
              <select id="audioMode" className="field" value={state.audioUpload ? "upload" : state.audioMode} onChange={(event) => update({ audioMode: event.target.value as AudioMode, audioUpload: null })}>
                <option value="source">Use original audio</option>
                <option value="upload">Use uploaded audio</option>
                <option value="none">No audio</option>
              </select>
            </div>
          </div>
          {state.advanced ? (
            <UploadButton
              kind="audio"
              label="Upload soundtrack"
              accept="audio/*"
              uploading={uploading === "audio"}
              upload={state.audioUpload}
              onUpload={handleUpload}
              onClear={() => update({ audioUpload: null, audioMode: "source" })}
            />
          ) : null}
        </Section>

        <Section icon={ICON.sliders} title="Output & limits">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="maxCost">Max cost (USD)</label>
              <input id="maxCost" className="field" inputMode="decimal" value={state.maxCost} onChange={(event) => update({ maxCost: event.target.value })} placeholder="$10.00 USD" />
              <p className="hint">Run stops before any provider call if the estimate is higher.</p>
            </div>
            <div>
              <div className="flex items-center justify-between gap-3">
                <label className="label" htmlFor="maxSeconds">Duration</label>
                <span className="text-xs font-bold text-accent">{durationLabel}</span>
              </div>
              <input
                id="maxSeconds"
                className="mt-3 w-full accent-accent"
                min="1"
                max={durationMax}
                step="1"
                type="range"
                value={durationValue}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  const isDefault = state.imageUpload ? value === imageDefaultDuration : value >= durationMax;
                  update({ maxSeconds: isDefault ? "" : String(value) });
                }}
              />
              <p className="hint">{state.imageUpload ? "Image-to-video can run 1-15 seconds; default is 5 seconds." : "Defaults to the full source when it is under 60 seconds, otherwise caps at 60 seconds."}</p>
            </div>
          </div>

          {state.advanced ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="aspectRatio">Aspect ratio</label>
                <select id="aspectRatio" className="field" value={state.aspectRatio} onChange={(event) => update({ aspectRatio: event.target.value })}>
                  <option value="auto">Auto from source</option>
                  <option value="9:16">9:16 vertical</option>
                  <option value="16:9">16:9 wide</option>
                  <option value="1:1">1:1 square</option>
                </select>
              </div>
              <UploadButton
                kind="image"
                label="Image-to-video still"
                accept="image/*"
                uploading={uploading === "image"}
                upload={state.imageUpload}
                onUpload={handleUpload}
                onClear={() => update({ imageUpload: null })}
              />
            </div>
          ) : null}

          {state.imageUpload ? (
            <div className="rounded-xl border border-accent/30 bg-accent-soft/20 p-3">
              <p className="text-xs font-bold text-accent">Image-to-video mode</p>
              <p className="mt-1 text-xs text-muted">The uploaded still overrides video input for planning and creates a single generated block.</p>
              <img className="mt-3 max-h-40 rounded-lg border border-line object-contain" src={state.imageUpload.url} alt="" />
            </div>
          ) : null}

          <label className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-line bg-surface-2/40 px-3 py-2.5 text-sm text-ink transition hover:border-line-strong">
            <input type="checkbox" checked={state.captions} onChange={(event) => update({ captions: event.target.checked })} className="h-4 w-4 rounded border-line-strong bg-surface-2 accent-accent focus:ring-accent" />
            <span className="flex-1">Burn-in captions</span>
            <span className="text-xs text-faint">Whisper + ffmpeg</span>
          </label>
          {state.captions ? (
            <div>
              <label className="label" htmlFor="captionPosition">Caption position</label>
              <select id="captionPosition" className="field" value={state.captionPosition} onChange={(event) => update({ captionPosition: event.target.value as CaptionPosition })}>
                <option value="bottom">Bottom</option>
                <option value="center">Center</option>
                <option value="top">Top</option>
              </select>
            </div>
          ) : null}
        </Section>

        <div className="sticky bottom-0 -mx-5 -mb-5 mt-1 rounded-b-2xl border-t border-line/70 bg-surface/90 px-5 py-4 backdrop-blur-xl">
          <div className="flex gap-3">
            <button className="btn-secondary flex-1" disabled={busy || Boolean(uploading)} type="submit">
              {planning ? <span className="inline-flex items-center gap-2"><Spinner /> Planning...</span> : "Plan"}
            </button>
            <button className="btn flex-1" disabled={busy || Boolean(uploading) || !planReady} type="button" onClick={onRun}>
              {running ? <span className="inline-flex items-center gap-2"><Spinner dark /> Running...</span> : planReady ? "Run" : "Plan first"}
            </button>
          </div>
          <p className="mt-2.5 flex items-center gap-1.5 text-xs text-muted">
            <span className={classNames("h-1.5 w-1.5 shrink-0 rounded-full", planReady ? "bg-success shadow-[0_0_8px_rgba(52,211,153,0.8)]" : "bg-faint")} />
            {planReady ? "Plan is ready; Run confirms cost before provider calls." : "Plan first for a free timeline and cost estimate."}
          </p>
        </div>
      </form>
    </section>
  );
}

function UploadButton({
  kind,
  label,
  accept,
  uploading,
  upload,
  onUpload,
  onClear,
}: {
  kind: "video" | "image" | "audio";
  label: string;
  accept: string;
  uploading: boolean;
  upload?: UploadResult | null;
  onUpload: (kind: "video" | "image" | "audio", file: File | undefined) => void;
  onClear: () => void;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface-2/40 p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-bold text-ink">{label}</span>
        {upload ? <button type="button" className="text-xs font-bold text-accent" onClick={onClear}>Clear</button> : null}
      </div>
      <label className="mt-2 flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-line-strong px-3 py-4 text-center text-xs font-semibold text-muted hover:border-accent hover:text-accent">
        <input
          className="sr-only"
          type="file"
          accept={accept}
          onChange={(event) => {
            void onUpload(kind, event.target.files?.[0]);
            event.currentTarget.value = "";
          }}
        />
        {uploading ? "Uploading..." : upload ? upload.name : "Choose file"}
      </label>
      {upload ? <p className="mt-2 truncate text-xs text-faint">{upload.path}</p> : null}
    </div>
  );
}

function Spinner({ dark = false }: { dark?: boolean }) {
  return (
    <span
      className={classNames(
        "h-3.5 w-3.5 animate-spin rounded-full border-2",
        dark ? "border-white/40 border-t-white" : "border-line border-t-accent",
      )}
    />
  );
}

function readVideoDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const video = document.createElement("video");
    const url = URL.createObjectURL(file);
    let settled = false;
    const done = (duration: number | null) => {
      if (settled) return;
      settled = true;
      URL.revokeObjectURL(url);
      video.removeAttribute("src");
      video.load();
      resolve(duration && Number.isFinite(duration) ? duration : null);
    };
    const timeout = window.setTimeout(() => done(null), 2500);
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      window.clearTimeout(timeout);
      done(video.duration);
    };
    video.onerror = () => {
      window.clearTimeout(timeout);
      done(null);
    };
    video.src = url;
  });
}
