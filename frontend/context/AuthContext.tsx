"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { apiFetch } from "@/lib/api";

export interface User {
  id: string;
  full_name: string;
  role: "CREDIT_ANALYST" | "SANCTIONING_AUTHORITY" | "RELATIONSHIP_MANAGER" | "SYSTEM_ADMIN" | string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  demoLogin: (role: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    setLoading(true);
    const { data, status } = await apiFetch<User>("/api/auth/me");
    if (status === 200 && data && data.id) {
      setUser(data);
    } else {
      setUser(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    const { data, status, error } = await apiFetch<User>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (status === 200 && data && data.id) {
      setUser(data);
      return { success: true };
    }
    return { success: false, error: error || "Authentication failed" };
  };

  const demoLogin = async (role: string): Promise<{ success: boolean; error?: string }> => {
    const { data, status, error } = await apiFetch<User>("/api/auth/demo/session", {
      method: "POST",
      body: JSON.stringify({ role }),
    });

    if (status === 200 && data && data.id) {
      setUser(data);
      return { success: true };
    }
    return { success: false, error: error || "Guided demo access is unavailable in this environment." };
  };

  const logout = async () => {
    await apiFetch("/api/auth/logout", { method: "POST" });
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, demoLogin, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
