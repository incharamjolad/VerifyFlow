import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("vf_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/api/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem("vf_token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const cleanEmail = email.trim();
    const res = await api.post("/api/auth/login", {
      email: cleanEmail,
      username: cleanEmail,
      password: password,
    });
    const { access_token, user: userData } = res.data;
    localStorage.setItem("vf_token", access_token);
    setUser(userData);
    return userData;
  };

  const register = async (name, email, password) => {
    await api.post("/api/auth/register", { name, email, password });
    return login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("vf_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

