"use client";
import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Badge, Textarea, Spinner, Modal, Empty, SectionTitle } from "@/components/ui";
import { Trophy, ChevronDown, ChevronUp } from "lucide-react";

export default function MeritPage() {
  const { schemeId } = useParams<{ schemeId: string }>();
  const [scheme, setScheme] = useState<any>(null);
  const [list, setList] = useState<any[] | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [adjust, setAdjust] = useState<any>(null);
  const [justification, setJustification] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const loadList = () => api(`/schemes/${schemeId}/merit-list`).then(setList).catch(() => setList([]));
  useEffect(() => { api(`/schemes/${schemeId}`).then(setScheme); loadList(); }, [schemeId]);

  const generate = async () => {
    setBusy(true); setMsg("");
    try {
      const res = await api<{ ranked: number }>(`/schemes/${schemeId}/generate-merit`, { method: "POST" });
      setMsg(`Merit list generated for ${res.ranked} screened applications.`);
      await loadList();
    } catch (e) { setMsg(e instanceof ApiError ? e.message : "Failed"); }
    finally { setBusy(false); }
  };

  const publish = async () => {
    if (!confirm("Publish results? Selected applicants will be notified and selection letters generated.")) return;
    setBusy(true);
    try {
      const res = await api<{ selected: number }>(`/schemes/${schemeId}/publish`, { method: "POST" });
      setMsg(`Results published. ${res.selected} applicants selected.`);
      await loadList();
    } catch (e) { setMsg(e instanceof ApiError ? e.message : "Failed"); }
    finally { setBusy(false); }
  };

  const doAdjust = async (selected: boolean) => {
    setBusy(true);
    try {
      await api(`/merit/${adjust.application_id}/adjust`, {
        method: "POST", body: { selected, justification },
      });
      setAdjust(null); setJustification(""); await loadList();
    } catch (e) { alert(e instanceof ApiError ? e.message : "Failed"); }
    finally { setBusy(false); }
  };

  if (!scheme) return <Spinner />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTitle sub={`${scheme.name} · ${scheme.slots} slots · transparent, weighted scoring`}>
          Merit List · {scheme.code}
        </SectionTitle>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={generate} loading={busy}>Generate / Refresh</Button>
          <Button variant="accent" onClick={publish} loading={busy} disabled={!list?.length}>Publish results</Button>
        </div>
      </div>
      {msg && <div className="text-sm bg-sky-50 text-sky-800 rounded-md px-3 py-2">{msg}</div>}

      {!list ? <Spinner /> : list.length === 0 ? (
        <Card><Empty>No merit list yet. Ensure applications are screened, then Generate.</Empty></Card>
      ) : (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-left">
                <tr>
                  <th className="p-3">Rank</th>
                  <th className="p-3">Applicant</th>
                  <th className="p-3">Score</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Quota</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {list.map((r) => {
                  const within = r.rank && r.rank <= scheme.slots;
                  return (
                    <React.Fragment key={r.application_id}>
                      <tr className={"border-t border-slate-100 " + (within ? "bg-green-50/40" : "")}>
                        <td className="p-3 font-semibold">{r.rank <= 3 && <Trophy size={14} className="inline text-amber-500 mr-1" />}{r.rank}</td>
                        <td className="p-3">{r.applicant_name} {r.adjusted && <Badge className="bg-violet-100 text-violet-700 ml-1">adjusted</Badge>}</td>
                        <td className="p-3 font-medium">{r.total}</td>
                        <td className="p-3">
                          <Badge className={r.status === "SELECTED" || r.status === "FELLOWSHIP_ACTIVE" ? "bg-green-100 text-green-800" : r.status === "REJECTED" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-600"}>
                            {r.status}
                          </Badge>
                        </td>
                        <td className="p-3 text-xs text-slate-500">{r.quota_tag || "—"}</td>
                        <td className="p-3 flex gap-2">
                          <button onClick={() => setExpanded(expanded === r.application_id ? null : r.application_id)} className="text-sky text-xs hover:underline inline-flex items-center">
                            Breakdown {expanded === r.application_id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          </button>
                          <button onClick={() => setAdjust(r)} className="text-violet-600 text-xs hover:underline">Adjust</button>
                        </td>
                      </tr>
                      {expanded === r.application_id && (
                        <tr className="bg-slate-50/70"><td colSpan={6} className="p-3">
                          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-2">
                            {(r.breakdown || []).map((b: any, i: number) => (
                              <div key={i} className="bg-white rounded-lg border border-slate-200 p-2 text-xs">
                                <div className="font-medium capitalize">{b.criterion.replace(/_/g, " ")}</div>
                                <div className="text-slate-500">raw {String(b.raw ?? "—")} → norm {b.normalized}</div>
                                <div className="text-slate-500">weight {Math.round(b.weight * 100)}% → <b>+{b.contribution}</b></div>
                              </div>
                            ))}
                          </div>
                        </td></tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Modal open={!!adjust} onClose={() => setAdjust(null)} title={`Adjust · ${adjust?.applicant_name}`}>
        <p className="text-sm text-slate-500 mb-2">Committee overrides require a justification and are recorded in the audit log.</p>
        <Textarea rows={3} placeholder="Justification (required)" value={justification} onChange={(e) => setJustification(e.target.value)} />
        <div className="flex justify-end gap-2 mt-3">
          <Button variant="ghost" onClick={() => doAdjust(false)} loading={busy} disabled={justification.length < 5}>Mark not selected</Button>
          <Button variant="accent" onClick={() => doAdjust(true)} loading={busy} disabled={justification.length < 5}>Mark selected</Button>
        </div>
      </Modal>
    </div>
  );
}
