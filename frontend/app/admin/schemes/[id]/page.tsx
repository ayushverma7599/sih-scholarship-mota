"use client";
import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Input, Label, Spinner, SectionTitle, Field } from "@/components/ui";
import { Trash2, Plus } from "lucide-react";

const OPS = ["==", "!=", "<", "<=", ">", ">=", "in", "not_in", "contains"];
const empty = {
  code: "", name: "", description: "", academic_year: "2025-26", slots: 10,
  window_open: "", window_close: "", is_active: true, is_sample: true,
  rules: { combinator: "all", rules: [] as any[] },
  documents: [] as any[],
  merit_weights: {} as Record<string, number>,
  merit_tiebreak: [] as string[],
  merit_quotas: {} as Record<string, number>,
};

export default function SchemeEditor() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const isNew = id === "new";
  const [s, setS] = useState<any>(isNew ? empty : null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (isNew) return;
    api(`/schemes/${id}`).then((d) => setS({
      ...d,
      rules: d.rules?.rules ? d.rules : { combinator: "all", rules: [] },
      merit_weights: d.merit_criteria?.weights || {},
      merit_tiebreak: d.merit_criteria?.tiebreak || [],
      merit_quotas: d.merit_criteria?.quotas || {},
      window_open: d.window_open || "", window_close: d.window_close || "",
    })).catch(() => setErr("Failed to load"));
  }, [id, isNew]);

  if (!s) return <Spinner />;
  const set = (k: string, v: any) => setS((p: any) => ({ ...p, [k]: v }));

  // rules helpers
  const setRule = (i: number, k: string, v: any) => set("rules", {
    ...s.rules, rules: s.rules.rules.map((r: any, j: number) => j === i ? { ...r, [k]: v } : r),
  });
  const addRule = () => set("rules", { ...s.rules, rules: [...s.rules.rules, { field: "", op: "==", value: "", label: "" }] });
  const delRule = (i: number) => set("rules", { ...s.rules, rules: s.rules.rules.filter((_: any, j: number) => j !== i) });

  // documents helpers
  const setDoc = (i: number, k: string, v: any) => set("documents", s.documents.map((d: any, j: number) => j === i ? { ...d, [k]: v } : d));
  const addDoc = () => set("documents", [...s.documents, { doc_type: "", label: "", mandatory: true, extract_fields: [], order: s.documents.length + 1 }]);
  const delDoc = (i: number) => set("documents", s.documents.filter((_: any, j: number) => j !== i));

  const save = async () => {
    setBusy(true); setErr("");
    // Coerce rule values: numbers stay numbers, "in"/"not_in" become arrays.
    const rules = {
      combinator: s.rules.combinator || "all",
      rules: s.rules.rules.map((r: any) => {
        let value = r.value;
        if (r.op === "in" || r.op === "not_in") {
          value = Array.isArray(value) ? value : String(value).split(",").map((x: string) => x.trim());
        } else if (!isNaN(Number(value)) && value !== "" && typeof value !== "boolean") {
          value = Number(value);
        }
        return { ...r, value };
      }),
    };
    const payload = {
      code: s.code, name: s.name, description: s.description, academic_year: s.academic_year,
      slots: Number(s.slots), window_open: s.window_open || null, window_close: s.window_close || null,
      is_active: s.is_active, is_sample: s.is_sample, rules,
      documents: s.documents.map((d: any) => ({
        ...d,
        extract_fields: Array.isArray(d.extract_fields) ? d.extract_fields : String(d.extract_fields).split(",").map((x: string) => x.trim()).filter(Boolean),
      })),
      merit_weights: s.merit_weights, merit_tiebreak: s.merit_tiebreak, merit_quotas: s.merit_quotas,
    };
    try {
      if (isNew) await api("/schemes", { method: "POST", body: payload });
      else await api(`/schemes/${id}`, { method: "PUT", body: payload });
      router.push("/admin/schemes");
    } catch (e) { setErr(e instanceof ApiError ? e.message : "Save failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <SectionTitle sub="No code required — everything here is stored as configurable data.">
          {isNew ? "New Scheme" : `Configure · ${s.code}`}
        </SectionTitle>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => router.push("/admin/schemes")}>Cancel</Button>
          <Button variant="accent" onClick={save} loading={busy}>Save scheme</Button>
        </div>
      </div>
      {err && <div className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{err}</div>}

      {/* Basics */}
      <Card>
        <SectionTitle>Basic details</SectionTitle>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Code (e.g. NFST)"><Input value={s.code} onChange={(e) => set("code", e.target.value)} /></Field>
          <Field label="Academic year"><Input value={s.academic_year} onChange={(e) => set("academic_year", e.target.value)} /></Field>
          <div className="sm:col-span-2"><Field label="Name"><Input value={s.name} onChange={(e) => set("name", e.target.value)} /></Field></div>
          <div className="sm:col-span-2"><Field label="Description"><Input value={s.description} onChange={(e) => set("description", e.target.value)} /></Field></div>
          <Field label="Slots"><Input type="number" value={s.slots} onChange={(e) => set("slots", e.target.value)} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Window open"><Input type="date" value={s.window_open} onChange={(e) => set("window_open", e.target.value)} /></Field>
            <Field label="Window close"><Input type="date" value={s.window_close} onChange={(e) => set("window_close", e.target.value)} /></Field>
          </div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={s.is_active} onChange={(e) => set("is_active", e.target.checked)} /> Active</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={s.is_sample} onChange={(e) => set("is_sample", e.target.checked)} /> Mark as SAMPLE (values pending official guidelines)</label>
        </div>
      </Card>

      {/* Eligibility rules */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div><h3 className="font-semibold">Eligibility Rules</h3><p className="text-xs text-slate-500">Evaluated with combinator: {s.rules.combinator}. Use comma-separated values for "in"/"not_in".</p></div>
          <Button variant="ghost" onClick={addRule}><Plus size={14} /> Add rule</Button>
        </div>
        <div className="space-y-2">
          {s.rules.rules.map((r: any, i: number) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-center">
              <Input className="col-span-3" placeholder="field" value={r.field} onChange={(e) => setRule(i, "field", e.target.value)} />
              <select className="input col-span-2" value={r.op} onChange={(e) => setRule(i, "op", e.target.value)}>{OPS.map((o) => <option key={o}>{o}</option>)}</select>
              <Input className="col-span-2" placeholder="value" value={Array.isArray(r.value) ? r.value.join(",") : r.value} onChange={(e) => setRule(i, "value", e.target.value)} />
              <Input className="col-span-4" placeholder="human-readable label" value={r.label} onChange={(e) => setRule(i, "label", e.target.value)} />
              <button className="col-span-1 text-red-500 flex justify-center" onClick={() => delRule(i)}><Trash2 size={16} /></button>
            </div>
          ))}
          {s.rules.rules.length === 0 && <p className="text-sm text-slate-400">No rules — scheme open to all.</p>}
        </div>
      </Card>

      {/* Documents */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div><h3 className="font-semibold">Required Documents</h3><p className="text-xs text-slate-500">extract_fields drives OCR extraction (comma-separated).</p></div>
          <Button variant="ghost" onClick={addDoc}><Plus size={14} /> Add document</Button>
        </div>
        <div className="space-y-2">
          {s.documents.map((d: any, i: number) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-center">
              <Input className="col-span-2" placeholder="doc_type" value={d.doc_type} onChange={(e) => setDoc(i, "doc_type", e.target.value)} />
              <Input className="col-span-3" placeholder="label" value={d.label} onChange={(e) => setDoc(i, "label", e.target.value)} />
              <Input className="col-span-4" placeholder="extract fields (comma)" value={Array.isArray(d.extract_fields) ? d.extract_fields.join(",") : d.extract_fields} onChange={(e) => setDoc(i, "extract_fields", e.target.value)} />
              <label className="col-span-2 flex items-center gap-1 text-xs"><input type="checkbox" checked={d.mandatory} onChange={(e) => setDoc(i, "mandatory", e.target.checked)} /> mandatory</label>
              <button className="col-span-1 text-red-500 flex justify-center" onClick={() => delDoc(i)}><Trash2 size={16} /></button>
            </div>
          ))}
          {s.documents.length === 0 && <p className="text-sm text-slate-400">No documents configured.</p>}
        </div>
      </Card>

      {/* Merit criteria */}
      <Card>
        <h3 className="font-semibold mb-1">Merit Criteria (weights)</h3>
        <p className="text-xs text-slate-500 mb-3">Weights are normalized automatically. Known keys: marks, income_bracket, research_proposal, university_rank, interview.</p>
        <KeyValueEditor obj={s.merit_weights} onChange={(o) => set("merit_weights", o)} valuePlaceholder="weight (0-1)" numeric />
        <div className="grid sm:grid-cols-2 gap-4 mt-4">
          <Field label="Tie-break order (comma; suffix _asc for ascending)">
            <Input value={s.merit_tiebreak.join(",")} onChange={(e) => set("merit_tiebreak", e.target.value.split(",").map((x) => x.trim()).filter(Boolean))} />
          </Field>
          <div>
            <Label>Reservation quotas</Label>
            <KeyValueEditor obj={s.merit_quotas} onChange={(o) => set("merit_quotas", o)} valuePlaceholder="share (0-1)" numeric />
          </div>
        </div>
      </Card>
    </div>
  );
}

