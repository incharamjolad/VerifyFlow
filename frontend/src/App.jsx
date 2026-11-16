import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ApplicantView from "./pages/ApplicantView";
import ReviewerView from "./pages/ReviewerView";
import AdminView from "./pages/AdminView";
import AuditorView from "./pages/AuditorView";

function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9F9FB] flex items-center justify-center text-xs text-slate-400">
        Authenticating session...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // If not allowed, redirect to their role home
    if (user.role === "admin") return <Navigate to="/admin" replace />;
    if (user.role === "reviewer") return <Navigate to="/reviewer" replace />;
    if (user.role === "auditor") return <Navigate to="/auditor" replace />;
    return <Navigate to="/applicant" replace />;
  }

  return <Layout>{children}</Layout>;
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "admin") return <Navigate to="/admin" replace />;
  if (user.role === "reviewer") return <Navigate to="/reviewer" replace />;
  if (user.role === "auditor") return <Navigate to="/auditor" replace />;
  return <Navigate to="/applicant" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route
            path="/applicant"
            element={
              <ProtectedRoute allowedRoles={["applicant", "admin"]}>
                <ApplicantView />
              </ProtectedRoute>
            }
          />

          <Route
            path="/reviewer"
            element={
              <ProtectedRoute allowedRoles={["reviewer", "admin", "auditor"]}>
                <ReviewerView />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <AdminView />
              </ProtectedRoute>
            }
          />

          <Route
            path="/auditor"
            element={
              <ProtectedRoute allowedRoles={["auditor", "admin"]}>
                <AuditorView />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<RootRedirect />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
