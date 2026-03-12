import React from "react";
import { clsx } from "clsx";

interface CardProps {
  title?: string;
  value?: string | number;
  children?: React.ReactNode;
  interactive?: boolean;
  className?: string;
  onClick?: () => void;
}

export function Card({ title, value, children, interactive, className, onClick }: CardProps) {
  return (
    <div 
        className={clsx("card", interactive && "interactive", className)}
        onClick={onClick}
    >
      {title && <div className="card-title">{title}</div>}
      {value !== undefined && <div className="card-value">{value}</div>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
