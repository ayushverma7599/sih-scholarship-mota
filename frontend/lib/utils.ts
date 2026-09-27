import clsx, { ClassValue } from "clsx";

export const cn = (...a: ClassValue[]) => clsx(a);

export function inr(n: number): string {
  return "₹" + (n ?? 0).toLocaleString("en-IN");
}

export const STATUS_META: Record<string, { label: string; cls: string }> = {
  DRAFT: { label: "Draft", cls: "bg-slate-100 text-slate-700" },
  SUBMITTED: { label: "Submitted", cls: "bg-sky-100 text-sky-800" },
  AUTO_VERIFIED: { label: "Auto-Verified", cls: "bg-cyan-100 text-cyan-800" },
  UNDER_SCRUTINY: { label: "Under Scrutiny", cls: "bg-amber-100 text-amber-800" },
  DEFICIENCY_RAISED: { label: "Deficiency Raised", cls: "bg-orange-100 text-orange-800" },
  RESUBMITTED: { label: "Resubmitted", cls: "bg-indigo-100 text-indigo-800" },
  SCREENED: { label: "Screened", cls: "bg-violet-100 text-violet-800" },
  SELECTED: { label: "Selected", cls: "bg-green-100 text-green-800" },
  REJECTED: { label: "Rejected", cls: "bg-red-100 text-red-700" },
  FELLOWSHIP_ACTIVE: { label: "Fellowship Active", cls: "bg-emerald-100 text-emerald-800" },
};

export const RISK_CLS: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-green-100 text-green-800",
};

export const SEVERITY_CLS: Record<string, string> = {
  high: "bg-red-100 text-red-700 border-red-200",
  medium: "bg-amber-100 text-amber-800 border-amber-200",
  low: "bg-slate-100 text-slate-700 border-slate-200",
};

export function prettyDoc(t?: string | null): string {
  if (!t) return "—";
  return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
