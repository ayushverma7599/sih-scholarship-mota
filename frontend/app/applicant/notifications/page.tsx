"use client";
import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, Button, Spinner, Empty, SectionTitle, Badge } from "@/components/ui";
import { Bell } from "lucide-react";

export default function NotificationsPage() {
  const [data, setData] = useState<any>(null);
  const load = () => api("/notifications").then(setData).catch(() => setData({ items: [], unread: 0 }));
  useEffect(() => { load(); }, []);
  if (!data) return <Spinner />;

  const markAll = async () => { await api("/notifications/read-all", { method: "POST" }); load(); };
  const markOne = async (id: number) => { await api(`/notifications/${id}/read`, { method: "POST" }); load(); };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <SectionTitle sub="In-app alerts. Email/SMS are mocked (logged on the server).">Notifications</SectionTitle>
        {data.unread > 0 && <Button variant="ghost" onClick={markAll}>Mark all read</Button>}
      </div>
      {data.items.length === 0 ? <Card><Empty>No notifications yet.</Empty></Card> : (
        <div className="space-y-2">
          {data.items.map((n: any) => (
            <Card key={n.id} className={n.read ? "opacity-70" : ""}>
              <div className="flex gap-3">
                <Bell size={18} className={n.read ? "text-slate-300" : "text-saffron"} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{n.title}</span>
                    {n.channel !== "in_app" && <Badge className="bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200">MOCK {n.channel}</Badge>}
                    {!n.read && <span className="h-2 w-2 rounded-full bg-saffron" />}
                  </div>
                  <div className="text-sm text-slate-600 mt-0.5">{n.message}</div>
                  <div className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</div>
                </div>
                {!n.read && <button onClick={() => markOne(n.id)} className="text-xs text-sky hover:underline self-start">Mark read</button>}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
