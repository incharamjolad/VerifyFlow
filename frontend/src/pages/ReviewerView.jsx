import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  CheckSquare,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Send,
  Eye,
  RefreshCw,
} from "lucide-react";

export default function ReviewerView() {
  const [queue, setQueue] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [docDetails, setDocDetails] = useState(null);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Decision form
  const [remarks, setRemarks] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [decisionError, setDecisionError] = useState("");
  const [decisionSuccess, setDecisionSuccess] = useState("");

  const fetchQueue = async () => {
    try {
      const res = await api.get("/api/reviews/queue");
      setQueue(res.data);
      if (res.data.length > 0 && !selectedDocId) {
        loadDocumentDetails(res.data[0].id);
      } else if (res.data.length === 0) {
        setDocDetails(null);
        setSelectedDocId(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingQueue(false);
    }
  };

  const loadDocumentDetails = async (docId) => {
    setSelectedDocId(docId);
    setLoadingDetails(true);
    setDecisionError("");
    setDecisionSuccess("");
    setRemarks("");
    try {
      const res = await api.get(`/api/reviews/${docId}`);
      setDocDetails(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDetails(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleDecision = async (decision) => {
    if (decision !== "APPROVED" && !remarks.trim()) {
      setDecisionError(`Remarks are required when submitting decision: ${decision.replace("_", " ")}`);
      return;
    }
    setDecisionError("");
    setSubmittingDecision(true);

    try {
      await api.post(`/api/reviews/${selectedDocId}/decision`, {
        decision,
        remarks: remarks.trim(),
      });
      setDecisionSuccess(`Document successfully marked as ${decision.replace("_", " ")}.`);
      // Refresh queue
      const qRes = await api.get("/api/reviews/queue");
      setQueue(qRes.data);
      if (qRes.data.length > 0) {
        loadDocumentDetails(qRes.data[0].id);
      } else {
        setDocDetails(null);
        setSelectedDocId(null);
      }
    } catch (err) {
      setDecisionError(err.response?.data?.detail || "Decision submission failed.");
    } finally {
      setSubmittingDecision(false);
    }
  };

  const getRuleStatusBadge = (status) => {
    switch (status) {
      case "PASS":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">PASS</span>;
      case "WARNING":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">WARNING</span>;
      case "FAIL":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">FAIL</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700">INFO</span>;
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">Reviewer Workspace</h1>
          <p className="text-xs text-slate-500 mt-1">Examine automated findings, inspect documents, and record verification decisions</p>
        </div>
        <button
          onClick={fetchQueue}
          className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Queue ({queue.length})
        </button>
      </div>

      {loadingQueue ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading reviewer queue...</div>
      ) : queue.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center shadow-xs">
          <CheckSquare className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-800">Review Queue is Clear!</h3>
          <p className="text-xs text-slate-400 mt-1">All submitted documents have been reviewed and verified.</p>
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-6">
          {/* Left: Queue List (4 cols) */}
          <div className="col-span-4 bg-white rounded-2xl border border-slate-200/80 p-4 shadow-xs flex flex-col h-[750px]">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-2">
              Pending Submissions ({queue.length})
            </div>
            <div className="overflow-y-auto space-y-2 flex-1 pr-1">
              {queue.map((item) => {
                const active = item.id === selectedDocId;
                return (
                  <button
                    key={item.id}
                    onClick={() => loadDocumentDetails(item.id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition flex flex-col gap-1.5 ${
                      active
                        ? "bg-indigo-50/60 border-indigo-200 text-slate-900 shadow-xs"
                        : "bg-white border-slate-100 hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-semibold text-xs truncate max-w-[180px]">
                        {item.filename || "Document.pdf"}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                        v{item.current_revision || 1}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500">
                      <span className="capitalize">{item.document_type?.replace("_", " ")}</span>
                      <span className={`font-semibold ${
                        (item.risk_score || 0) >= 30 ? "text-amber-600" : "text-slate-500"
                      }`}>
                        Risk: {item.risk_score || 0}
                      </span>
                    </div>

                    <div className="text-[10px] text-slate-400 truncate">
                      By: {item.owner_name || item.owner_email || "Applicant"}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right: Inspection Workspace (8 cols) */}
          <div className="col-span-8 bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs h-[750px] flex flex-col overflow-y-auto">
            {loadingDetails || !docDetails ? (
              <div className="m-auto text-center text-xs text-slate-400">Loading document inspection...</div>
            ) : (
              <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-indigo-600" />
                      {docDetails.revision?.filename || docDetails.filename || "Document.pdf"}
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Revision v{docDetails.current_revision || 1} · SHA-256:{" "}
                      <span className="font-mono text-[10px]">{docDetails.revision?.sha256}</span>
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                      Risk Score: {docDetails.verification_results?.risk_score || 0}/100
                    </span>
                  </div>
                </div>

                {/* Split Document View: PDF on left, Findings on right */}
                <div className="grid grid-cols-2 gap-4">
                  {/* PDF Viewer */}
                  <div className="border border-slate-200 rounded-xl overflow-hidden bg-slate-100 h-80 flex flex-col">
                    <div className="bg-slate-200 px-3 py-1.5 text-[10px] font-semibold text-slate-600 uppercase tracking-wider flex items-center justify-between">
                      <span>Document Preview</span>
                      <a
                        href={`/api/documents/${docDetails.id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-600 hover:underline"
                      >
                        Open In Tab ↗
                      </a>
                    </div>
                    <iframe
                      src={`/api/documents/${docDetails.id}/download#toolbar=0`}
                      title="PDF Preview"
                      className="w-full h-full border-0"
                    />
                  </div>

                  {/* Extracted Fields */}
                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 flex flex-col justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                        OCR Extracted Fields
                      </div>
                      <div className="space-y-2 text-xs">
                        <div>
                          <span className="text-slate-400 block text-[10px]">Candidate Name:</span>
                          <span className="font-medium text-slate-900">
                            {docDetails.extractions?.fields?.candidate_name || "(Not detected)"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Registration / Cert #:</span>
                          <span className="font-medium text-slate-900">
                            {docDetails.extractions?.fields?.registration_number || "(Not detected)"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Issue Date:</span>
                          <span className="font-medium text-slate-900">
                            {docDetails.extractions?.fields?.issue_date || "(Not detected)"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-200/60 text-[10px] text-slate-400">
                      OCR Confidence: {Math.round((docDetails.extractions?.confidence || 0) * 100)}%
                    </div>
                  </div>
                </div>

                {/* Per-Rule Verification Checks */}
                <div>
                  <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
                    Verification Rule Findings
                  </h3>
                  <div className="space-y-2">
                    {docDetails.verification_results?.rule_results?.map((rule, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl border border-slate-200 bg-white flex items-start justify-between gap-3 text-xs"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[11px] font-semibold text-slate-900">
                              {rule.rule_id}
                            </span>
                            <span className="text-slate-600 font-medium">{rule.rule_name}</span>
                          </div>
                          <p className="text-slate-600 text-[11px]">{rule.explanation}</p>
                          {rule.evidence && (
                            <p className="text-slate-400 text-[10px] font-mono">
                              Evidence: {rule.evidence}
                            </p>
                          )}
                        </div>
                        <div>{getRuleStatusBadge(rule.status)}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Decision Panel */}
                <div className="pt-4 border-t border-slate-200">
                  <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Review Decision
                  </h3>

                  {decisionError && (
                    <div className="mb-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>{decisionError}</span>
                    </div>
                  )}

                  {decisionSuccess && (
                    <div className="mb-3 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{decisionSuccess}</span>
                    </div>
                  )}

                  <div className="mb-3">
                    <label className="block text-[11px] text-slate-500 mb-1">
                      Reviewer Remarks (Required for Reject & Correction):
                    </label>
                    <textarea
                      rows={2}
                      value={remarks}
                      onChange={(e) => setRemarks(e.target.value)}
                      placeholder="Add specific observations, missing pages, or clarification notes..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                    />
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      disabled={submittingDecision}
                      onClick={() => handleDecision("APPROVED")}
                      className="flex-1 py-2 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 shadow-xs disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Approve
                    </button>
                    <button
                      disabled={submittingDecision}
                      onClick={() => handleDecision("CORRECTION_REQUESTED")}
                      className="flex-1 py-2 px-4 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 shadow-xs disabled:opacity-50"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Request Correction
                    </button>
                    <button
                      disabled={submittingDecision}
                      onClick={() => handleDecision("REJECTED")}
                      className="flex-1 py-2 px-4 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-medium transition flex items-center justify-center gap-1.5 shadow-xs disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

