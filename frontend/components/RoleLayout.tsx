"use client";
import React from "react";
import { Role, useRequireRole } from "@/lib/auth";
import AppShell from "./AppShell";
import { Spinner } from "./ui";

export default function RoleLayout({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user, loading } = useRequireRole(roles);
  if (loading || !user) {
    return <div className="min-h-screen flex items-center justify-center"><Spinner /></div>;
  }
  if (!roles.includes(user.role)) return null;
  return <AppShell>{children}</AppShell>;
}
