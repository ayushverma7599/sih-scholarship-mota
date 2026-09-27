"use client";
import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Badge, Textarea, Spinner, Modal, SectionTitle, Empty } from "@/components/ui";
import { STATUS_META, RISK_CLS, SEVERITY_CLS, prettyDoc } from "@/lib/utils";
import { Clock, ShieldAlert, FileText, Check } from "lucide-react";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [app, setApp] = useState<any>(null);
  const [activeDoc, setActiveDoc] = useState<number | null>(null);
  const [modal, setModal] = useState<null | "deficiency" | "reject" | "override">(null);
  const [overrideFlag, setOverrideFlag] = useState<any>(null);
  const [note, setNote] = useState("");
  const [defItems, setDefItems] = useState<{ doc_type: string; message: string }[]>([{ doc_type: "", message: "" }]);
  const [busy, setBusy] = useState(false);

  const load = () => api(`/scrutiny/${id}`).then((a) => {
    setApp(a);
    if (a.documents?.length && activeDoc === null) setActiveDoc(a.documents[0].id);
  }).catch(() => setApp(null));
  useEffect(() => { load(); }, [id]);

  if (!app) return <Spinner />;
  const meta = STATUS_META[app.status] || { label: app.status, cls: "" };
  const doc = app.documents?.find((d: any) => d.id === activeDoc);

  const act = async (fn: () => Promise<any>, after?: () => void) => {
    setBusy(true);
    try { await fn(); setModal(null); setNote(""); if (after) after(); else await load(); }
    catch (e) { alert(e instanceof ApiError ? e.message : "Action failed"); }
    finally { setBusy(false); }
  };

  const verify = () => act(() => api(`/scrutiny/${id}/verify`, { method: "POST", body: { note } }),
    () => router.push("/officer"));
  const reject = () => act(() => api(`/scrutiny/${id}/reject`, { method: "POST", body: { reason: note } }),
    () => router.push("/officer"));
  const raiseDef = () => act(() => api(`/scrutiny/${id}/raise-deficiency`, {
    method: "POST", body: { items: defItems.filter((d) => d.message), note },
  }), () => router.push("/officer"));
  const doOverride = () => act(() => api(`/scrutiny/ai-flags/${overrideFlag.id}/override`, {
    method: "POST", body: { note },
  }));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <button onClick={() => router.push("/officer")} className="text-sky text-sm hover:underline">← Queue</button>
            <h1 className="text-xl font-semibold">{app.applicant_name}</h1>
            <Badge className={meta.cls}>{meta.label}</Badge>
          </div>
          <div className="text-sm text-slate-400">Application #{app.id} · {app.scheme_code} · {app.applicant_state}</div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={RISK_CLS[app.risk?.level]}>Risk {app.risk?.score} · {app.risk?.level}</Badge>
          <span className="inline-flex items-center gap-1 text-sm text-slate-500"><Clock size={14} />{app.sla_hours}h pending</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* LEFT: document preview */}
        <Card className="p-0 overflow-hidden">
          <div className="flex gap-1 p-2 border-b border-slate-100 overflow-x-auto">
            {(app.documents || []).map((d: any) => (
              <button key={d.id} onClick={() => setActiveDoc(d.id)}
                className={"px-2.5 py-1.5 rounded text-xs whitespace-nowrap " + (activeDoc === d.id ? "bg-navy text-white" : "bg-slate-100 text-slate-600")}>
                {prettyDoc(d.doc_type)}
              </button>
            ))}
          </div>
          {doc ? (
            <div className="h-[70vh] bg-slate-100">
              <iframe src={`/api/documents/${doc.id}/file`} className="w-full h-full" title="Document" />
            </div>
          ) : <Empty>No documents uploaded.</Empty>}
        </Card>

        {/* RIGHT: extracted + form + flags */}
        <div className="space-y-4">
          {/* AI flags */}
          <Card>
            <SectionTitle sub="AI-assist only. Override any flag with a logged justification.">
              AI Flags & Risk
            </SectionTitle>
            {(app.flags || []).length === 0 ? <Empty>No flags — clean application.</Empty> : (
              <div className="space-y-2">
                {app.flags.map((f: any) => (
                  <div key={f.id} className={"rounded-lg border p-2.5 text-sm " + (f.overridden ? "bg-slate-50 border-slate-200 opacity-70" : SEVERITY_CLS[f.severity])}>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium flex items-center gap-1"><ShieldAlert size={14} /> {prettyDoc(f.type)}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs">conf {(f.confidence * 100).toFixed(0)}%</span>
                        {f.overridden ? <Badge className="bg-slate-200 text-slate-600">Overridden</Badge> : (
                          <button className="text-xs underline" onClick={() => { setOverrideFlag(f); setModal("override"); }}>Override</button>
                        )}
                      </div>
                    </div>
                    <div className="mt-1">{f.reason}</div>
                    {f.overridden && f.override_note && <div className="text-xs text-slate-500 mt-1">Note: {f.override_note}</div>}
                  </div>
                ))}
              </div>
            )}
            <div className="mt-3 text-xs text-slate-500">
              <b>Why this risk:</b> {(app.risk?.factors || []).join(" · ")}
            </div>
          </Card>

          {/* Extracted vs form */}
          <Card>
            <SectionTitle>Extracted data vs form ({doc ? prettyDoc(doc.doc_type) : "—"})</SectionTitle>
            {doc?.extracted?.length ? (
              <table className="w-full text-sm">
                <tbody>
                  {doc.extracted.map((e: any, i: number) => (
                    <tr key={i} className="border-b border-slate-100">
                      <td className="py-1.5 text-slate-500 capitalize">{e.key.replace(/_/g, " ")}</td>
                      <td className="py-1.5 font-medium">{e.value || "—"}</td>
                      <td className="py-1.5 text-right text-xs text-slate-400">{(e.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <Empty>No extracted fields for this document.</Empty>}
            <div className="mt-3 text-xs text-slate-500">
              <b>Form data:</b> {Object.entries(app.form_data || {}).map(([k, v]) => `${k}=${v}`).join(" · ")}
            </div>
          </Card>

          {/* Actions */}
          <Card>
            <div className="flex flex-wrap gap-2">
              <Button variant="accent" onClick={verify}><Check size={16} /> Verify</Button>
              <Button variant="ghost" onClick={() => setModal("deficiency")}>Raise Deficiency</Button>
              <Button variant="danger" onClick={() => setModal("reject")}>Reject</Button>
            </div>
          </Card>
        </div>
      </div>

      {/* Modals */}
      <Modal open={modal === "reject"} onClose={() => setModal(null)} title="Reject application">
        <Textarea rows={3} placeholder="Reason for rejection (required)" value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="flex justify-end mt-3"><Button variant="danger" onClick={reject} loading={busy} disabled={!note}>Confirm reject</Button></div>
      </Modal>

      <Modal open={modal === "override"} onClose={() => setModal(null)} title="Override AI flag">
        <p className="text-sm text-slate-500 mb-2">{overrideFlag?.reason}</p>
        <Textarea rows={3} placeholder="Justification (required, logged in audit)" value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="flex justify-end mt-3"><Button onClick={doOverride} loading={busy} disabled={note.length < 3}>Override & log</Button></div>
      </Modal>

      <Modal open={modal === "deficiency"} onClose={() => setModal(null)} title="Raise deficiency">
        {defItems.map((it, i) => (
          <div key={i} className="mb-3 space-y-2 border-b border-slate-100 pb-3">
            <select className="input" value={it.doc_type} onChange={(e) => setDefItems((d) => d.map((x, j) => j === i ? { ...x, doc_type: e.target.value } : x))}>
              <option value="">General (no specific document)</option>
              {(app.documents || []).map((d: any) => <option key={d.id} value={d.doc_type}>{prettyDoc(d.doc_type)}</option>)}
            </select>
            <Textarea rows={2} placeholder="What is wrong / what to fix" value={it.message}
              onChange={(e) => setDefItems((d) => d.map((x, j) => j === i ? { ...x, message: e.target.value } : x))} />
          </div>
        ))}
        <button className="text-sm text-sky hover:underline" onClick={() => setDefItems((d) => [...d, { doc_type: "", message: "" }])}>+ Add another</button>
        <div className="flex justify-end mt-3"><Button onClick={raiseDef} loading={busy} disabled={!defItems.some((d) => d.message)}>Send to applicant</Button></div>
      </Modal>
    </div>
  );
}
