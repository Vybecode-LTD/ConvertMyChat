import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import type { UserData } from "@/types";
import { getMe } from "@/services/api";

interface AuthCtx {
  user: UserData | null;
  token: string | null;
  loading: boolean;
  setAuth: (token: string, user: UserData) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  user: null, token: null, loading: true,
  setAuth: () => {}, logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserData | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("cmc_token");
    if (saved) {
      setToken(saved);
      getMe()
        .then((u) => setUser(u))
        .catch(() => { localStorage.removeItem("cmc_token"); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const setAuth = useCallback((t: string, u: UserData) => {
    localStorage.setItem("cmc_token", t);
    setToken(t);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("cmc_token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
