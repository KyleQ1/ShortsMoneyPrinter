import { useEffect, useMemo, useRef, useState } from "react";
import { createPlan, getModels, getPreflight, getRun, getStyles, listRuns, saveStyle, startRun } from "./api";
import { EnvironmentStatus } from "./components/EnvironmentStatus";
import { Header } from "./components/Header";
import { OutputPreview } from "./components/OutputPreview";
import { PlanSummary } from "./components/PlanSummary";
import { ProgressLog } from "./components/ProgressLog";
import { RecentRuns } from "./components/RecentRuns";
import { requestFingerprint, RunForm, toRequest, type RunFormState } from "./components/RunForm";
import { StyleManager } from "./components/StyleManager";
import { canonicalQuality, defaultQualityForMode, isLocalQuality } from "./modelInfo";
import { classNames, money, parseUsd } from "./lib";
import type { ModelInfo, PreflightStatus, RunPlan, StyleOption } from "./types";

const defaultForm: RunFormState = {
  source: "",
  style: "nursery-3d",
  prompt: "",
  language: "auto",
  audioMode: "source",
  quality: "local",
  maxCost: "$10.00 USD",
  maxSeconds: "",
  captions: false,
  captionPosition: "bottom",
  localCommand: "",
  resolution: "480p",
  aspectRatio: "auto",
  advanced: false,
  promptEnhance: false,
  promptApiKey: "",
  promptModel: "gpt-4o-mini",
  imageUpload: null,
  audioUpload: null,
  videoUpload: null,
  sourceDuration: null,
};

const savedSettingsKey = "shorts_money_printer_run_settings";

function loadSavedForm(): RunFormState {
  try {
    const raw = localStorage.getItem(savedSettingsKey);
    if (!raw) return defaultForm;
    const saved = JSON.parse(raw) as Partial<RunFormState>;
    return {
      ...defaultForm,
      style: saved.style || defaultForm.style,
      language: saved.language || defaultForm.language,
      audioMode: saved.audioMode === "upload" || saved.audioMode === "none" ? saved.audioMode : defaultForm.audioMode,
      quality: saved.quality || defaultForm.quality,
      maxCost: saved.maxCost || defaultForm.maxCost,
      maxSeconds: saved.maxSeconds || defaultForm.maxSeconds,
      captions: saved.captions ?? defaultForm.captions,
      captionPosition: saved.captionPosition || defaultForm.captionPosition,
      localCommand: saved.localCommand || defaultForm.localCommand,
      resolution: saved.resolution || defaultForm.resolution,
      aspectRatio: saved.aspectRatio || defaultForm.aspectRatio,
      advanced: saved.advanced ?? defaultForm.advanced,
    };
  } catch {
    return defaultForm;
  }
}

function usdInput(value: number | null | undefined, fallback: string): string {
  return typeof value === "number" && value > 0 ? `$${value.toFixed(2)} USD` : fallback;
}

function formFromRun(run: RunPlan, fallbackMaxCost: string): RunFormState {
  const limitedDuration = run.original_duration > 0 && run.duration < run.original_duration - 0.25;
  const isImage = Boolean(run.is_image_to_video);
  const audioMode = run.audio_mode === "upload" || run.audio_mode === "none" ? run.audio_mode : "source";
  return {
    source: run.source,
    style: run.style,
    prompt: run.user_prompt || "",
    language: run.language,
    audioMode,
    quality: run.quality,
    maxCost: usdInput(run.max_cost, fallbackMaxCost),
    maxSeconds: limitedDuration ? String(Math.round(run.duration)) : "",
    captions: run.captions,
    captionPosition: run.caption_position,
    localCommand: run.local_command || "",
    resolution: run.resolution || defaultForm.resolution,
    aspectRatio: run.aspect_ratio || defaultForm.aspectRatio,
    advanced: isImage || audioMode === "upload" || Boolean(run.aspect_ratio),
    imageUpload: isImage
      ? { id: run.run_id, kind: "image", name: run.source_title || "image", path: run.source_path, url: `/api/runs/${run.run_id}/source.mp4` }
      : null,
    audioUpload: audioMode === "upload" && run.audio_path
      ? { id: run.run_id, kind: "audio", name: "uploaded audio", path: run.audio_path, url: run.audio_path }
      : null,
    videoUpload: null,
    sourceDuration: isImage ? null : run.original_duration,
    promptEnhance: false,
    promptApiKey: "",
    promptModel: defaultForm.promptModel,
  };
}