function KeyValueEditor({ obj, onChange, valuePlaceholder, numeric }: {
  obj: Record<string, any>; onChange: (o: Record<string, any>) => void; valuePlaceholder?: string; numeric?: boolean;
}) {
  const entries = Object.entries(obj);
  const update = (idx: number, key: string, val: string) => {
    const next: Record<string, any> = {};
    entries.forEach(([k, v], i) => {
      if (i === idx) next[key] = numeric ? Number(val) : val;
      else next[k] = v;
    });
    onChange(next);
  };
  const rename = (idx: number, newKey: string) => {
    const next: Record<string, any> = {};
    entries.forEach(([k, v], i) => { next[i === idx ? newKey : k] = v; });
    onChange(next);
  };
  const add = () => onChange({ ...obj, "": numeric ? 0 : "" });
  const del = (idx: number) => onChange(Object.fromEntries(entries.filter((_, i) => i !== idx)));
  return (
    <div className="space-y-2">
      {entries.map(([k, v], i) => (
        <div key={i} className="flex gap-2 items-center">
          <Input placeholder="key" value={k} onChange={(e) => rename(i, e.target.value)} />
          <Input placeholder={valuePlaceholder} value={String(v)} onChange={(e) => update(i, k, e.target.value)} />
          <button className="text-red-500" onClick={() => del(i)}><Trash2 size={16} /></button>
        </div>
      ))}
      <button className="text-sm text-sky hover:underline" onClick={add}>+ Add</button>
    </div>
  );
}
