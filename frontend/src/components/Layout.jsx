import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  ShieldCheck,
  FileText,
  CheckSquare,
  BarChart2,
  Users,
  History,
  LogOut,
  User,
} from "lucide-react";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const role = user?.role || "applicant";

  const getNavLinks = () => {
    const links = [];
    if (role === "applicant" || role === "admin") {
      links.push({
        path: "/applicant",
        label: "My Documents",
        icon: FileText,
      });
    }
    if (role === "reviewer" || role === "admin") {
      links.push({
        path: "/reviewer",
        label: "Review Queue",
        icon: CheckSquare,
      });
    }
    if (role === "admin") {
      links.push({
        path: "/admin",
        label: "Admin & Analytics",
        icon: BarChart2,
      });
    }
    if (role === "auditor" || role === "admin") {
      links.push({
        path: "/auditor",
        label: "Audit Ledger",
        icon: History,
      });
    }
    return links;
  };

  const navLinks = getNavLinks();

  const getRoleBadgeColor = (r) => {
    switch (r) {
      case "admin":
        return "bg-purple-100 text-purple-700 border-purple-200";
      case "reviewer":
        return "bg-blue-100 text-blue-700 border-blue-200";
      case "auditor":
        return "bg-amber-100 text-amber-700 border-amber-200";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9FB] flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200/80 flex flex-col justify-between shrink-0">
        <div>
          {/* Header */}
          <div className="h-16 flex items-center px-6 border-b border-slate-100 gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="font-semibold text-slate-900 text-sm tracking-tight">VerifyFlow</span>
              <span className="block text-[10px] text-slate-400 uppercase tracking-wider font-medium">Platform</span>
            </div>
          </div>

          {/* Nav Items */}
          <nav className="p-4 space-y-1">
            <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Navigation
            </div>
            {navLinks.map((item) => {
              const Icon = item.icon;
              const active = location.pathname.startsWith(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition ${
                    active
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${active ? "text-indigo-600" : "text-slate-400"}`} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 shrink-0">
                <User className="w-4 h-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-medium text-slate-900 truncate">{user?.name || "User"}</div>
                <div className="text-[11px] text-slate-400 truncate">{user?.email}</div>
              </div>
            </div>
            <span
              className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border ${getRoleBadgeColor(
                role
              )}`}
            >
              {role}
            </span>
          </div>

          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}

