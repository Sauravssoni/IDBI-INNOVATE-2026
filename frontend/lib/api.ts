export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  ((process.env.NODE_ENV === "development" || process.env.NODE_ENV === "test") ? "http://localhost:8000" : "");

export function getCsrfToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith("vyapar_csrf_token="));
  return match ? decodeURIComponent(match.split("=")[1]) : "";
}

export async function apiFetch<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data?: T; error?: string; status: number }> {
  const url = `${API_BASE_URL}${endpoint}`;
  const method = (options.method || "GET").toUpperCase();

  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };

  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      credentials: "include", // Essential for sending/receiving cookies
    });

    let data;
    const contentType = res.headers?.get ? res.headers.get("content-type") : null;
    if (contentType && contentType.includes("application/json")) {
      data = await res.json();
    } else {
      const text = await res.text();
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }

    if (!res.ok) {
      if (res.status === 401) {
        if (typeof localStorage !== "undefined") {
          localStorage.removeItem("vyapar_user");
        }
        // Avoid redirecting if the URL we requested was /api/auth/me 
        // AND it was a background refresh that might be racing with a login.
        // Actually, let's only redirect if we're not on the login page.
        // To fix the race condition, if a login just occurred, we shouldn't hard redirect.
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
          // If the request that got 401 was for /api/auth/me, we shouldn't hard redirect 
          // if we are already handling Auth state in React. 
          // Let AuthContext handle it!
          if (endpoint !== "/api/auth/me") {
             window.location.href = "/login";
          }
        }
      }

      let errorMsg = `HTTP error ${res.status}`;
      if (typeof data === "object" && data !== null) {
        if (Array.isArray(data.detail)) {
          errorMsg = data.detail
            .map((err: Record<string, unknown>) => err.msg || JSON.stringify(err))
            .join(", ");
        } else if (typeof data.detail === "string") {
          errorMsg = data.detail;
        } else if (typeof data.detail === "object" && data.detail !== null) {
          errorMsg = (data.detail.code && data.detail.message)
            ? `${data.detail.code}: ${data.detail.message}`
            : (data.detail.message || JSON.stringify(data.detail));
        } else if (data.message) {
          errorMsg = data.message;
        } else if (data.detail) {
          errorMsg = String(data.detail);
        }
      } else if (typeof data === "string" && data.trim()) {
        errorMsg = data;
      }
      return {
        error: errorMsg,
        status: res.status,
        data: (typeof data === "object" && data !== null && data.detail !== undefined) ? data.detail : data
      };
    }

    return { data, status: res.status };
  } catch (err) {
    return {
      error: (err instanceof Error ? err.message : String(err)) || "Network request failed. Ensure backend is running.",
      status: 0,
    };
  }
}

