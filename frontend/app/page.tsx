"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth, HOME_BY_ROLE, Role } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Card, Input, Label } from "@/components/ui";
import { ApiError } from "@/lib/api";

const DEMO: { email: string; role: Role; label: string; desc: string }[] = [
  { email: "admin@demo.gov.in", role: "admin", label: "Ministry Admin", desc: "Configure schemes, view dashboards & audit" },
  { email: "scrutiny@demo.gov.in", role: "scrutiny", label: "Scrutiny Officer", desc: "Verify documents, raise deficiencies" },
  { email: "committee@demo.gov.in", role: "committee", label: "Committee Member", desc: "Merit list & selection" },
  { email: "applicant@demo.gov.in", role: "applicant", label: "Applicant (ST student)", desc: "Discover schemes & apply" },
];

const ROLE_COLOR: Record<Role, string> = {
  admin: "border-l-navy", scrutiny: "border-l-amber-500",
  committee: "border-l-violet-500", applicant: "border-l-leaf",
};

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const { t, lang, toggle } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("demo1234");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace(HOME_BY_ROLE[user.role]);
  }, [user, loading, router]);

  const doLogin = async (e?: React.FormEvent, presetEmail?: string) => {
    e?.preventDefault();
    setErr(""); setBusy(true);
    try {
      const u = await login(presetEmail || email, password);
      router.replace(HOME_BY_ROLE[u.role]);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <div className="gov-strip" />
      <div className="flex-1 grid lg:grid-cols-2">
        {/* Left: intro */}
        <div className="bg-navy text-white p-8 lg:p-14 flex flex-col justify-center">
          <button onClick={toggle} className="self-start mb-6 text-sm bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-md">
            {lang === "en" ? "हिंदी में देखें" : "View in English"}
          </button>
          <div className="text-sm text-white/70">{t("govt_india")} · {t("ministry")}</div>
          <h1 className="text-3xl lg:text-4xl font-bold mt-2 leading-tight">{t("app_name")}</h1>
          <p className="text-white/80 mt-4 max-w-md">
            {lang === "en"
              ? "One secure, transparent and intelligent platform for Scheduled Tribe scholarships & fellowships (NFST, NOS). Configurable rules, AI-assisted verification, and human-reviewed decisions."
              : "अनुसूचित जनजाति छात्रवृत्ति एवं फ़ेलोशिप (NFST, NOS) के लिए एक सुरक्षित, पारदर्शी और बुद्धिमान मंच। विन्यास-योग्य नियम, एआई-सहायता प्राप्त सत्यापन और मानव-समीक्षित निर्णय।"}
          </p>
          <ul className="mt-6 space-y-2 text-sm text-white/80">
            <li>• Configurable scheme engine (eligibility, documents, merit weights)</li>
            <li>• OCR + cross-verification with explainable AI flags</li>
            <li>• Officer workbench, merit list & fellowship lifecycle</li>
            <li>• Every automated decision is reviewable, overridable & audited</li>
          </ul>
          <div className="mt-8 text-xs text-white/50">Prototype · SIH 2026 · PS 26239. Not an official Government portal.</div>
        </div>

        {/* Right: login + demo */}
        <div className="p-8 lg:p-14 flex flex-col justify-center bg-slate-50">
          <div className="w-full max-w-md mx-auto">
            <Card>
              <h2 className="text-xl font-semibold mb-1">{t("login")}</h2>
              <p className="text-sm text-slate-500 mb-4">Sign in with a demo account or your credentials.</p>
              <form onSubmit={doLogin} className="space-y-3">
                <div><Label>{t("email")}</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required /></div>
                <div><Label>{t("password")}</Label><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></div>
                {err && <div className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{err}</div>}
                <Button type="submit" loading={busy} className="w-full">{t("login")}</Button>
              </form>
            </Card>

            <div className="mt-6">
              <div className="text-sm font-medium text-slate-600 mb-2">{t("demo_logins")} <span className="text-slate-400">(password: demo1234)</span></div>
              <div className="grid gap-2">
                {DEMO.map((d) => (
                  <button key={d.email} onClick={() => { setEmail(d.email); doLogin(undefined, d.email); }}
                    className={`text-left bg-white rounded-lg border border-slate-200 border-l-4 ${ROLE_COLOR[d.role]} px-4 py-3 hover:shadow-card transition`}>
                    <div className="font-medium text-sm">{d.label}</div>
                    <div className="text-xs text-slate-500">{d.desc}</div>
                    <div className="text-xs text-slate-400 mt-0.5">{d.email}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
