"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import mixpanel from "mixpanel-browser";
import { clearDraft, draftStorage } from "@/lib/briefDraft";

interface User {
  id: number;
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, name: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const MIXPANEL_TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN;

function identifyUser(user: User) {
  if (MIXPANEL_TOKEN) {
    mixpanel.identify(String(user.id));
    mixpanel.people.set({ $email: user.email, $name: user.name });
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      const res = await fetch(`/api/me`, { credentials: "include" });
      const data = res.ok ? await res.json() : null;
      setUser(data);
      if (data) identifyUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();

    // A page restored from the back/forward cache never remounts, so it carries
    // whatever session state it was frozen with — press Back onto a page you
    // last saw while signed out and the navbar still says "Login" (#161). The
    // browser announces the restore with `persisted`, and that is the one
    // moment this provider cannot learn about any other way.
    function handlePageShow(event: PageTransitionEvent) {
      if (event.persisted) refreshUser();
    }

    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Login failed");
    }
    const data = await res.json();
    setUser(data);
    identifyUser(data);
  }, []);

  const signup = useCallback(
    async (email: string, name: string, password: string) => {
      const res = await fetch(`/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, name, password }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Signup failed");
      }
      const data = await res.json();
      setUser(data);
      identifyUser(data);
    },
    [],
  );

  const logout = useCallback(async () => {
    await fetch(`/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    setUser(null);
    // The saved brief form (#160) belongs to the person who typed it, not to
    // the tab — whoever signs in next must not find it waiting for them.
    clearDraft(draftStorage());
    router.push("/");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
