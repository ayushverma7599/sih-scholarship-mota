"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, getToken } from "./api";

export type Role = "applicant" | "scrutiny" | "committee" | "admin";
export type User = {
  id: number; email: string; full_name: string; role: Role;
  campus_verified: boolean; profile: Record<string, any>;
};

const AuthCtx = createContext<{
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<void>;
}>({ user: null, loading: true, login: async () => ({} as User), logout: () => {}, refresh: async () => {} });

export const HOME_BY_ROLE: Record<Role, string> = {
  applicant: "/applicant",
  scrutiny: "/officer",
  committee: "/committee",
  admin: "/admin",
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    if (!getToken()) { setUser(null); setLoading(false); return; }
    try {
      const me = await api<User>("/auth/me");
      setUser(me);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const login = async (email: string, password: string) => {
    const res = await api<{ access_token: string }>("/auth/login", {
      method: "POST", body: { email, password }, auth: false,
    });
    setToken(res.access_token);
    const me = await api<User>("/auth/me");
    setUser(me);
    return me;
  };

  const logout = () => { setToken(null); setUser(null); };

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout, refresh }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);

/** Client-side guard: redirects to /login if not authed or wrong role. */
export function useRequireRole(roles: Role[]) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (loading) return;
    if (!user) { router.replace("/"); return; }
    if (!roles.includes(user.role)) { router.replace(HOME_BY_ROLE[user.role]); }
  }, [user, loading, roles, router]);
  return { user, loading };
}
