import { useState, useEffect } from "react";

export interface UserProfile {
  name: string;
  email: string;
  username: string;
  role?: string;
}

const USER_STORAGE_KEY = "sih-user";
const TOKEN_STORAGE_KEY = "sih-token";
const AUTH_EVENT = "sih-auth-change";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || sessionStorage.getItem(TOKEN_STORAGE_KEY) || null;
  } catch {
    return null;
  }
}

export function getUser(): UserProfile | null {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY) || sessionStorage.getItem("sih-auth");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed.email && !parsed.username && !parsed.name) return null;
    return {
      name: parsed.name || parsed.username || (parsed.email ? parsed.email.split("@")[0] : "Officer"),
      email: parsed.email || "",
      username: parsed.username || parsed.name || (parsed.email ? parsed.email.split("@")[0] : "Officer"),
      role: parsed.role || "officer",
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
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    sessionStorage.setItem("sih-auth", JSON.stringify(user));
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // ignore storage errors
  }
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function logout(): void {
  try {
    localStorage.removeItem(USER_STORAGE_KEY);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem("sih-auth");
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem("sih-pending");
  } catch {
    // ignore storage errors
  }
  window.dispatchEvent(new Event(AUTH_EVENT));
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
