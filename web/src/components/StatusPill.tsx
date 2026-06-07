import type { ReactNode } from "react";
import { classNames } from "../lib";

const toneClass = {
  good: "border-green-200 bg-green-50 text-success",
  warn: "border-orange-200 bg-orange-50 text-warning",
  bad: "border-red-200 bg-red-50 text-danger",
  neutral: "border-line bg-white text-muted",
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
