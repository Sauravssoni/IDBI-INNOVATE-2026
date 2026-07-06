"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { ProtectedRoute } from "./ProtectedRoute";
import { BankerShell } from "./BankerShell";

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();

  if (pathname === "/login") {
    return <>{children}</>;
  }

  return (
    <ProtectedRoute>
      <BankerShell>{children}</BankerShell>
    </ProtectedRoute>
  );
};
