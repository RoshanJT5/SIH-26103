import { useState, useEffect } from "react";

export interface UserProfile {
  name: string;
  email: string;
  username: string;
  role?: string;
  lastLoginAt?: string;
}

const USER_STORAGE_KEY = "sih-user-session";
const TOKEN_STORAGE_KEY = "sih-token-session";
const LEGACY_USER_KEY = "sih-user";
const LEGACY_TOKEN_KEY = "sih-token";
const AUTH_EVENT = "sih-auth-change";

export function getToken(): string | null {
  try {
    return (
      localStorage.getItem(TOKEN_STORAGE_KEY) ||
      sessionStorage.getItem(TOKEN_STORAGE_KEY) ||
      localStorage.getItem(LEGACY_TOKEN_KEY) ||
      sessionStorage.getItem(LEGACY_TOKEN_KEY) ||
      _getCookie("access_token") ||
      null
    );
  } catch {
    return null;
  }
}

export function getUser(): UserProfile | null {
  try {
    const raw =
      localStorage.getItem(USER_STORAGE_KEY) ||
      sessionStorage.getItem(USER_STORAGE_KEY) ||
      localStorage.getItem(LEGACY_USER_KEY) ||
      sessionStorage.getItem("sih-auth");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed.email && !parsed.username && !parsed.name) return null;
    return {
      name: parsed.name || parsed.username || (parsed.email ? parsed.email.split("@")[0] : "Officer"),
      email: parsed.email || "",
      username: parsed.username || parsed.name || (parsed.email ? parsed.email.split("@")[0] : "Officer"),
      role: parsed.role || "officer",
      lastLoginAt: parsed.lastLoginAt || undefined,
    };
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getUser() !== null;
}

export function setUser(user: UserProfile, token?: string): void {
  try {
    const payload = {
      ...user,
      lastLoginAt: user.lastLoginAt || new Date().toISOString(),
    };
    const serialized = JSON.stringify(payload);

    // 1. Persistent Storage (survives browser close/restart)
    localStorage.setItem(USER_STORAGE_KEY, serialized);
    localStorage.setItem(LEGACY_USER_KEY, serialized);

    // 2. Session Storage (active tab backup)
    sessionStorage.setItem(USER_STORAGE_KEY, serialized);
    sessionStorage.setItem("sih-auth", serialized);

    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
      localStorage.setItem(LEGACY_TOKEN_KEY, token);
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
      sessionStorage.setItem(LEGACY_TOKEN_KEY, token);
      _setCookie("access_token", token, 30 * 24 * 60 * 60); // 30 days
    }
  } catch {
    // ignore storage quota errors
  }
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function logout(): void {
  try {
    // Completely wipe persistent and session storage
    localStorage.removeItem(USER_STORAGE_KEY);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(LEGACY_USER_KEY);
    localStorage.removeItem(LEGACY_TOKEN_KEY);

    sessionStorage.removeItem(USER_STORAGE_KEY);
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(LEGACY_TOKEN_KEY);
    sessionStorage.removeItem("sih-auth");
    sessionStorage.removeItem("sih-pending");

    // Clear session cookie
    _deleteCookie("access_token");
  } catch {
    // ignore errors
  }
  window.dispatchEvent(new Event(AUTH_EVENT));
}

function _setCookie(name: string, value: string, maxAgeSec: number): void {
  if (typeof document === "undefined") return;
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSec}; SameSite=Lax`;
}

function _getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^|;\\s*)" + encodeURIComponent(name) + "=([^;]*)"));
  return match ? decodeURIComponent(match[2]) : null;
}

function _deleteCookie(name: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `${encodeURIComponent(name)}=; path=/; max-age=0; SameSite=Lax`;
}

export function useCurrentUser() {
  const [user, setUserState] = useState<UserProfile | null>(getUser);
  const [token, setTokenState] = useState<string | null>(getToken);

  useEffect(() => {
    function handleAuthChange() {
      setUserState(getUser());
      setTokenState(getToken());
    }

    window.addEventListener(AUTH_EVENT, handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    return () => {
      window.removeEventListener(AUTH_EVENT, handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, []);

  return {
    user,
    token,
    isAuthenticated: !!user,
    updateUser: setUser,
    logout,
  };
}
