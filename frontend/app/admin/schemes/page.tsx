"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, Badge, Button, Spinner, SectionTitle } from "@/components/ui";
import { SampleBadge } from "@/components/AppShell";
import { Plus, Settings2 } from "lucide-react";

export default function SchemesList() {
  const [schemes, setSchemes] = useState<any[] | null>(null);
  useEffect(() => { api("/schemes").then(setSchemes).catch(() => setSchemes([])); }, []);
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionTitle sub="Create and edit schemes without code — rules, documents and merit weights are all data.">
          Scheme Configuration
        </SectionTitle>
        <Link href="/admin/schemes/new"><Button variant="accent"><Plus size={16} /> New scheme</Button></Link>
      </div>
      {!schemes ? <Spinner /> : (
        <div className="grid md:grid-cols-2 gap-4">
          {schemes.map((s) => (
            <Card key={s.id}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-lg">{s.code}</span>
                    {s.is_sample && <SampleBadge />}
                    {!s.is_active && <Badge className="bg-slate-100 text-slate-500">Inactive</Badge>}
                  </div>
                  <div className="text-sm text-slate-500">{s.name}</div>
                </div>
                <Link href={`/admin/schemes/${s.id}`}><Button variant="ghost"><Settings2 size={16} /> Configure</Button></Link>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-4 text-center text-xs">
                <div className="bg-slate-50 rounded p-2"><div className="font-semibold text-sm">{s.rules?.rules?.length || 0}</div>rules</div>
                <div className="bg-slate-50 rounded p-2"><div className="font-semibold text-sm">{s.documents?.length || 0}</div>documents</div>
                <div className="bg-slate-50 rounded p-2"><div className="font-semibold text-sm">{Object.keys(s.merit_criteria?.weights || {}).length}</div>merit criteria</div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
