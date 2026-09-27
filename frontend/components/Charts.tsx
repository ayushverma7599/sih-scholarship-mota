"use client";
import React from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  PieChart, Pie, Legend, CartesianGrid,
} from "recharts";

const PALETTE = ["#1e3a5f", "#ea7317", "#137a4b", "#0369a1", "#7c3aed", "#b45309", "#0891b2", "#be123c"];

type Datum = { label: string; value: number };

export function BarCard({ title, data, horizontal }: { title: string; data: Datum[]; horizontal?: boolean }) {
  return (
    <div className="card p-4">
      <div className="text-sm font-medium text-slate-600 mb-2">{title}</div>
      <ResponsiveContainer width="100%" height={220}>
        {horizontal ? (
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
            </Bar>
          </BarChart>
        ) : (
          <BarChart data={data} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef2f7" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} angle={data.length > 5 ? -20 : 0} textAnchor={data.length > 5 ? "end" : "middle"} height={data.length > 5 ? 50 : 30} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

export function PieCard({ title, data }: { title: string; data: Datum[] }) {
  return (
    <div className="card p-4">
      <div className="text-sm font-medium text-slate-600 mb-2">{title}</div>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={75} label={{ fontSize: 11 }}>
            {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
          </Pie>
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FunnelCard({ title, data }: { title: string; data: Datum[] }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="card p-4">
      <div className="text-sm font-medium text-slate-600 mb-3">{title}</div>
      <div className="space-y-2">
        {data.map((d, i) => (
          <div key={i}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-600">{d.label}</span>
              <span className="font-medium">{d.value}</span>
            </div>
            <div className="h-6 bg-slate-100 rounded overflow-hidden">
              <div className="h-full rounded" style={{ width: `${(d.value / max) * 100}%`, background: PALETTE[i % PALETTE.length] }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
