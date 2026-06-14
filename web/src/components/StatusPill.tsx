import type { ReactNode } from "react";
import { classNames } from "../lib";

const toneClass = {
  good: "border-success/30 bg-success/10 text-success",
  warn: "border-warning/30 bg-warning/10 text-warning",
  bad: "border-danger/30 bg-danger/10 text-danger",
  neutral: "border-line bg-surface-2/80 text-muted",
};

export function StatusPill({
  children,
  tone = "neutral",
  className,
  title,
}: {
  children: ReactNode;
  tone?: keyof typeof toneClass;
  className?: string;
  title?: string;
}) {
  return (
    <span className={classNames("pill", toneClass[tone], className)} title={title}>
      {children}
    </span>
  );
}

export function statusTone(status: string): keyof typeof toneClass {
  if (status === "done" || status === "skipped") return "good";
  if (status === "failed") return "bad";
  if (status === "running" || status === "generating") return "warn";
  return "neutral";
}
