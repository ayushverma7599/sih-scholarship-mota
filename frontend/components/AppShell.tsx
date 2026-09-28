"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, LogOut, Languages, ShieldCheck } from "lucide-react";
import { useAuth, Role } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV: Record<Role, { href: string; key: string; label: string }[]> = {
  applicant: [
    { href: "/applicant", key: "dashboard", label: "Home" },
    { href: "/applicant/notifications", key: "notifications", label: "Notifications" },
  ],
  scrutiny: [{ href: "/officer", key: "scrutiny_queue", label: "Queue" }],
  committee: [{ href: "/committee", key: "merit_list", label: "Merit & Selection" }],
  admin: [
    { href: "/admin", key: "dashboard", label: "Dashboard" },
    { href: "/admin/schemes", key: "schemes", label: "Schemes" },
    { href: "/admin/audit", key: "audit_log", label: "Audit" },
  ],
};

const ROLE_LABEL: Record<Role, string> = {
  applicant: "Applicant", scrutiny: "Scrutiny Officer",
  committee: "Committee", admin: "Ministry Admin",
};

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { t, lang, toggle } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!user) return;
    api<{ unread: number }>("/notifications?unread_only=true")
      .then((d) => setUnread(d.unread)).catch(() => {});
  }, [user, pathname]);

  if (!user) return null;
  const nav = NAV[user.role] || [];

  return (
    <div className="min-h-screen flex flex-col">
      <div className="gov-strip" />
      <header className="bg-navy text-white">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-white/10 flex items-center justify-center text-xl">🇮🇳</div>
            <div>
              <div className="text-xs text-white/70 leading-tight">{t("govt_india")} · {t("ministry")}</div>
              <div className="font-semibold leading-tight">{t("app_name")} <span className="font-normal text-white/60 text-xs">· {t("tagline")}</span></div>
            </div>
          </div>
          <nav className="hidden md:flex items-center gap-1 ml-6">
            {nav.map((n) => (
              <Link key={n.href} href={n.href}
                className={cn("px-3 py-1.5 rounded-md text-sm",
                  pathname === n.href ? "bg-white/15" : "hover:bg-white/10")}>
                {t(n.key) !== n.key ? t(n.key) : n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={toggle} title="Language"
              className="px-2.5 py-1.5 rounded-md hover:bg-white/10 text-sm flex items-center gap-1">
              <Languages size={16} /> {lang === "en" ? "हिंदी" : "EN"}
            </button>
            <Link href="/applicant/notifications" className="relative p-2 rounded-md hover:bg-white/10"
              onClick={(e) => { if (user.role !== "applicant") e.preventDefault(); }}>
              <Bell size={18} />
              {unread > 0 && (
                <span className="absolute -top-0.5 -right-0.5 bg-saffron text-[10px] rounded-full h-4 min-w-4 px-1 flex items-center justify-center">
                  {unread}
                </span>
              )}
            </Link>
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/10 text-sm">
              <ShieldCheck size={16} className="text-emerald-300" />
              <span>{user.full_name}</span>
              <span className="text-white/60">· {ROLE_LABEL[user.role]}</span>
            </div>
            <button onClick={() => { logout(); router.replace("/"); }}
              className="p-2 rounded-md hover:bg-white/10" title={t("logout")}>
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">{children}</main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 py-3 text-xs text-slate-400 flex flex-wrap gap-2 justify-between">
          <span>Prototype for SIH 2026 · PS 26239 · Ministry of Tribal Affairs.</span>
          <span>AI assists; every decision is human-reviewable & audited. Mocks are clearly labelled.</span>
        </div>
      </footer>
    </div>
  );
}

export function SampleBadge() {
  const { t } = useI18n();
  return (
    <span className="badge bg-amber-50 text-amber-700 border border-amber-200" title={t("sample_notice")}>
      SAMPLE
    </span>
  );
}

export function MockBadge() {
  return <span className="badge bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200">MOCK</span>;
}