export default function App() {
  const [form, setForm] = useState(loadSavedForm);
  const [styles, setStyles] = useState<StyleOption[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [preflight, setPreflight] = useState<PreflightStatus | null>(null);
  const [runs, setRuns] = useState<RunPlan[]>([]);
  const [plan, setPlan] = useState<RunPlan | null>(null);
  const [tab, setTab] = useState<"plan" | "runs">("plan");
  const [styleManagerOpen, setStyleManagerOpen] = useState(false);
  const [sourceInvalid, setSourceInvalid] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [running, setRunning] = useState(false);
  const [activityLabel, setActivityLabel] = useState("");
  const [logLines, setLogLines] = useState<string[]>(["ready"]);
  const currentFingerprint = useRef<string | null>(null);
  const planSeq = useRef(0);
  const eventSource = useRef<EventSource | null>(null);

  const maxCost = useMemo(() => parseUsd(form.maxCost), [form.maxCost]);
  const planReady = useMemo(() => {
    if (!plan) return false;
    return currentFingerprint.current === requestFingerprint(toRequest(form));
  }, [form, plan]);

  function log(line: string) {
    setLogLines((current) => [...current.slice(-120), `${new Date().toLocaleTimeString()}  ${line}`]);
  }

  async function refreshRuns() {
    try {
      setRuns(await listRuns());
    } catch (error) {
      log(error instanceof Error ? error.message : "Could not load recent runs.");
    }
  }

  async function refreshStyles() {
    try {
      const items = await getStyles();
      setStyles(items);
      setForm((current) => {
        const selected = items.find((item) => item.key === current.style);
        if (selected) {
          return current.prompt.trim() ? current : { ...current, prompt: selected.prompt };
        }
        return { ...current, style: items[0]?.key || defaultForm.style, prompt: items[0]?.prompt || "" };
      });
    } catch (error) {
      log(error instanceof Error ? error.message : "Could not load styles.");
    }
  }

  useEffect(() => {
    void refreshStyles();
    getModels()
      .then((items) => {
        setModels(items);
        setForm((current) => {
          const canonical = canonicalQuality(items, current.quality);
          if (canonical) return { ...current, quality: canonical };
          return { ...current, quality: defaultQualityForMode(items, "local") };
        });
      })
      .catch((error) => log(error instanceof Error ? error.message : "Could not load models."));
    getPreflight()
      .then(setPreflight)
      .catch(() => log("Preflight unavailable."));
    void refreshRuns();

    return () => {
      eventSource.current?.close();
    };
  }, []);

  function validateInputs(manual: boolean): boolean {
    if (!form.source.trim() && !(form.advanced && form.imageUpload?.path)) {
      if (manual) {
        setSourceInvalid(true);
        log("Source video is required unless advanced image-to-video is using an uploaded image.");
      }
      return false;
    }
    setSourceInvalid(false);
    if (form.maxSeconds && Number(form.maxSeconds) <= 0) {
      if (manual) log("Max seconds must be greater than 0, or blank for the full source.");
      return false;
    }
    return true;
  }

  async function makePlan(manual: boolean): Promise<RunPlan | null> {
    if (!validateInputs(manual)) return null;
    setTab("plan");
    const body = toRequest(form);
    const fingerprint = requestFingerprint(body);
    if (plan && currentFingerprint.current === fingerprint) return plan;

    const seq = ++planSeq.current;
    setPlanning(true);
    setActivityLabel("Planning");
    if (manual) log("planning");

    try {
      const nextPlan = await createPlan(body);
      if (seq !== planSeq.current) return nextPlan;
      currentFingerprint.current = fingerprint;
      setPlan(nextPlan);
      setForm((current) => (
        nextPlan.is_image_to_video
          ? current
          : { ...current, sourceDuration: nextPlan.original_duration || current.sourceDuration || null }
      ));
      setActivityLabel("Plan ready");
      log(`planned ${nextPlan.run_id} · estimated ${money(nextPlan.estimated_cost)}`);
      void refreshRuns();
      return nextPlan;
    } catch (error) {
      if (seq === planSeq.current) setActivityLabel("Plan failed");
      log(error instanceof Error ? error.message : "Plan failed.");
      return null;
    } finally {
      if (seq === planSeq.current) setPlanning(false);
    }
  }

  function watch(runId: string) {
    eventSource.current?.close();
    const source = new EventSource(`/api/runs/${runId}/events`);
    eventSource.current = source;
    source.onmessage = (event) => {
      const nextPlan = JSON.parse(event.data) as RunPlan;
      setPlan(nextPlan);
      const complete = nextPlan.blocks.filter((block) => block.status === "done" || block.status === "skipped").length;
      log(`${nextPlan.status}: ${complete}/${nextPlan.block_count} blocks complete`);
      if (nextPlan.status === "done" || nextPlan.status === "failed") {
        if (nextPlan.status === "failed" && nextPlan.error) log(`run failed: ${nextPlan.error}`);
        setRunning(false);
        source.close();
        void refreshRuns();
      }
    };
    source.onerror = () => {
      log("Progress stream disconnected.");
      setRunning(false);
      source.close();
    };
  }

  async function runLive() {
    setTab("plan");
    if (!validateInputs(true)) return;
    if (maxCost <= 0) {
      log("Max cost must be greater than $0.00 USD before Run.");
      return;
    }

    const fingerprint = requestFingerprint(toRequest(form));
    if (!plan || currentFingerprint.current !== fingerprint) {
      setActivityLabel("Plan required");
      log("Click Plan before Run. Re-plan after changing settings.");
      return;
    }
    if (plan.estimated_cost > maxCost) {
      log(`Stopped before provider call: estimated ${money(plan.estimated_cost)} exceeds your max cost of ${money(maxCost)} USD.`);
      return;
    }
    if (!window.confirm(`Run can spend up to ${money(maxCost)} USD. Estimated cost is ${money(plan.estimated_cost)}. Continue with live generation?`)) {
      log("cancelled before provider call");
      return;
    }

    setRunning(true);
    setActivityLabel("Starting run");
    log(`starting live generation for ${plan.run_id}`);
    try {
      await startRun(plan.run_id, maxCost);
      setActivityLabel("Run started");
      log("live generation started");
      watch(plan.run_id);
    } catch (error) {
      log(error instanceof Error ? error.message : "Run failed to start.");
      setRunning(false);
    }
  }

  async function loadExistingRun(runId: string) {
    try {
      const loaded = await getRun(runId);
      const loadedForm = formFromRun(loaded, form.maxCost);
      setPlan(loaded);
      setForm(loadedForm);
      currentFingerprint.current = requestFingerprint(toRequest(loadedForm));
      setActivityLabel("Run loaded");
      log(`loaded ${runId} settings`);
    } catch (error) {
      log(error instanceof Error ? error.message : "Could not load run.");
    }
  }

  function updateForm(next: RunFormState) {
    const cleaned = isLocalQuality(models, next.quality) ? next : { ...next, localCommand: "" };
    setForm(cleaned);
    localStorage.setItem(
      savedSettingsKey,
      JSON.stringify({
        style: cleaned.style,
        language: cleaned.language,
        audioMode: cleaned.audioMode,
        quality: cleaned.quality,
        maxCost: cleaned.maxCost,
        maxSeconds: cleaned.maxSeconds,
        captions: cleaned.captions,
        captionPosition: cleaned.captionPosition,
        localCommand: cleaned.localCommand,
        resolution: cleaned.resolution,
        aspectRatio: cleaned.aspectRatio,
        advanced: cleaned.advanced,
      }),
    );
    if (next.source.trim() || next.imageUpload?.path) setSourceInvalid(false);
  }

  async function addStyleFromPrompt(label: string, prompt: string) {
    const saved = await saveStyle({
      label,
      prompt,
      match_reference: true,
      kids: false,
    });
    await refreshStyles();
    setForm((current) => ({ ...current, style: saved.key, prompt: saved.prompt }));
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto grid max-w-7xl gap-5 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(340px,440px)_minmax(0,1fr)]">
        <div className="grid content-start gap-5 lg:sticky lg:top-[72px] lg:self-start">
          <RunForm
            state={form}
            styles={styles}
            models={models}
            sourceInvalid={sourceInvalid}
            planning={planning}
            running={running}
            planReady={planReady}
            onChange={updateForm}
            onManageStyles={() => setStyleManagerOpen(true)}
            onAddStyle={addStyleFromPrompt}
            onPlan={() => void makePlan(true)}
            onRun={() => void runLive()}
          />
          <EnvironmentStatus status={preflight} />
        </div>
        <div className="grid content-start gap-5">
          <div className="inline-flex w-fit gap-1 rounded-xl border border-line bg-surface/70 p-1 backdrop-blur-xl">
            {([
              ["plan", "Plan & Run"],
              ["runs", `Recent Runs${runs.length ? ` (${runs.length})` : ""}`],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={classNames(
                  "min-h-9 rounded-lg px-4 py-1.5 text-sm font-bold transition",
                  tab === key ? "bg-accent-gradient text-white shadow-glow-soft" : "text-muted hover:text-ink",
                )}
                onClick={() => setTab(key)}
              >
                {label}
              </button>
            ))}
          </div>
          {tab === "plan" ? (
            <div className="grid content-start gap-5 animate-fade-in">
              <PlanSummary plan={plan} maxCost={maxCost} planning={planning} activityLabel={activityLabel} />
              <OutputPreview plan={plan} />
              <ProgressLog lines={logLines} />
            </div>
          ) : (
            <div className="animate-fade-in">
              <RecentRuns
                runs={runs}
                onRefresh={() => void refreshRuns()}
                onSelect={(runId) => {
                  void loadExistingRun(runId);
                  setTab("plan");
                }}
              />
            </div>
          )}
        </div>
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-10 pt-2 text-center text-xs text-faint sm:px-6">
        ShortsMoneyPrinter · local-first AI video remix · MIT licensed
      </footer>
      {styleManagerOpen ? (
        <StyleManager
          styles={styles}
          defaultStyle={defaultForm.style}
          onClose={() => setStyleManagerOpen(false)}
          onChanged={(nextStyles) => {
            if (nextStyles) {
              setStyles(nextStyles);
            } else {
              void refreshStyles();
            }
          }}
        />
      ) : null}
    </div>
  );
}
