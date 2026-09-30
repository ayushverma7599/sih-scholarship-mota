"use client";
import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api, ApiError, apiDownload, apiObjectUrl } from "@/lib/api";
import { Button, Card, Badge, Textarea, Spinner, SectionTitle, Empty } from "@/components/ui";
import Timeline from "@/components/Timeline";
import { STATUS_META, prettyDoc, inr } from "@/lib/utils";
import { UploadCloud, Download, AlertTriangle } from "lucide-react";

export default function ApplicationTracker() {
  const { id } = useParams<{ id: string }>();
  const justSubmitted = useSearchParams().get("submitted");
  const [app, setApp] = useState<any>(null);
  const [responses, setResponses] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);

  const load = () => api(`/applications/${id}`).then(setApp).catch(() => setApp(null));
  useEffect(() => { load(); }, [id]);

  if (!app) return <Spinner />;
  const meta = STATUS_META[app.status] || { label: app.status, cls: "" };
  const openDefs = (app.deficiencies || []).filter((d: any) => d.status === "OPEN");

  const reupload = async (docType: string, file: File) => {
    setBusy(true);
    const fd = new FormData();
    fd.append("doc_type", docType); fd.append("file", file);
    try { await api(`/applications/${id}/documents`, { method: "POST", form: fd }); await load(); }
    finally { setBusy(false); }
  };

  const respond = async (defId: number) => {
    await api(`/deficiencies/${defId}/respond`, { method: "POST", body: { response: responses[defId] || "" } });
    await load();
  };

  const resubmit = async () => {
    setBusy(true);
    try { await api(`/applications/${id}/resubmit`, { method: "POST" }); await load(); }
    catch (e) { alert(e instanceof ApiError ? e.message : "Failed"); }
    finally { setBusy(false); }
  };

  const isSelected = app.status === "SELECTED" || app.status === "FELLOWSHIP_ACTIVE";

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Left: timeline + status */}
      <div className="space-y-6">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold">{app.scheme_code}</div>
              <div className="text-sm text-slate-500">{app.scheme_name}</div>
            </div>
            <Badge className={meta.cls}>{meta.label}</Badge>
          </div>
        </Card>
        <Card>
          <SectionTitle>Application Tracker</SectionTitle>
          <Timeline steps={app.timeline || []} />
        </Card>
        {isSelected && (
          <Card>
            <SectionTitle sub="Provisional selection (prototype).">🎉 Selected</SectionTitle>
            <Button variant="accent"
              onClick={() => apiDownload(`/selection/${id}/letter.pdf`, `selection-letter-${id}.pdf`)
                .catch((e) => alert(e instanceof ApiError ? e.message : "Download failed"))}>
              <Download size={16} /> Download selection letter
            </Button>
          </Card>
        )}
      </div>

      {/* Right: deficiencies, docs */}
      <div className="lg:col-span-2 space-y-6">
        {justSubmitted && (
          <div className="bg-sky-50 border border-sky-200 text-sky-800 rounded-lg px-4 py-3 text-sm">
            Application submitted and run through automated verification. See the status and any deficiencies below.
          </div>
        )}

        {/* Deficiency inbox */}
        <Card>
          <SectionTitle sub="Exactly what needs fixing. Re-upload only what's needed, then resubmit.">
            Deficiency Inbox
          </SectionTitle>
          {openDefs.length === 0 ? (
            <Empty>No open deficiencies. 🎉</Empty>
          ) : (
            <div className="space-y-3">
              {openDefs.map((d: any) => (
                <div key={d.id} className="border border-orange-200 bg-orange-50/50 rounded-lg p-3">
                  <div className="flex gap-2 text-sm">
                    <AlertTriangle size={16} className="text-orange-500 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="text-slate-800">{d.message}</div>
                      {d.doc_type && (
                        <label className="btn-ghost cursor-pointer mt-2 inline-flex text-xs">
                          <UploadCloud size={14} /> Re-upload {prettyDoc(d.doc_type)}
                          <input type="file" className="hidden" accept="application/pdf,image/*"
                            onChange={(e) => e.target.files?.[0] && reupload(d.doc_type, e.target.files[0])} />
                        </label>
                      )}
                      <Textarea placeholder="Add a note to the officer (optional)" rows={2} className="mt-2 text-sm"
                        value={responses[d.id] || ""} onChange={(e) => setResponses((r) => ({ ...r, [d.id]: e.target.value }))} />
                      <Button variant="ghost" className="mt-1 text-xs" onClick={() => respond(d.id)}>Save response</Button>
                    </div>
                  </div>
                </div>
              ))}
              {app.status === "DEFICIENCY_RAISED" && (
                <Button variant="accent" onClick={resubmit} loading={busy}>Resubmit application</Button>
              )}
            </div>
          )}
        </Card>

        {/* Documents */}
        <Card>
          <SectionTitle>Documents & extracted data</SectionTitle>
          {(app.documents || []).length === 0 ? <Empty>No documents uploaded.</Empty> : (
            <div className="space-y-2">
              {app.documents.map((d: any) => (
                <div key={d.id} className="border border-slate-200 rounded-lg p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{prettyDoc(d.doc_type)}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">Readability {(d.readability * 100).toFixed(0)}%</span>
                      <button onClick={() => apiObjectUrl(`/documents/${d.id}/file`)
                        .then((url) => window.open(url, "_blank"))
                        .catch(() => alert("Could not open document"))}
                        className="text-sky text-xs hover:underline">View</button>
                    </div>
                  </div>
                  {d.extracted?.length > 0 && (
                    <div className="text-xs text-slate-500 mt-1">
                      {d.extracted.filter((x: any) => x.value).map((x: any) => `${x.key}: ${x.value}`).join(" · ") || "—"}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
