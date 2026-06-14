import type { FormEvent, ReactNode } from "react";
import {
  defaultQualityForMode,
  modelInfoMap,
  modelOptionsForMode,
  providerModeForQuality,
  type ProviderMode,
} from "../modelInfo";
import type { AudioMode, CaptionPosition, Language, ModelInfo, Quality, RemixRequest, StyleOption } from "../types";
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
  captionPosition: CaptionPosition;
  localCommand: string;
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
    caption_position: state.captionPosition,
    max_total_seconds: state.maxSeconds ? Number(state.maxSeconds) : null,
    local_command: state.localCommand.trim() || null,
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
  onPlan,
  onRun,
}: RunFormProps) {
  const model = modelInfoMap(models)[state.quality] || models[0];
  const providerMode = providerModeForQuality(models, state.quality);
  const visibleModelOptions = modelOptionsForMode(models, providerMode);
  const busy = planning || running;

  function update<K extends keyof RunFormState>(key: K, value: RunFormState[K]) {
    onChange({ ...state, [key]: value });
  }

  function updateProviderMode(nextMode: ProviderMode) {
    if (nextMode === providerMode) return;
    onChange({ ...state, quality: defaultQualityForMode(models, nextMode) });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    onPlan();
  }

  return (
    <section className="panel animate-fade-up">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-extrabold tracking-tight text-ink">Create a Short</h2>
        <span className="pill">{providerMode === "local" ? "Local model" : "Cloud model"}</span>
      </div>

      <form className="mt-5 space-y-5" onSubmit={submit}>
        {/* SOURCE */}
        <Section icon={ICON.film} title="Source">
          <div>
            <label className="label" htmlFor="source">
              Source video
            </label>
            <input
              id="source"
              className={classNames("field", sourceInvalid && "field-invalid")}
              value={state.source}
              onChange={(event) => update("source", event.target.value)}
              placeholder="https://youtube.com/…  or  /path/to/video.mp4"
              aria-invalid={sourceInvalid}
            />
            <p className="hint">Public YouTube, Instagram, or TikTok URL — or a local MP4 path on this machine.</p>
          </div>
        </Section>

        {/* ENGINE */}
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
                    providerMode === mode ? "bg-accent-gradient text-night shadow-glow-soft" : "text-muted hover:text-ink",
                  )}
                  onClick={() => updateProviderMode(mode)}
                >
                  {mode === "local" ? "Local · free" : "Cloud · BYO key"}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="label" htmlFor="quality">
              {providerMode === "local" ? "Local model" : "Remote model"}
            </label>
            <select
              id="quality"
              className="field"
              value={state.quality}
              onChange={(event) => update("quality", event.target.value as Quality)}
            >
              {visibleModelOptions.map((option) => (
                <option key={option.quality} value={option.quality}>
                  {option.label}
                  {option.recommended ? " — Recommended" : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="rounded-xl border border-line bg-surface-2/40 p-3.5">
            <div className="flex items-center gap-2">
              <b className="text-sm text-ink">{model?.title || "Model loading"}</b>
              {model?.recommended ? (
                <span className="rounded-full border border-accent/40 bg-accent-soft/50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent">
                  Recommended
                </span>
              ) : null}
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted">{model?.detail || "Loading model catalog."}</p>
            {model?.cost ? (
              <p className="mt-2.5 flex items-start gap-1.5 text-xs font-semibold leading-relaxed text-accent">
                <svg viewBox="0 0 24 24" className="mt-0.5 h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                <span className="min-w-0">{model.cost}</span>
              </p>
            ) : null}
          </div>
          {providerMode === "local" ? (
            <div>
              <label className="label" htmlFor="localCommand">
                Local command
              </label>
              <input
                id="localCommand"
                className="field font-mono text-xs"
                value={state.localCommand}
                onChange={(event) => update("localCommand", event.target.value)}
                placeholder="python run_ltx.py --input {input} --prompt {prompt} --output {output}"
              />
              <p className="hint">
                Required for local Run. Placeholders: <code className="text-accent">{"{input}"}</code>{" "}
                <code className="text-accent">{"{keyframe}"}</code> <code className="text-accent">{"{prompt}"}</code>{" "}
                <code className="text-accent">{"{output}"}</code> <code className="text-accent">{"{index}"}</code>.
              </p>
            </div>
          ) : null}
        </Section>

        {/* STYLE & PROMPTS */}
        <Section icon={ICON.wand} title="Style & prompts">
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
              Video subject <span className="font-normal text-faint">· optional</span>
            </label>
            <textarea
              id="videoSubjectPrompt"
              className="field min-h-16 resize-y"
              value={state.videoSubjectPrompt}
              onChange={(event) => update("videoSubjectPrompt", event.target.value)}
              placeholder="Niche or subject, e.g. satisfying finance facts for Shorts."
            />
          </div>
          <div>
            <label className="label" htmlFor="videoScriptPrompt">
              Video script <span className="font-normal text-faint">· optional</span>
            </label>
            <textarea
              id="videoScriptPrompt"
              className="field min-h-20 resize-y"
              value={state.videoScriptPrompt}
              onChange={(event) => update("videoScriptPrompt", event.target.value)}
              placeholder="Narration / script direction. Required only when Audio is set to TTS."
            />
          </div>
          <div>
            <label className="label" htmlFor="prompt">
              Visual prompt <span className="font-normal text-faint">· optional</span>
            </label>
            <textarea
              id="prompt"
              className="field min-h-20 resize-y"
              value={state.prompt}
              onChange={(event) => update("prompt", event.target.value)}
              placeholder="Direction, e.g. make it playful, keep the same beat, toy-like characters."
            />
          </div>
        </Section>

        {/* AUDIO & LANGUAGE */}
        <Section icon={ICON.audio} title="Audio & language">
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
                <option value="source">Use original audio</option>
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
              <p className="hint">Uses Edge TTS by default.</p>
            </div>
          ) : null}
        </Section>

        {/* OUTPUT & LIMITS */}
        <Section icon={ICON.sliders} title="Output & limits">
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
              <p className="hint">Run stops before any provider call if the estimate is higher.</p>
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
              <p className="hint">Blank plans the full source.</p>
            </div>
          </div>

          <label className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-line bg-surface-2/40 px-3 py-2.5 text-sm text-ink transition hover:border-line-strong">
            <input
              type="checkbox"
              checked={state.captions}
              onChange={(event) => update("captions", event.target.checked)}
              className="h-4 w-4 rounded border-line-strong bg-surface-2 accent-accent focus:ring-accent"
            />
            <span className="flex-1">Burn-in captions</span>
            <span className="text-xs text-faint">Whisper + ffmpeg</span>
          </label>
          {state.captions ? (
            <div>
              <label className="label" htmlFor="captionPosition">
                Caption position
              </label>
              <select
                id="captionPosition"
                className="field"
                value={state.captionPosition}
                onChange={(event) => update("captionPosition", event.target.value as CaptionPosition)}
              >
                <option value="bottom">Bottom</option>
                <option value="center">Center</option>
                <option value="top">Top</option>
              </select>
            </div>
          ) : null}
        </Section>

        {/* ACTION BAR */}
        <div className="sticky bottom-0 -mx-5 -mb-5 mt-1 rounded-b-2xl border-t border-line/70 bg-surface/90 px-5 py-4 backdrop-blur-xl">
          <div className="flex gap-3">
            <button className="btn-secondary flex-1" disabled={busy} type="submit">
              {planning ? (
                <span className="inline-flex items-center gap-2">
                  <Spinner /> Planning…
                </span>
              ) : (
                "Plan"
              )}
            </button>
            <button className="btn flex-1" disabled={busy || !planReady} type="button" onClick={onRun}>
              {running ? (
                <span className="inline-flex items-center gap-2">
                  <Spinner dark /> Running…
                </span>
              ) : planReady ? (
                <span className="inline-flex items-center gap-2">
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M8 5.5v13a1 1 0 0 0 1.54.84l10-6.5a1 1 0 0 0 0-1.68l-10-6.5A1 1 0 0 0 8 5.5Z" /></svg>
                  Run
                </span>
              ) : (
                "Plan first"
              )}
            </button>
          </div>
          <p className="mt-2.5 flex items-center gap-1.5 text-xs text-muted">
            {planReady ? (
              <>
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                Plan is ready — Run confirms the cost before any provider call.
              </>
            ) : (
              <>
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-faint" />
                Plan first for a free dry-run timeline & cost estimate.
              </>
            )}
          </p>
        </div>
      </form>
    </section>
  );
}

function Spinner({ dark = false }: { dark?: boolean }) {
  return (
    <span
      className={classNames(
        "h-3.5 w-3.5 animate-spin rounded-full border-2",
        dark ? "border-night/40 border-t-night" : "border-line border-t-accent",
      )}
    />
  );
}
