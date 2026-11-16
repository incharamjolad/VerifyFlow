import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  Upload,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Download,
  RefreshCw,
  Plus,
  Send,
  X,
} from "lucide-react";

export default function ApplicantView() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [revisionTargetDoc, setRevisionTargetDoc] = useState(null);

  // Upload form state
  const [file, setFile] = useState(null);
  const [docType, setDocType] = useState("academic_certificate");
  const [candidateName, setCandidateName] = useState("");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const fetchDocuments = async () => {
    try {
      const res = await api.get("/api/documents");
      setDocuments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setUploadError("Please choose a valid PDF file.");
      return;
    }
    setUploadError("");
    setSubmitting(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", docType);
    formData.append("candidate_name", candidateName);
    formData.append("registration_number", registrationNumber);
    formData.append("issue_date", issueDate);

    try {
      if (revisionTargetDoc) {
        // Upload revision
        await api.post(`/api/documents/${revisionTargetDoc.id}/revisions`, formData);
      } else {
        // Initial upload
        await api.post("/api/documents/upload", formData);
      }
      setShowUploadModal(false);
      setRevisionTargetDoc(null);
      setFile(null);
      setCandidateName("");
      setRegistrationNumber("");
      setIssueDate("");
      fetchDocuments();
    } catch (err) {
      setUploadError(err.response?.data?.detail || "Upload failed. Verify that the file is a PDF.");
    } finally {
      setSubmitting(false);
    }
  };

  const openRevisionModal = (doc) => {
    setRevisionTargetDoc(doc);
    setCandidateName(doc.submitted_metadata?.candidate_name || "");
    setRegistrationNumber(doc.submitted_metadata?.registration_number || "");
    setIssueDate(doc.submitted_metadata?.issue_date || "");
    setUploadError("");
    setShowUploadModal(true);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "APPROVED":
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200"><CheckCircle2 className="w-3 h-3" /> Approved</span>;
      case "REJECTED":
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200"><XCircle className="w-3 h-3" /> Rejected</span>;
      case "CORRECTION_REQUESTED":
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200"><AlertTriangle className="w-3 h-3" /> Correction Needed</span>;
      case "UNDER_REVIEW":
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200"><Clock className="w-3 h-3" /> Under Review</span>;
      case "PROCESSING":
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"><RefreshCw className="w-3 h-3 animate-spin" /> Processing</span>;
      case "PROCESSING_FAILED":
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200"><AlertTriangle className="w-3 h-3" /> Processing Failed</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">Submitted</span>;
    }
  };

  const total = documents.length;
  const underReview = documents.filter((d) => d.status === "UNDER_REVIEW" || d.status === "PROCESSING").length;
  const approved = documents.filter((d) => d.status === "APPROVED").length;
  const corrections = documents.filter((d) => d.status === "CORRECTION_REQUESTED");

  return (
    <div>
      {/* Title & Action */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">Applicant Portal</h1>
          <p className="text-xs text-slate-500 mt-1">Submit authentic identity and certificate documents for verification</p>
        </div>
        <button
          onClick={() => {
            setRevisionTargetDoc(null);
            setShowUploadModal(true);
            setUploadError("");
          }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-medium shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          Submit Document
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500 mb-1">Total Submissions</div>
          <div className="text-2xl font-bold text-slate-900">{total}</div>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500 mb-1">In Processing / Review</div>
          <div className="text-2xl font-bold text-indigo-600">{underReview}</div>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500 mb-1">Approved Documents</div>
          <div className="text-2xl font-bold text-emerald-600">{approved}</div>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500 mb-1">Corrections Requested</div>
          <div className="text-2xl font-bold text-amber-600">{corrections.length}</div>
        </div>
      </div>

      {/* Correction Notice Banner */}
      {corrections.length > 0 && (
        <div className="mb-8 p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold">Action Required: Correction Requested</h3>
              <p className="text-xs text-amber-800 mt-1">
                A reviewer requested updates on {corrections.length} of your documents. Please review remarks and upload revised files.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {corrections.map((cd) => (
                  <button
                    key={cd.id}
                    onClick={() => openRevisionModal(cd)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium transition"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload Revision: {cd.filename || "Document"}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Documents Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">My Document History</h2>
          <button
            onClick={fetchDocuments}
            className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <div className="text-sm font-medium text-slate-700">No documents submitted yet</div>
            <p className="text-xs text-slate-400 mt-1">Submit your first PDF document to begin the automated verification process.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/50 text-slate-500 uppercase tracking-wider text-[10px] font-semibold border-b border-slate-100">
                <tr>
                  <th className="px-6 py-3">Document Name</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Revision</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">SHA-256 Fingerprint</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50/50 transition">
                    <td className="px-6 py-4 font-medium text-slate-900 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
                      <span className="truncate max-w-xs">{d.filename || "Document.pdf"}</span>
                    </td>
                    <td className="px-6 py-4 text-slate-600 capitalize">
                      {d.document_type?.replace("_", " ")}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-mono text-[10px]">
                        v{d.current_revision || 1}
                      </span>
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(d.status)}</td>
                    <td className="px-6 py-4 font-mono text-[10px] text-slate-400 truncate max-w-[140px]" title={d.sha256}>
                      {d.sha256 ? `${d.sha256.substring(0, 10)}...` : "—"}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <a
                        href={`/api/documents/${d.id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-[11px] font-medium transition"
                      >
                        <Download className="w-3 h-3" /> Download
                      </a>
                      {d.status === "CORRECTION_REQUESTED" && (
                        <button
                          onClick={() => openRevisionModal(d)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-medium transition"
                        >
                          <Upload className="w-3 h-3" /> Resubmit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Upload / Revision Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-base font-semibold text-slate-900">
                {revisionTargetDoc ? `Submit Revised Document (v${(revisionTargetDoc.current_revision || 1) + 1})` : "Upload Document"}
              </h3>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {uploadError && (
              <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">PDF Document File</label>
                <input
                  type="file"
                  accept="application/pdf"
                  required
                  onChange={(e) => setFile(e.target.files[0])}
                  className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                />
              </div>

              {!revisionTargetDoc && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">Document Classification</label>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  >
                    <option value="academic_certificate">Academic Certificate</option>
                    <option value="identity_card">Government ID / Passport</option>
                    <option value="employment_record">Employment Record</option>
                    <option value="income_proof">Proof of Income</option>
                  </select>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">Candidate Name</label>
                  <input
                    type="text"
                    value={candidateName}
                    onChange={(e) => setCandidateName(e.target.value)}
                    placeholder="e.g. Alice Smith"
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">Registration / Cert #</label>
                  <input
                    type="text"
                    value={registrationNumber}
                    onChange={(e) => setRegistrationNumber(e.target.value)}
                    placeholder="e.g. CERT-1024"
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Issue Date (YYYY-MM-DD)</label>
                <input
                  type="date"
                  value={issueDate}
                  onChange={(e) => setIssueDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  {submitting ? "Uploading..." : revisionTargetDoc ? "Submit Revision" : "Submit"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

