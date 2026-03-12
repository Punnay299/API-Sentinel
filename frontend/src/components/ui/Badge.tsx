import React from "react";
import { clsx } from "clsx";

interface BadgeProps {
  status: string;
  className?: string;
}

export function Badge({ status, className }: BadgeProps) {
  const norm = status.toLowerCase();
  
  let variant = "active";
  if (["zombie"].includes(norm)) variant = "zombie";
  if (["shadow"].includes(norm)) variant = "shadow";
  if (["deprecated", "medium", "warning"].includes(norm)) variant = "deprecated";
  if (["orphaned", "critical", "high"].includes(norm)) variant = "critical";

  return (
    <span className={clsx("badge", `badge-${variant}`, className)}>
      {status}
    </span>
  );
}
