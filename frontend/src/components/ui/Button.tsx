import React from "react";
import { clsx } from "clsx";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "critical" | "outline";
  icon?: React.ReactNode;
}

export function Button({ variant = "primary", icon, className, children, ...props }: ButtonProps) {
  return (
    <button
      className={clsx("btn", `btn-${variant}`, className)}
      {...props}
    >
      {icon && <span className="flex items-center">{icon}</span>}
      {children}
    </button>
  );
}
