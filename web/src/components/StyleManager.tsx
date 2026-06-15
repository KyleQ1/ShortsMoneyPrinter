import { useEffect, useState } from "react";
import { deleteStyle, resetStyle, resetStyles, saveStyle } from "../api";
import { classNames } from "../lib";
import type { StyleInput, StyleOption } from "../types";

type StyleManagerProps = {
  styles: StyleOption[];
  defaultStyle: string;
  onClose: () => void;
  onChanged: (styles?: StyleOption[]) => void;
};

const emptyDraft: StyleInput = {
  label: "",
  prompt: "",
  match_reference: true,
  kids: false,
};

export function StyleManager({ styles, defaultStyle, onClose, onChanged }: StyleManagerProps) {
  const [draft, setDraft] = useState<StyleInput>(emptyDraft);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  function edit(style: StyleOption) {
    setSelectedKey(style.key);
    setDraft({
      key: style.key,
      label: style.label,
      prompt: style.prompt,
      match_reference: style.match_reference,
      kids: style.kids,
    });
    setMessage("");
  }

  function createNew() {
    setSelectedKey(null);
    setDraft(emptyDraft);
    setMessage("");
  }

  async function submit() {
    setSaving(true);
    setMessage("");
    try {
      await saveStyle({ ...draft, key: selectedKey || draft.key });
      setMessage("Style saved.");
      onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save style.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(style: StyleOption) {
    if (style.key === defaultStyle) {
      setMessage("The default style cannot be deleted.");
      return;
    }
    if (!window.confirm(`Delete ${style.label}?`)) return;
    await deleteStyle(style.key);
    if (selectedKey === style.key) createNew();
    onChanged();
  }

  async function resetOne(style: StyleOption) {
    await resetStyle(style.key);
    if (selectedKey === style.key) createNew();
    onChanged();
  }

  async function resetAll() {
    if (!window.confirm("Reset all styles to defaults? Custom styles and edits will be removed.")) return;
    const next = await resetStyles();
    createNew();
    onChanged(next);
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm">
      <section className="panel grid max-h-[90vh] w-full max-w-5xl gap-4 overflow-hidden">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-extrabold text-ink">Manage Styles</h2>
            <p className="mt-1 text-xs text-muted">Create, edit, hide, and reset prompt presets.</p>
          </div>
          <button className="btn-secondary min-h-9 px-3 py-1 text-xs" type="button" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="grid min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="min-h-0 overflow-auto rounded-xl border border-line">
            <div className="grid gap-px bg-line">
              {styles.map((style) => (
                <div className="grid gap-3 bg-surface p-3 sm:grid-cols-[minmax(0,1fr)_auto]" key={style.key}>
                  <button className="min-w-0 text-left" type="button" onClick={() => edit(style)}>
                    <span className="flex flex-wrap items-center gap-2">
                      <b className="text-sm text-ink">{style.label}</b>
                      {style.custom ? <Badge>custom</Badge> : <Badge>built-in</Badge>}
                      {style.overridden ? <Badge tone="accent">edited</Badge> : null}
                      {style.kids ? <Badge tone="accent">kids</Badge> : null}
                    </span>
                    <span className="mt-1 block max-h-10 overflow-hidden text-xs text-muted">{style.prompt || "No style prompt."}</span>
                  </button>
                  <div className="flex flex-wrap items-center gap-2">
                    <button className="btn-secondary min-h-8 px-3 py-1 text-xs" type="button" onClick={() => edit(style)}>
                      Edit
                    </button>
                    {style.overridden ? (
                      <button className="btn-secondary min-h-8 px-3 py-1 text-xs" type="button" onClick={() => void resetOne(style)}>
                        Reset
                      </button>
                    ) : null}
                    <button
                      className="btn-secondary min-h-8 px-3 py-1 text-xs"
                      disabled={style.key === defaultStyle}
                      type="button"
                      onClick={() => void remove(style)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid content-start gap-3 rounded-xl border border-line bg-surface-2/40 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-extrabold text-ink">{selectedKey ? "Edit Style" : "New Style"}</h3>
              <button className="text-xs font-bold text-accent" type="button" onClick={createNew}>
                New
              </button>
            </div>
            <div>
              <label className="label" htmlFor="styleLabel">Label</label>
              <input id="styleLabel" className="field" value={draft.label} onChange={(event) => setDraft((current) => ({ ...current, label: event.target.value }))} />
            </div>
            <div>
              <label className="label" htmlFor="stylePrompt">Prompt</label>
              <textarea
                id="stylePrompt"
                className="field min-h-40 resize-y"
                value={draft.prompt}
                onChange={(event) => setDraft((current) => ({ ...current, prompt: event.target.value }))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                className="h-4 w-4 accent-accent"
                checked={draft.match_reference}
                onChange={(event) => setDraft((current) => ({ ...current, match_reference: event.target.checked }))}
              />
              Match source motion and framing
            </label>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                className="h-4 w-4 accent-accent"
                checked={draft.kids}
                onChange={(event) => setDraft((current) => ({ ...current, kids: event.target.checked }))}
              />
              Kid-safe style
            </label>
            <button className="btn" disabled={saving || !draft.label.trim()} type="button" onClick={() => void submit()}>
              {saving ? "Saving..." : "Save Style"}
            </button>
            <button className="btn-secondary" type="button" onClick={() => void resetAll()}>
              Reset All To Defaults
            </button>
            {message ? <p className="text-xs text-muted">{message}</p> : null}
          </div>
        </div>
      </section>
    </div>
  );
}

function Badge({ children, tone = "neutral" }: { children: string; tone?: "neutral" | "accent" }) {
  return (
    <span
      className={classNames(
        "rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
        tone === "accent"
          ? "border-accent/40 bg-accent-soft/40 text-accent"
          : "border-line bg-surface-2 text-muted",
      )}
    >
      {children}
    </span>
  );
}
