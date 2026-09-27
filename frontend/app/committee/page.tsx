"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, Badge, Spinner, SectionTitle } from "@/components/ui";
import { SampleBadge } from "@/components/AppShell";

export default function CommitteeHome() {
  const [schemes, setSchemes] = useState<any[] | null>(null);
  useEffect(() => { api("/schemes").then(setSchemes).catch(() => setSchemes([])); }, []);
  if (!schemes) return <Spinner />;
  return (
    <div className="space-y-4">
      <SectionTitle sub="Generate the merit list from configured weights, review, adjust with justification, and publish.">
        Merit & Selection
      </SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        {schemes.map((s) => (
          <Link key={s.id} href={`/committee/merit/${s.id}`}>
            <Card className="hover:shadow-md transition">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-lg">{s.code}</span>
                  {s.is_sample && <SampleBadge />}
                </div>
                <Badge className="bg-slate-100 text-slate-600">{s.slots} slots</Badge>
              </div>
              <div className="text-sm text-slate-500 mt-1">{s.name}</div>
              <div className="mt-3 text-xs text-slate-500">
                Weights: {Object.entries(s.merit_criteria.weights).map(([k, v]) => `${k} ${Math.round((v as number) * 100)}%`).join(" · ")}
              </div>
              {Object.keys(s.merit_criteria.quotas || {}).length > 0 && (
                <div className="text-xs text-slate-400 mt-1">
                  Quotas: {Object.entries(s.merit_criteria.quotas).map(([k, v]) => `${k} ${Math.round((v as number) * 100)}%`).join(" · ")}
                </div>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
