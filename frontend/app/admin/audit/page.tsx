"use client";
import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, Badge, Spinner, Empty, SectionTitle } from "@/components/ui";
import { prettyDoc } from "@/lib/utils";

const ACTION_CLS: Record<string, string> = {
  override: "bg-red-100 text-red-700",
  config_change: "bg-violet-100 text-violet-700",
  create: "bg-green-100 text-green-700",
  status_change: "bg-sky-100 text-sky-700",
  reject: "bg-red-100 text-red-700",
  verify: "bg-emerald-100 text-emerald-700",
  committee_adjust: "bg-amber-100 text-amber-800",
  publish_results: "bg-navy text-white",
};

export default function AuditPage() {
  const [logs, setLogs] = useState<any[] | null>(null);
  const [entity, setEntity] = useState("");
  const load = () => api(`/audit${entity ? `?entity=${entity}` : ""}`).then(setLogs).catch(() => setLogs([]));
  useEffect(() => { load(); }, [entity]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionTitle sub="Immutable, append-only record of every status change, AI override and config change.">
          Audit Log
        </SectionTitle>
        <select className="input w-auto" value={entity} onChange={(e) => setEntity(e.target.value)}>
          <option value="">All entities</option>
          {["application", "scheme", "ai_flag", "merit_score", "fellowship", "grievance"].map((x) => <option key={x} value={x}>{prettyDoc(x)}</option>)}
        </select>
      </div>
      {!logs ? <Spinner /> : logs.length === 0 ? <Card><Empty>No audit entries.</Empty></Card> : (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-left">
                <tr><th className="p-3">When</th><th className="p-3">Actor</th><th className="p-3">Entity</th><th className="p-3">Action</th><th className="p-3">Change</th></tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id} className="border-t border-slate-100 align-top">
                    <td className="p-3 text-xs text-slate-400 whitespace-nowrap">{new Date(l.at).toLocaleString()}</td>
                    <td className="p-3 text-xs">{l.actor_role}{l.actor_id ? ` #${l.actor_id}` : ""}</td>
                    <td className="p-3 text-xs">{prettyDoc(l.entity)}{l.entity_id ? ` #${l.entity_id}` : ""}</td>
                    <td className="p-3"><Badge className={ACTION_CLS[l.action] || "bg-slate-100 text-slate-600"}>{l.action}</Badge></td>
                    <td className="p-3 text-xs text-slate-500 max-w-md">
                      {l.before && <div>from: <code className="text-[11px]">{JSON.stringify(l.before)}</code></div>}
                      {l.after && <div>to: <code className="text-[11px]">{JSON.stringify(l.after)}</code></div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
