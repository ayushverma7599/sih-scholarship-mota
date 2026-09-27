"use client";
import React from "react";
import { Check } from "lucide-react";
import { STATUS_META } from "@/lib/utils";

type Step = { stage: string; reached: boolean; at: string | null; current: boolean };

export default function Timeline({ steps }: { steps: Step[] }) {
  return (
    <ol className="relative">
      {steps.map((s, i) => {
        const meta = STATUS_META[s.stage] || { label: s.stage, cls: "" };
        const isRejected = s.stage === "REJECTED";
        return (
          <li key={i} className="flex gap-3 pb-5 last:pb-0 relative">
            {i < steps.length - 1 && (
              <span className="absolute left-[11px] top-6 bottom-0 w-0.5 bg-slate-200" />
            )}
            <span className={
              "z-10 mt-0.5 h-6 w-6 rounded-full flex items-center justify-center text-white shrink-0 " +
              (s.reached ? (isRejected ? "bg-red-500" : "bg-leaf") :
                s.current ? "bg-saffron" : "bg-slate-300")
            }>
              {s.reached ? <Check size={14} /> : <span className="h-2 w-2 rounded-full bg-white" />}
            </span>
            <div>
              <div className={"text-sm font-medium " + (s.reached || s.current ? "text-ink" : "text-slate-400")}>
                {meta.label}
              </div>
              {s.at && <div className="text-xs text-slate-400">{new Date(s.at).toLocaleString()}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
