"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Badge, Empty, Spinner, SectionTitle } from "@/components/ui";
import { SampleBadge } from "@/components/AppShell";
import { useI18n } from "@/lib/i18n";
import { STATUS_META } from "@/lib/utils";

type Eligible = {
  scheme_id: number; code: string; name: string; description: string;
  academic_year: string; slots: number; is_sample: boolean;
  eligible: boolean; summary: string;
  reasons: { label: string; pass: boolean; reason: string }[];
};
type App = { id: number; scheme_code: string; scheme_name: string; status: string; open_deficiencies: number };

export default function ApplicantHome() {
  const { t } = useI18n();
  const router = useRouter();
  const [schemes, setSchemes] = useState<Eligible[] | null>(null);
  const [apps, setApps] = useState<App[] | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [applying, setApplying] = useState<number | null>(null);

  const load = () => {
    api<Eligible[]>("/me/eligible-schemes").then(setSchemes).catch(() => setSchemes([]));
    api<App[]>("/me/applications").then(setApps).catch(() => setApps([]));
  };
  useEffect(load, []);

  const appliedSchemeIds = new Set((apps || []).map((a) => a.scheme_code));

  const apply = async (schemeId: number) => {
    setApplying(schemeId);
    try {
      const created = await api<{ id: number }>("/applications", { method: "POST", body: { scheme_id: schemeId, form_data: {} } });
      router.push(`/applicant/apply/${created.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        // already exists — go to it
        const mine = await api<App[]>("/me/applications");
        const existing = mine.find((m) => m.scheme_code === schemes?.find(s => s.scheme_id === schemeId)?.code);
        if (existing) router.push(`/applicant/application/${existing.id}`);
      } else alert(e instanceof ApiError ? e.message : "Failed");
    } finally { setApplying(null); }
  };

  return (
    <div className="space-y-8">
      {/* My applications */}
      <section>
        <SectionTitle sub="Track status, respond to deficiencies, resubmit.">{t("my_applications")}</SectionTitle>
        {!apps ? <Spinner /> : apps.length === 0 ? (
          <Card><Empty>No applications yet. Explore the schemes below to apply.</Empty></Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {apps.map((a) => {
              const meta = STATUS_META[a.status] || { label: a.status, cls: "" };
              return (
                <Link key={a.id} href={`/applicant/application/${a.id}`}>
                  <Card className="hover:shadow-md transition h-full">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">{a.scheme_code}</span>
                      <Badge className={meta.cls}>{meta.label}</Badge>
                    </div>
                    <div className="text-sm text-slate-500 mt-1">{a.scheme_name}</div>
                    {a.open_deficiencies > 0 && (
                      <div className="mt-3 text-xs text-orange-700 bg-orange-50 rounded px-2 py-1 inline-block">
                        {a.open_deficiencies} deficiency(ies) to resolve
                      </div>
                    )}
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      {/* Eligible schemes */}
      <section>
        <SectionTitle sub="Instant eligibility pre-check based on your profile — with reasons.">
          {t("eligible_schemes")}
        </SectionTitle>
        {!schemes ? <Spinner /> : (
          <div className="grid md:grid-cols-2 gap-4">
            {schemes.map((s) => (
              <Card key={s.scheme_id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-lg">{s.code}</span>
                      {s.is_sample && <SampleBadge />}
                    </div>
                    <div className="text-sm text-slate-500">{s.name}</div>
                  </div>
                  <Badge className={s.eligible ? "bg-green-100 text-green-800" : "bg-red-100 text-red-700"}>
                    {s.eligible ? t("eligible") : t("not_eligible")}
                  </Badge>
                </div>
                <p className="text-sm text-slate-600 mt-3">{s.description}</p>
                <div className="text-xs text-slate-400 mt-2">Academic year {s.academic_year} · {s.slots} slots</div>

                <button onClick={() => setExpanded(expanded === s.scheme_id ? null : s.scheme_id)}
                  className="text-sm text-sky mt-3 hover:underline">
                  {expanded === s.scheme_id ? "Hide" : "Why?"} eligibility check
                </button>
                {expanded === s.scheme_id && (
                  <ul className="mt-2 space-y-1.5 border-t border-slate-100 pt-2">
                    {s.reasons.map((r, i) => (
                      <li key={i} className="text-xs flex gap-2">
                        <span className={r.pass ? "text-green-600" : "text-red-600"}>{r.pass ? "✓" : "✗"}</span>
                        <span className="text-slate-600">{r.reason}</span>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="mt-4">
                  {appliedSchemeIds.has(s.code) ? (
                    <Badge className="bg-slate-100 text-slate-500">Already applied</Badge>
                  ) : (
                    <Button variant={s.eligible ? "accent" : "ghost"} loading={applying === s.scheme_id}
                      onClick={() => apply(s.scheme_id)}>
                      {t("apply")}
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
