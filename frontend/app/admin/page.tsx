"use client";
import React, { useEffect, useState } from "react";
import { api, apiDownload, ApiError } from "@/lib/api";
import { StatCard, Card, Spinner, SectionTitle, Button } from "@/components/ui";
import { BarCard, PieCard, FunnelCard } from "@/components/Charts";
import { inr } from "@/lib/utils";
import { Download } from "lucide-react";

export default function AdminDashboard() {
  const [kpis, setKpis] = useState<any>(null);
  const [charts, setCharts] = useState<any>(null);
  const [perf, setPerf] = useState<any>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const exportReport = async (format: "csv" | "pdf") => {
    setDownloading(format);
    try {
      const ts = new Date().toISOString().slice(0, 10);
      await apiDownload(`/dashboard/reports/export?format=${format}`, `unnati-report-${ts}.${format}`);
    } catch (e) {
      alert(e instanceof ApiError ? `Export failed: ${e.message}` : "Export failed");
    } finally {
      setDownloading(null);
    }
  };

  useEffect(() => {
    api("/dashboard/kpis").then(setKpis).catch(() => {});
    api("/dashboard/charts").then(setCharts).catch(() => {});
    api("/dashboard/officer-performance").then(setPerf).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionTitle sub="Real-time visibility across schemes, states and the selection funnel.">
          Ministry Dashboard
        </SectionTitle>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => exportReport("csv")} loading={downloading === "csv"}>
            <Download size={16} /> CSV
          </Button>
          <Button variant="ghost" onClick={() => exportReport("pdf")} loading={downloading === "pdf"}>
            <Download size={16} /> PDF
          </Button>
        </div>
      </div>

      {!kpis ? <Spinner /> : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard label="Applications" value={kpis.total_applications} />
          <StatCard label="Auto-verified" value={`${kpis.auto_verified_pct}%`} accent="text-cyan-600" />
          <StatCard label="Pending scrutiny" value={kpis.pending_scrutiny} accent="text-amber-600" />
          <StatCard label="Avg processing" value={`${kpis.avg_processing_hours}h`} />
          <StatCard label="Deficiency rate" value={`${kpis.deficiency_rate_pct}%`} accent="text-orange-600" />
          <StatCard label="Selected" value={kpis.selected} accent="text-green-600" />
          <StatCard label="Funds committed" value={inr(kpis.funds_committed)} hint="mock DBT" accent="text-navy" />
        </div>
      )}

      {!charts ? <Spinner /> : (
        <>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            <FunnelCard title="Selection funnel" data={charts.funnel} />
            <PieCard title="Applications by scheme" data={charts.by_scheme} />
            <PieCard title="By gender" data={charts.by_gender} />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <BarCard title="Applications by state" data={charts.by_state.slice(0, 8)} horizontal />
            <BarCard title="By tribe" data={charts.by_tribe.slice(0, 8)} horizontal />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <BarCard title="By course level" data={charts.by_course} />
            <BarCard title="Top deficiency reasons" data={charts.top_deficiencies} horizontal />
          </div>
        </>
      )}

      {perf && (
        <div className="grid md:grid-cols-2 gap-4">
          <Card>
            <SectionTitle>Officer performance</SectionTitle>
            <table className="w-full text-sm">
              <thead className="text-slate-500 text-left"><tr><th className="py-1">Officer</th><th>Actions</th><th>Verified</th></tr></thead>
              <tbody>
                {perf.officers.length === 0 ? <tr><td className="py-2 text-slate-400" colSpan={3}>No data yet.</td></tr> :
                  perf.officers.map((o: any, i: number) => (
                    <tr key={i} className="border-t border-slate-100"><td className="py-1.5">{o.officer}</td><td>{o.actions}</td><td>{o.verified}</td></tr>
                  ))}
              </tbody>
            </table>
          </Card>
          <BarCard title="Backlog by scheme" data={perf.backlog} />
        </div>
      )}
    </div>
  );
}
