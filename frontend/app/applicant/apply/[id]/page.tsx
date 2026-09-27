"use client";
import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Badge, Input, Label, Spinner, SectionTitle } from "@/components/ui";
import { SampleBadge } from "@/components/AppShell";
import { prettyDoc } from "@/lib/utils";
import { CheckCircle2, AlertTriangle, UploadCloud, FileText } from "lucide-react";

// Applicant-editable fields; only those relevant to the scheme are shown.
const FIELD_DEFS: Record<string, { label: string; type: "number" | "text" | "select"; options?: string[] }> = {
  full_name: { label: "Full name (as on documents)", type: "text" },
  category: { label: "Social category", type: "select", options: ["ST", "OBC", "General"] },
  age: { label: "Age (years)", type: "number" },
  family_income: { label: "Annual family income (₹)", type: "number" },
  qualifying_marks: { label: "Qualifying exam marks (%)", type: "number" },
  course_level: { label: "Course level", type: "select" },
  university_rank: { label: "University QS World Rank", type: "number" },
  research_proposal_score: { label: "Research proposal self-score (0-100)", type: "number" },
};

export default function ApplyPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [app, setApp] = useState<any>(null);
  const [scheme, setScheme] = useState<any>(null);
  const [form, setForm] = useState<Record<string, any>>({});
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploads, setUploads] = useState<Record<string, any>>({});

  const load = async () => {
    const a = await api(`/applications/${id}`);
    setApp(a);
    const s = await api(`/schemes/${a.scheme_id}`);
    setScheme(s);
    setForm({ full_name: a.applicant_name || "", ...(a.applicant_profile || {}), ...(a.form_data || {}) });
    const up: Record<string, any> = {};
    (a.documents || []).forEach((d: any) => { up[d.doc_type] = d; });
    setUploads(up);
  };
  useEffect(() => { load(); }, [id]);

  // Which fields to render: union of eligibility-rule fields + merit fields.
  const fields = useMemo(() => {
    if (!scheme) return [];
    const set = new Set<string>(["full_name"]);
    (scheme.rules?.rules || []).forEach((r: any) => set.add(r.field));
    const meritMap: Record<string, string> = {
      marks: "qualifying_marks", income_bracket: "family_income",
      research_proposal: "research_proposal_score", university_rank: "university_rank",
    };
    Object.keys(scheme.merit_criteria?.weights || {}).forEach((k) => {
      if (meritMap[k]) set.add(meritMap[k]);
    });
    return Array.from(set).filter((f) => FIELD_DEFS[f]);
  }, [scheme]);

  const courseOptions = useMemo(() => {
    const rule = (scheme?.rules?.rules || []).find((r: any) => r.field === "course_level" && r.op === "in");
    return rule?.value || ["M.Phil", "Ph.D", "Masters"];
  }, [scheme]);

  if (!app || !scheme) return <Spinner />;

  const setField = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const saveDraft = async () => {
    setSaving(true);
    try { await api(`/applications/${id}`, { method: "PUT", body: { form_data: form } }); }
    finally { setSaving(false); }
  };

  const uploadDoc = async (docType: string, file: File) => {
    setUploads((u) => ({ ...u, [docType]: { loading: true } }));
    const fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      const res = await api(`/applications/${id}/documents`, { method: "POST", form: fd });
      setUploads((u) => ({ ...u, [docType]: res }));
    } catch (e) {
      setUploads((u) => ({ ...u, [docType]: { error: e instanceof ApiError ? e.message : "Upload failed" } }));
    }
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      await saveDraft();
      const res = await api<{ auto_verification: any }>(`/applications/${id}/submit`, { method: "POST" });
      router.push(`/applicant/application/${id}?submitted=1`);
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "Submit failed");
    } finally { setSubmitting(false); }
  };

  const mandatoryDocs = scheme.documents.filter((d: any) => d.mandatory);
  const missingMandatory = mandatoryDocs.filter((d: any) => !uploads[d.doc_type] || uploads[d.doc_type].error);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">Apply · {scheme.code}</h1>
        {scheme.is_sample && <SampleBadge />}
      </div>

      {/* Steps */}
      <div className="flex gap-2 text-sm">
        {["Details", "Documents", "Review & Submit"].map((s, i) => (
          <div key={i} className={`flex-1 rounded-lg px-3 py-2 text-center border ${step === i + 1 ? "bg-navy text-white border-navy" : "bg-white text-slate-500 border-slate-200"}`}>
            {i + 1}. {s}
          </div>
        ))}
      </div>

      {step === 1 && (
        <Card>
          <SectionTitle sub="This form is generated from the scheme's configured rules & merit criteria.">Applicant details</SectionTitle>
          <div className="grid sm:grid-cols-2 gap-4">
            {fields.map((f) => {
              const def = FIELD_DEFS[f];
              const opts = f === "course_level" ? courseOptions : def.options;
              return (
                <div key={f} className={f === "full_name" ? "sm:col-span-2" : ""}>
                  <Label>{def.label}</Label>
                  {def.type === "select" ? (
                    <select className="input" value={form[f] ?? ""} onChange={(e) => setField(f, e.target.value)}>
                      <option value="">Select…</option>
                      {(opts || []).map((o: string) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : (
                    <Input type={def.type} value={form[f] ?? ""}
                      onChange={(e) => setField(f, def.type === "number" ? Number(e.target.value) : e.target.value)} />
                  )}
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-5">
            <Button variant="ghost" onClick={saveDraft} loading={saving}>Save draft</Button>
            <Button onClick={() => { saveDraft(); setStep(2); }}>Next: Documents</Button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <SectionTitle sub="Upload each document. You get instant feedback — detected type, readability & AI checks.">
            Documents
          </SectionTitle>
          <div className="space-y-3">
            {scheme.documents.map((d: any) => {
              const u = uploads[d.doc_type];
              return (
                <div key={d.id} className="border border-slate-200 rounded-lg p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <FileText size={18} className="text-slate-400" />
                      <div>
                        <div className="text-sm font-medium">{d.label}</div>
                        <div className="text-xs text-slate-400">
                          {d.mandatory ? "Mandatory" : "Optional"} · {prettyDoc(d.doc_type)}
                        </div>
                      </div>
                    </div>
                    <label className="btn-ghost cursor-pointer">
                      <UploadCloud size={16} /> {u && !u.error ? "Replace" : "Upload"}
                      <input type="file" className="hidden" accept="application/pdf,image/*"
                        onChange={(e) => e.target.files?.[0] && uploadDoc(d.doc_type, e.target.files[0])} />
                    </label>
                  </div>
                  {u?.loading && <div className="text-xs text-slate-400 mt-2">Processing…</div>}
                  {u?.error && <div className="text-xs text-red-600 mt-2">{u.error}</div>}
                  {u && !u.error && !u.loading && (
                    <div className="mt-2 text-xs bg-slate-50 rounded p-2 space-y-1">
                      <div className="flex items-center gap-2">
                        {u.matches_expected ? <CheckCircle2 size={14} className="text-green-600" /> : <AlertTriangle size={14} className="text-orange-500" />}
                        <span>Detected: <b>{prettyDoc(u.detected_type)}</b>{!u.matches_expected && " — does not match this slot"}</span>
                      </div>
                      <div>Readability: {(u.readability * 100).toFixed(0)}%</div>
                      {u.extracted?.length > 0 && (
                        <div className="text-slate-500">
                          Extracted: {u.extracted.filter((x: any) => x.value).map((x: any) => `${x.key}=${x.value}`).join(", ") || "—"}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-5">
            <Button variant="ghost" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={() => setStep(3)}>Next: Review</Button>
          </div>
        </Card>
      )}

      {step === 3 && (
        <Card>
          <SectionTitle sub="Review, then submit for automated verification.">Review & Submit</SectionTitle>
          <div className="grid sm:grid-cols-2 gap-2 text-sm">
            {fields.map((f) => (
              <div key={f} className="flex justify-between border-b border-slate-100 py-1">
                <span className="text-slate-500">{FIELD_DEFS[f].label}</span>
                <span className="font-medium">{String(form[f] ?? "—")}</span>
              </div>
            ))}
          </div>
          {missingMandatory.length > 0 && (
            <div className="mt-4 text-sm text-orange-700 bg-orange-50 rounded-md px-3 py-2">
              Missing mandatory documents: {missingMandatory.map((d: any) => d.label).join(", ")}.
              You can still submit — the system will raise a deficiency you can fix later.
            </div>
          )}
          <div className="flex justify-between mt-5">
            <Button variant="ghost" onClick={() => setStep(2)}>Back</Button>
            <Button variant="accent" onClick={submit} loading={submitting}>Submit application</Button>
          </div>
        </Card>
      )}
    </div>
  );
}
