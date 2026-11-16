import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ShieldCheck, KeyRound, AlertCircle, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const userData = await login(email, password);
      if (userData.role === "admin") navigate("/admin");
      else if (userData.role === "reviewer") navigate("/reviewer");
      else if (userData.role === "auditor") navigate("/auditor");
      else navigate("/applicant");
    } catch (err) {
      if (!err.response) {
        setError("Cannot reach server");
      } else if (err.response.status === 401) {
        setError("Wrong email or password");
      } else {
        setError(err.response.data?.detail || "An unexpected error occurred");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const fillDemo = (demoEmail) => {
    setEmail(demoEmail);
    setPassword("VerifyDemo#2026!x");
    setError("");
  };

  return (
    <div className="min-h-screen bg-[#F9F9FB] flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-600 text-white mb-3 shadow-sm">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">VerifyFlow</h1>
          <p className="text-sm text-slate-500 mt-1">Intelligent Document Verification & Audit Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white border border-slate-200/80 rounded-2xl p-8 shadow-sm">
          <h2 className="text-lg font-medium text-slate-900 mb-6">Sign in to your account</h2>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">Email address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {submitting ? "Signing in..." : "Sign in"}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Demo Logins Section */}
          <div className="mt-8 pt-6 border-t border-slate-100">
            <div className="text-xs font-medium text-slate-500 mb-2.5 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5" />
              <span>Click to load seeded demo accounts:</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillDemo("applicant@verifyflow.com")}
                className="px-2.5 py-2 text-left rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium transition"
              >
                👤 Applicant
              </button>
              <button
                type="button"
                onClick={() => fillDemo("reviewer@verifyflow.com")}
                className="px-2.5 py-2 text-left rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium transition"
              >
                🔍 Reviewer
              </button>
              <button
                type="button"
                onClick={() => fillDemo("admin@verifyflow.com")}
                className="px-2.5 py-2 text-left rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium transition"
              >
                ⚙️ Admin
              </button>
              <button
                type="button"
                onClick={() => fillDemo("auditor@verifyflow.com")}
                className="px-2.5 py-2 text-left rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium transition"
              >
                📜 Auditor
              </button>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-500 mt-6">
          Don't have an account?{" "}
          <Link to="/register" className="text-indigo-600 hover:underline font-medium">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
}

