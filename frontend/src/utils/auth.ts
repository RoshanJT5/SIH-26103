import { useState, useEffect } from "react";

export interface UserProfile {
  name: string;
  email: string;
  username: string;
}

const STORAGE_KEY = "sih-user";
const AUTH_EVENT = "sih-auth-change";

export function getUser(): UserProfile | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem("sih-auth");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed.email && !parsed.username && !parsed.name) return null;
    return {
      name: parsed.name || parsed.username || (parsed.email ? parsed.email.split("@")[0] : "Officer"),
      email: parsed.email || "",
      username: parsed.username || parsed.name || (parsed.email ? parsed.email.split("@")[0] : "Officer"),
    };
  } catch {
    return null;
  }
}

export function setUser(user: UserProfile): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  sessionStorage.setItem("sih-auth", JSON.stringify(user));
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function logout(): void {
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem("sih-auth");
  sessionStorage.removeItem("sih-pending");
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function useCurrentUser() {
  const [user, setUserState] = useState<UserProfile | null>(getUser);

  useEffect(() => {
    function handleAuthChange() {
      setUserState(getUser());
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
    updateUser: setUser,
    logout,
  };
}
