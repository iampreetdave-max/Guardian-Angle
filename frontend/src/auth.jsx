import { createContext, useContext, useEffect, useState, useCallback } from "react";
import * as API from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On load, if a token exists, resolve the current user.
  useEffect(() => {
    if (!API.getToken()) {
      setLoading(false);
      return;
    }
    API.authMe()
      .then(setUser)
      .catch(() => API.setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await API.authLogin({ email, password });
    API.setToken(res.token);
    setUser(res.user);
    return res.user;
  }, []);

  const register = useCallback(async (payload) => {
    const res = await API.authRegister(payload);
    API.setToken(res.token);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await API.authLogout();
    } catch {
      /* ignore */
    }
    API.setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);

export const isStaff = (u) => u && ["officer", "lead", "admin"].includes(u.role);
export const isLead = (u) => u && ["lead", "admin"].includes(u.role);
export const isAdmin = (u) => u && u.role === "admin";
