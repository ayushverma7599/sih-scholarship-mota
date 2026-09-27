"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, Button, Badge, Spinner, Empty, SectionTitle } from "@/components/ui";
import { STATUS_META, RISK_CLS, inr } from "@/lib/utils";
import { Clock, AlertTriangle } from "lucide-react";

export default function OfficerQueue() {
  const router = useRouter();
  const [rows, setRows] = useState<any[] | null>(null);
  const [schemes, setSchemes] = useState<any[]>([]);
  const [filters, setFilters] = useState<{ scheme_id?: string; status?: string; min_risk?: string }>({});
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);

  const load = () => {
    const q = new URLSearchParams();
    if (filters.scheme_id) q.set("scheme_id", filters.scheme_id);
    if (filters.status) q.set("status", filters.status);
    if (filters.min_risk) q.set("min_risk", filters.min_risk);
    api(`/scrutiny/queue?${q}`).then(setRows).catch(() => setRows([]));
  };
  useEffect(() => { api("/schemes").then(setSchemes).catch(() => {}); }, []);
  useEffect(load, [filters]);

  const toggle = (id: number) => setSelected((s) => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n;
  });

  const bulkVerify = async () => {
    setBusy(true);
    try {
      const res = await api<{ verified: number[]; skipped: any[] }>("/scrutiny/bulk-verify", {
        method: "POST", body: { application_ids: Array.from(selected), note: "Bulk verified (clean)." },
      });
      alert(`Verified ${res.verified.length}, skipped ${res.skipped.length} (had deficiencies/high-risk).`);
      setSelected(new Set()); load();
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <SectionTitle sub="Prioritised by risk & time pending. AI flags are advisory — you decide.">
          Scrutiny Queue {rows && <span className="text-slate-400 font-normal">({rows.length})</span>}
        </SectionTitle>
        <div className="flex flex-wrap gap-2">
          <select className="input w-auto" value={filters.scheme_id || ""} onChange={(e) => setFilters((f) => ({ ...f, scheme_id: e.target.value || undefined }))}>
            <option value="">All schemes</option>
            {schemes.map((s) => <option key={s.id} value={s.id}>{s.code}</option>)}
          </select>
          <select className="input w-auto" value={filters.status || ""} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}>
            <option value="">All statuses</option>
            {["SUBMITTED", "AUTO_VERIFIED", "UNDER_SCRUTINY", "RESUBMITTED"].map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
          </select>
          <select className="input w-auto" value={filters.min_risk || ""} onChange={(e) => setFilters((f) => ({ ...f, min_risk: e.target.value || undefined }))}>
            <option value="">Any risk</option>
            <option value="60">High (≥60)</option>
            <option value="25">Medium+ (≥25)</option>
          </select>
        </div>
      </div>

      {selected.size > 0 && (
        <div className="bg-navy text-white rounded-lg px-4 py-2 flex items-center justify-between text-sm">
          <span>{selected.size} selected</span>
          <Button variant="accent" onClick={bulkVerify} loading={busy}>Bulk verify clean ones</Button>
        </div>
      )}

      {!rows ? <Spinner /> : rows.length === 0 ? <Card><Empty>Queue is clear.</Empty></Card> : (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-left">
                <tr>
                  <th className="p-3 w-8"></th>
                  <th className="p-3">Applicant</th>
                  <th className="p-3">Scheme</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Risk</th>
                  <th className="p-3">Flags</th>
                  <th className="p-3">SLA</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const meta = STATUS_META[r.status] || { label: r.status, cls: "" };
                  return (
                    <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="p-3"><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} /></td>
                      <td className="p-3">
                        <div className="font-medium">{r.applicant_name}</div>
                        <div className="text-xs text-slate-400">#{r.id} · {r.applicant_state || "—"}</div>
                      </td>
                      <td className="p-3">{r.scheme_code}</td>
                      <td className="p-3"><Badge className={meta.cls}>{meta.label}</Badge></td>
                      <td className="p-3">
                        <Badge className={RISK_CLS[r.risk_level]}>{r.risk_score} · {r.risk_level}</Badge>
                      </td>
                      <td className="p-3">
                        {r.active_flags > 0 ? (
                          <span className="inline-flex items-center gap-1 text-orange-600"><AlertTriangle size={14} />{r.active_flags}</span>
                        ) : <span className="text-slate-300">0</span>}
                        {r.open_deficiencies > 0 && <span className="ml-2 text-xs text-orange-500">{r.open_deficiencies} def</span>}
                      </td>
                      <td className="p-3"><span className="inline-flex items-center gap-1 text-slate-500"><Clock size={13} />{r.sla_hours}h</span></td>
                      <td className="p-3"><Button variant="ghost" onClick={() => router.push(`/officer/review/${r.id}`)}>Review</Button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
