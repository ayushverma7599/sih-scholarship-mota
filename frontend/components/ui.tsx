"use client";
import React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("card p-5", className)}>{children}</div>;
}

export function SectionTitle({ children, sub }: { children: React.ReactNode; sub?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-ink">{children}</h2>
      {sub && <p className="text-sm text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "accent" | "ghost" | "danger";
  loading?: boolean;
};
export function Button({ variant = "primary", loading, className, children, disabled, ...rest }: BtnProps) {
  const map = {
    primary: "btn-primary", accent: "btn-accent", ghost: "btn-ghost", danger: "btn-danger",
  } as const;
  return (
    <button className={cn(map[variant], className)} disabled={disabled || loading} {...rest}>
      {loading ? "…" : children}
    </button>
  );
}

export function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cn("badge", className)}>{children}</span>;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn("input", props.className)} />;
}
export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn("input", props.className)} />;
}
export function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return <label htmlFor={htmlFor} className="label">{children}</label>;
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><Label>{label}</Label>{children}</div>;
}

export function Modal({ open, onClose, title, children }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="card p-6 w-full max-w-lg max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl leading-none">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return <div className="flex items-center gap-2 text-slate-500 text-sm py-8 justify-center">
    <span className="animate-spin h-4 w-4 border-2 border-slate-300 border-t-navy rounded-full" />
    {label || "Loading…"}
  </div>;
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="text-center text-slate-400 text-sm py-10">{children}</div>;
}

export function StatCard({ label, value, hint, accent }: {
  label: string; value: React.ReactNode; hint?: string; accent?: string;
}) {
  return (
    <div className="card p-4">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={cn("text-2xl font-bold mt-1", accent || "text-ink")}>{value}</div>
      {hint && <div className="text-xs text-slate-400 mt-1">{hint}</div>}
    </div>
  );
}
