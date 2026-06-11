import { useEffect, useMemo, useRef, useState } from "react";
import { createPlan, getPreflight, getRun, getStyles, listRuns, startRun } from "./api";
import { EnvironmentStatus } from "./components/EnvironmentStatus";
import { Header } from "./components/Header";
import { OutputPreview } from "./components/OutputPreview";
import { PlanSummary } from "./components/PlanSummary";
import { ProgressLog } from "./components/ProgressLog";
import { RecentRuns } from "./components/RecentRuns";
import { requestFingerprint, RunForm, toRequest, type RunFormState } from "./components/RunForm";
import { money, parseUsd } from "./lib";
import type { PreflightStatus, RunPlan, StyleOption } from "./types";

const defaultForm: RunFormState = {
  source: "",
  style: "nursery-3d",
  prompt: "",
  videoSubjectPrompt: "",
  videoScriptPrompt: "",
  language: "auto",
  audioMode: "source",
  ttsVoice: "",
  quality: "local",
  maxCost: "$10.00 USD",
  maxSeconds: "",
  captions: false,
  wanCommand: "",
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
      audioMode: saved.audioMode || defaultForm.audioMode,
      ttsVoice: saved.ttsVoice || defaultForm.ttsVoice,
      quality: saved.quality || defaultForm.quality,
      maxCost: saved.maxCost || defaultForm.maxCost,
      maxSeconds: saved.maxSeconds || defaultForm.maxSeconds,
      captions: saved.captions ?? defaultForm.captions,
      wanCommand: saved.wanCommand || defaultForm.wanCommand,
    };
  } catch {
    return defaultForm;
  }
}

export default function App() {
  const [form, setForm] = useState(loadSavedForm);
  const [styles, setStyles] = useState<StyleOption[]>([]);
  const [preflight, setPreflight] = useState<PreflightStatus | null>(null);
  const [runs, setRuns] = useState<RunPlan[]>([]);
  const [plan, setPlan] = useState<RunPlan | null>(null);
  const [sourceInvalid, setSourceInvalid] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [running, setRunning] = useState(false);
  const [activityLabel, setActivityLabel] = useState("");
  const [logLines, setLogLines] = useState<string[]>(["ready"]);
  const currentFingerprint = useRef<string | null>(null);
  const planSeq = useRef(0);
  const eventSource = useRef<EventSource | null>(null);

  const maxCost = useMemo(() => parseUsd(form.maxCost), [form.maxCost]);

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

  useEffect(() => {
    getStyles()
      .then((items) => {
        setStyles(items);
        if (items.length && !items.some((item) => item.key === defaultForm.style)) {
          setForm((current) => ({ ...current, style: items[0].key }));
        }
      })
      .catch((error) => log(error instanceof Error ? error.message : "Could not load styles."));
    getPreflight()
      .then(setPreflight)
      .catch(() => log("Preflight unavailable."));
    void refreshRuns();

    return () => {
      eventSource.current?.close();
    };
  }, []);

  useEffect(() => {
    if (!form.source.trim()) return;
    const timer = window.setTimeout(() => {
      void makePlan(false);
    }, 900);
    return () => window.clearTimeout(timer);
  }, [
    form.source,
    form.style,
    form.prompt,
    form.videoSubjectPrompt,
    form.videoScriptPrompt,
    form.language,
    form.audioMode,
    form.ttsVoice,
    form.quality,
    form.maxSeconds,
    form.captions,
    form.wanCommand,
  ]);

  function validateInputs(manual: boolean): boolean {
    if (!form.source.trim()) {
      if (manual) {
        setSourceInvalid(true);
        log("Source video is required.");
      }
      return false;
    }
    setSourceInvalid(false);
    if (form.maxSeconds && Number(form.maxSeconds) <= 0) {
      if (manual) log("Max seconds must be greater than 0, or blank for the full source.");
      return false;
    }
    if (form.audioMode === "tts" && !form.videoScriptPrompt.trim()) {
      if (manual) log("TTS audio needs a video script prompt.");
      return false;
    }
    return true;
  }

  async function makePlan(manual: boolean): Promise<RunPlan | null> {
    if (!validateInputs(manual)) return null;
    const body = toRequest(form);
    const fingerprint = requestFingerprint(body);
    if (plan && currentFingerprint.current === fingerprint) return plan;

    const seq = ++planSeq.current;
    setPlanning(true);
    setActivityLabel("Planning");
    if (manual) log("planning");
    else log("planning preview");

    try {
      const nextPlan = await createPlan(body);
      if (seq !== planSeq.current) return nextPlan;
      currentFingerprint.current = fingerprint;
      setPlan(nextPlan);
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
    if (!validateInputs(true)) return;
    if (maxCost <= 0) {
      log("Max cost must be greater than $0.00 USD before Run.");
      return;
    }

    setRunning(true);
    const nextPlan = await makePlan(false);
    if (!nextPlan) {
      setRunning(false);
      return;
    }
    if (nextPlan.estimated_cost > maxCost) {
      log(`Stopped before provider call: estimated ${money(nextPlan.estimated_cost)} exceeds your max cost of ${money(maxCost)} USD.`);
      setRunning(false);
      return;
    }
    if (!window.confirm(`Run can spend up to ${money(maxCost)} USD. Estimated cost is ${money(nextPlan.estimated_cost)}. Continue with live generation?`)) {
      log("cancelled before provider call");
      setRunning(false);
      return;
    }

    try {
      await startRun(nextPlan.run_id, maxCost);
      log("live generation started");
      watch(nextPlan.run_id);
    } catch (error) {
      log(error instanceof Error ? error.message : "Run failed to start.");
      setRunning(false);
    }
  }

  async function loadExistingRun(runId: string) {
    try {
      const loaded = await getRun(runId);
      setPlan(loaded);
      currentFingerprint.current = null;
      setActivityLabel("Run loaded");
      log(`loaded ${runId}`);
    } catch (error) {
      log(error instanceof Error ? error.message : "Could not load run.");
    }
  }

  function updateForm(next: RunFormState) {
    const cleaned = next.quality === "local" ? next : { ...next, wanCommand: "" };
    setForm(cleaned);
    localStorage.setItem(
      savedSettingsKey,
      JSON.stringify({
        style: cleaned.style,
        language: cleaned.language,
        audioMode: cleaned.audioMode,
        ttsVoice: cleaned.ttsVoice,
        quality: cleaned.quality,
        maxCost: cleaned.maxCost,
        maxSeconds: cleaned.maxSeconds,
        captions: cleaned.captions,
        wanCommand: cleaned.wanCommand,
      }),
    );
    if (next.source.trim()) setSourceInvalid(false);
  }

  return (
    <div className="min-h-screen bg-canvas">
      <Header />
      <main className="mx-auto grid max-w-7xl gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
        <div className="grid content-start gap-4">
          <RunForm
            state={form}
            styles={styles}
            sourceInvalid={sourceInvalid}
            planning={planning}
            running={running}
            onChange={updateForm}
            onPlan={() => void makePlan(true)}
            onRun={() => void runLive()}
          />
          <EnvironmentStatus status={preflight} />
        </div>
        <div className="grid content-start gap-4">
          <PlanSummary plan={plan} maxCost={maxCost} planning={planning} activityLabel={activityLabel} />
          <RecentRuns runs={runs} onRefresh={() => void refreshRuns()} onSelect={(runId) => void loadExistingRun(runId)} />
          <ProgressLog lines={logLines} />
          <OutputPreview plan={plan} />
        </div>
      </main>
    </div>
  );
}
