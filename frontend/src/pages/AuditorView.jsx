import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  ShieldCheck,
  ShieldAlert,
  History,
  RefreshCw,
  CheckCircle2,
  XCircle,
  FileCode,
  X,
} from "lucide-react";

export default function AuditorView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async () => {
    try {
      const res = await api.get("/api/audit");
      setLogs(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const res = await api.get("/api/audit/verify");
      setVerificationResult(res.data);
    } catch (err) {
      setVerificationResult({ valid: false, error: "Network or server failure during chain verification." });
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    handleVerifyChain();
  }, []);

  return (
    <div>
      {/* Top Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">Audit Trail & Cryptographic Ledger</h1>
          <p className="text-xs text-slate-500 mt-1">
            Immutable-style tamper-evident SHA-256 hash-chained log of all verification activities
          </p>
        </div>

        <div className="flex items-center gap-3">
          {verificationResult && (
            <div
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold ${
                verificationResult.valid
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-rose-50 text-rose-700 border-rose-200"
              }`}
            >
              {verificationResult.valid ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Chain Verified ({verificationResult.total_events} events intact)</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                  <span>
                    Tampering Detected (Sequence #{verificationResult.broken_at_sequence})
                  </span>
                </>
              )}
            </div>
          )}

          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-medium shadow-xs transition disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            {verifying ? "Verifying..." : "Verify Hash Chain"}
          </button>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <History className="w-4 h-4 text-indigo-600" />
            Sequential Hash Chain Events
          </h2>
          <button
            onClick={fetchLogs}
            className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading audit ledger...</div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">No audit events recorded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/50 text-slate-500 uppercase tracking-wider text-[10px] font-semibold border-b border-slate-100">
                <tr>
                  <th className="px-5 py-3">Seq #</th>
                  <th className="px-5 py-3">Action</th>
                  <th className="px-5 py-3">Entity Type</th>
                  <th className="px-5 py-3">Entity ID</th>
                  <th className="px-5 py-3">Actor</th>
                  <th className="px-5 py-3">Timestamp (UTC)</th>
                  <th className="px-5 py-3">Event Hash</th>
                  <th className="px-5 py-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 font-mono text-[11px]">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/50 transition">
                    <td className="px-5 py-3.5 font-bold text-slate-900">#{log.sequence}</td>
                    <td className="px-5 py-3.5 font-sans font-semibold text-xs text-indigo-600">
                      {log.action}
                    </td>
                    <td className="px-5 py-3.5 font-sans capitalize text-slate-600">{log.entity_type}</td>
                    <td className="px-5 py-3.5 text-slate-500 truncate max-w-[100px]" title={log.entity_id}>
                      {log.entity_id ? `${String(log.entity_id).substring(0, 8)}...` : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 truncate max-w-[90px]" title={log.actor_id}>
                      {log.actor_id ? `${String(log.actor_id).substring(0, 8)}...` : "system"}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-[10px] font-sans">
                      {log.timestamp || log.created_at}
                    </td>
                    <td className="px-5 py-3.5 text-slate-400 text-[10px]" title={log.event_hash}>
                      {log.event_hash ? `${log.event_hash.substring(0, 10)}...` : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-right font-sans">
                      <button
                        onClick={() => setSelectedLog(log)}
                        className="px-2.5 py-1 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 text-[10px] font-medium transition"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inspect Event Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-indigo-600" />
                Audit Event #{selectedLog.sequence}: {selectedLog.action}
              </h3>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Event Hash (SHA-256):</span>
                <span className="font-mono text-[11px] text-slate-800 break-all select-all">
                  {selectedLog.event_hash}
                </span>
              </div>

              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Previous Hash:</span>
                <span className="font-mono text-[11px] text-slate-500 break-all select-all">
                  {selectedLog.previous_hash}
                </span>
              </div>

              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Canonical Details Payload:</span>
                <pre className="p-3 mt-1 rounded-xl bg-slate-900 text-slate-100 text-[11px] font-mono overflow-x-auto max-h-48">
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-1.5 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

