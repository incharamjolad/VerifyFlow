import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  Users,
  FileCheck2,
  Clock,
  XCircle,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  ShieldAlert,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

export default function AdminView() {
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updatingUser, setUpdatingUser] = useState(null);
  const [updateMsg, setUpdateMsg] = useState("");

  const fetchData = async () => {
    try {
      const [anaRes, usersRes] = await Promise.all([
        api.get("/api/analytics/overview"),
        api.get("/api/admin/users"),
      ]);
      setAnalytics(anaRes.data);
      setUsers(usersRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRoleChange = async (userId, newRole) => {
    setUpdatingUser(userId);
    setUpdateMsg("");
    try {
      await api.patch(`/api/admin/users/${userId}/role`, { role: newRole });
      setUpdateMsg("Role updated successfully.");
      fetchData();
    } catch (err) {
      setUpdateMsg(err.response?.data?.detail || "Failed to update role.");
    } finally {
      setUpdatingUser(null);
    }
  };

  const chartData = analytics
    ? [
        { name: "Under Review", count: analytics.under_review, color: "#6366F1" },
        { name: "Approved", count: analytics.approved, color: "#10B981" },
        { name: "Correction", count: analytics.correction_requested, color: "#F59E0B" },
        { name: "Rejected", count: analytics.rejected, color: "#EF4444" },
        { name: "Failed", count: analytics.processing_failed, color: "#DC2626" },
      ]
    : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">Admin & System Analytics</h1>
          <p className="text-xs text-slate-500 mt-1">Tenant overview, document pipeline distribution, and user role management</p>
        </div>
        <button
          onClick={fetchData}
          className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Analytics
        </button>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading administrative metrics...</div>
      ) : (
        <div className="space-y-8">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="text-xs font-medium text-slate-500 mb-1">Total Submissions</div>
              <div className="text-2xl font-bold text-slate-900">{analytics?.total_documents || 0}</div>
            </div>
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="text-xs font-medium text-slate-500 mb-1">Active Review Queue</div>
              <div className="text-2xl font-bold text-indigo-600">{analytics?.under_review || 0}</div>
            </div>
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="text-xs font-medium text-slate-500 mb-1">Approved Documents</div>
              <div className="text-2xl font-bold text-emerald-600">{analytics?.approved || 0}</div>
            </div>
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="text-xs font-medium text-slate-500 mb-1">Audit Ledger Events</div>
              <div className="text-2xl font-bold text-slate-700">{analytics?.total_audit_events || 0}</div>
            </div>
          </div>

          {/* Status Distribution Chart */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
            <h2 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-indigo-600" />
              Document Status Pipeline Distribution
            </h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                  <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94A3B8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FFFFFF",
                      borderRadius: "12px",
                      border: "1px solid #E2E8F0",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* User Role Management Table */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <Users className="w-4 h-4 text-indigo-600" />
                  User Role & Permissions Management
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">Assign administrative, reviewer, and auditor access rights</p>
              </div>
              {updateMsg && <span className="text-xs font-medium text-emerald-600">{updateMsg}</span>}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/50 text-slate-500 uppercase tracking-wider text-[10px] font-semibold border-b border-slate-100">
                  <tr>
                    <th className="px-6 py-3">User</th>
                    <th className="px-6 py-3">Email Address</th>
                    <th className="px-6 py-3">Account Status</th>
                    <th className="px-6 py-3">Current Role</th>
                    <th className="px-6 py-3 text-right">Change Role</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/50 transition">
                      <td className="px-6 py-4 font-medium text-slate-900">{u.name || "User"}</td>
                      <td className="px-6 py-4 text-slate-600">{u.email}</td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Active
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase bg-slate-100 text-slate-800">
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <select
                          disabled={updatingUser === u.id}
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                        >
                          <option value="applicant">Applicant</option>
                          <option value="reviewer">Reviewer</option>
                          <option value="auditor">Auditor</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

