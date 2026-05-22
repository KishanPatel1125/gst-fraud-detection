// BulkUpload.jsx
// Add this as a new tab in your App.jsx

import { useState, useRef } from "react";

const API = "http://localhost:8000"; // Change if your API server is hosted elsewhere

const riskColor = l => ({
  CRITICAL:"#FF3B5C", HIGH:"#FF8C00",
  MEDIUM:"#FFD60A",   LOW:"#30D158"
}[l] || "#8E8E93");

const riskBg = l => ({
  CRITICAL:"rgba(255,59,92,0.12)", HIGH:"rgba(255,140,0,0.12)",
  MEDIUM:"rgba(255,214,10,0.12)",  LOW:"rgba(48,209,88,0.12)"
}[l] || "rgba(142,142,147,0.12)");

export default function BulkUpload({ token }) {
  const [file,         setFile]         = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [results,      setResults]      = useState(null);
  const [error,        setError]        = useState("");
  const [dragOver,     setDragOver]     = useState(false);
  const [downloading,  setDownloading]  = useState(false);
  const fileRef = useRef();

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  // ── Handle file selection ──
  const handleFile = (f) => {
    if (!f) return;
    if (!f.name.endsWith(".csv")) {
      setError("Only CSV files are accepted");
      return;
    }
    setFile(f);
    setError("");
    setResults(null);
  };

  // ── Drag and drop ──
  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  };

  // ── Upload and analyze ──
  const handleUpload = async () => {
    if (!file) { setError("Please select a CSV file"); return; }
    setLoading(true);
    setError("");
    setResults(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const res  = await fetch(`${API}/api/bulk/upload`, {
        method: "POST",
        headers,
        body: form,
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Upload failed");
        return;
      }
      setResults(data);
    } catch {
      setError("Cannot connect to API server");
    } finally {
      setLoading(false);
    }
  };

  // ── Download results as CSV ──
  const handleDownloadResults = async () => {
    if (!file) return;
    setDownloading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res  = await fetch(`${API}/api/bulk/download`, {
        method: "POST", headers, body: form,
      });
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `GST_Bulk_Analysis_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError("Download failed");
    } finally {
      setDownloading(false);
    }
  };

  // ── Download template ──
  const handleDownloadTemplate = () => {
    window.open(`${API}/api/bulk/template`, "_blank");
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 22, fontWeight: 800 }}>📤 Bulk GSTIN Analysis</h2>
        <p style={{ fontSize: 13, color: "#8E8E93", marginTop: 4 }}>
          Upload a CSV with up to 1,000 GSTINs and analyze all of them at once
        </p>
      </div>

      {/* Instructions */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(3,1fr)",
        gap: 12, marginBottom: 24,
      }}>
        {[
          { step: "1", icon: "📥", title: "Download Template",
            desc: "Get the CSV template with correct format" },
          { step: "2", icon: "✏️", title: "Fill GSTINs",
            desc: "Add your GSTINs and optional company data" },
          { step: "3", icon: "📊", title: "Get Results",
            desc: "Upload and get instant fraud scores for all" },
        ].map(({ step, icon, title, desc }) => (
          <div key={step} style={{
            background: "rgba(255,255,255,0.025)",
            border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: 16, padding: "16px 18px",
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "rgba(255,59,92,0.15)",
              color: "#FF3B5C", fontSize: 13, fontWeight: 700,
              display: "flex", alignItems: "center",
              justifyContent: "center", marginBottom: 10,
            }}>{step}</div>
            <div style={{ fontSize: 20, marginBottom: 6 }}>{icon}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#F5F5F7", marginBottom: 4 }}>{title}</div>
            <div style={{ fontSize: 12, color: "#8E8E93", lineHeight: 1.5 }}>{desc}</div>
          </div>
        ))}
      </div>

      {/* Template download */}
      <div style={{
        background: "rgba(255,255,255,0.025)",
        border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 16, padding: "14px 20px",
        marginBottom: 16, display: "flex",
        alignItems: "center", justifyContent: "space-between",
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#F5F5F7" }}>
            📄 CSV Template Format
          </div>
          <div style={{
            fontSize: 12, color: "#8E8E93", marginTop: 4,
            fontFamily: "'DM Mono',monospace",
          }}>
            gstin, company_name, annual_turnover, missing_returns, avg_itc_ratio
          </div>
        </div>
        <button onClick={handleDownloadTemplate} style={{
          padding: "8px 16px", borderRadius: 10,
          background: "rgba(255,255,255,0.06)",
          border: "1px solid rgba(255,255,255,0.12)",
          color: "#F5F5F7", fontSize: 12, cursor: "pointer",
          fontFamily: "inherit", fontWeight: 500, whiteSpace: "nowrap",
        }}>
          ⬇️ Download Template
        </button>
      </div>

      {/* Upload area */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? "#FF3B5C" : file ? "#30D158" : "rgba(255,255,255,0.15)"}`,
          borderRadius: 20, padding: "40px 24px",
          textAlign: "center", cursor: "pointer",
          background: dragOver
            ? "rgba(255,59,92,0.05)"
            : file
            ? "rgba(48,209,88,0.05)"
            : "rgba(255,255,255,0.02)",
          transition: "all 0.2s", marginBottom: 16,
        }}
      >
        <input
          ref={fileRef} type="file" accept=".csv"
          style={{ display: "none" }}
          onChange={e => handleFile(e.target.files[0])}
        />
        <div style={{ fontSize: 40, marginBottom: 12 }}>
          {file ? "✅" : "📁"}
        </div>
        {file ? (
          <>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#30D158" }}>
              {file.name}
            </div>
            <div style={{ fontSize: 12, color: "#8E8E93", marginTop: 6 }}>
              {(file.size / 1024).toFixed(1)} KB • Click to change file
            </div>
          </>
        ) : (
          <>
            <div style={{ fontSize: 15, fontWeight: 600, color: "#F5F5F7" }}>
              Drop your CSV file here
            </div>
            <div style={{ fontSize: 12, color: "#8E8E93", marginTop: 6 }}>
              or click to browse • Max 10MB • CSV format only
            </div>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: "rgba(255,59,92,0.1)",
          border: "1px solid rgba(255,59,92,0.3)",
          borderRadius: 12, padding: "10px 16px",
          fontSize: 13, color: "#FF3B5C", marginBottom: 16,
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Upload button */}
      <button
        onClick={handleUpload}
        disabled={!file || loading}
        style={{
          width: "100%", padding: 16, borderRadius: 14,
          background: file && !loading
            ? "linear-gradient(135deg,#FF3B5C,#FF6B00)"
            : "rgba(255,255,255,0.06)",
          border: "none", color: "white",
          fontSize: 15, fontWeight: 700, cursor: file ? "pointer" : "not-allowed",
          fontFamily: "inherit", marginBottom: 24,
          opacity: file ? 1 : 0.5,
          transition: "all 0.2s",
        }}
      >
        {loading ? (
          <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
            <span style={{
              width: 18, height: 18,
              border: "2px solid rgba(255,255,255,0.3)",
              borderTop: "2px solid white",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
              display: "inline-block",
            }} />
            Analyzing GSTINs...
          </span>
        ) : `🔍 Analyze ${file ? "CSV" : "GSTINs"}`}
      </button>

      {/* Results */}
      {results && (
        <div>
          {/* Summary cards */}
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(4,1fr)",
            gap: 12, marginBottom: 20,
          }}>
            {[
              { label: "Total Analyzed", value: results.total_analyzed, color: "#0A84FF" },
              { label: "🔴 Critical",     value: results.summary.critical, color: "#FF3B5C" },
              { label: "🟠 High Risk",    value: results.summary.high,     color: "#FF8C00" },
              { label: "✅ Low Risk",     value: results.summary.low,      color: "#30D158" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                background: "rgba(255,255,255,0.025)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: 16, padding: "16px 18px", textAlign: "center",
              }}>
                <div style={{
                  fontSize: 30, fontWeight: 800, color,
                  fontFamily: "'DM Mono',monospace",
                }}>{value}</div>
                <div style={{ fontSize: 12, color: "#8E8E93", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Warnings */}
          {results.warnings?.length > 0 && (
            <div style={{
              background: "rgba(255,214,10,0.08)",
              border: "1px solid rgba(255,214,10,0.2)",
              borderRadius: 12, padding: "10px 16px",
              marginBottom: 16, fontSize: 12, color: "#FFD60A",
            }}>
              {results.warnings.map((w, i) => <div key={i}>⚠️ {w}</div>)}
            </div>
          )}

          {/* Download results */}
          <div style={{
            display: "flex", justifyContent: "space-between",
            alignItems: "center", marginBottom: 14,
          }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>
              📊 Analysis Results ({results.total_analyzed} GSTINs)
            </div>
            <button onClick={handleDownloadResults} disabled={downloading} style={{
              padding: "8px 16px", borderRadius: 10,
              background: "linear-gradient(135deg,#0A84FF,#0055AA)",
              border: "none", color: "white", fontSize: 12,
              cursor: "pointer", fontFamily: "inherit", fontWeight: 600,
            }}>
              {downloading ? "⟳ Downloading..." : "⬇️ Download Full Report CSV"}
            </button>
          </div>

          {/* Results table */}
          <div style={{
            background: "rgba(255,255,255,0.025)",
            border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: 20, overflow: "hidden",
          }}>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 90px 80px 80px 80px 90px",
              padding: "12px 20px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              fontSize: 10, color: "#8E8E93",
              fontWeight: 700, letterSpacing: "0.07em",
            }}>
              <span>GSTIN</span>
              <span style={{ textAlign: "center" }}>SCORE</span>
              <span style={{ textAlign: "center" }}>XGB</span>
              <span style={{ textAlign: "center" }}>ANOMALY</span>
              <span style={{ textAlign: "center" }}>GRAPH</span>
              <span style={{ textAlign: "center" }}>RISK</span>
            </div>

            {results.results.slice(0, 50).map((r, i) => {
              const color = riskColor(r.risk_level);
              return (
                <div key={r.gstin} style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 90px 80px 80px 80px 90px",
                  padding: "12px 20px", alignItems: "center",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  background: i % 2 === 0
                    ? "transparent"
                    : "rgba(255,255,255,0.01)",
                }}>
                  <div>
                    <div style={{
                      fontSize: 12, fontFamily: "'DM Mono',monospace",
                      fontWeight: 600, color: "#F5F5F7",
                    }}>{r.gstin}</div>
                    {r.company_name && r.company_name !== "Unknown" && (
                      <div style={{ fontSize: 11, color: "#8E8E93", marginTop: 2 }}>
                        {r.company_name}
                      </div>
                    )}
                    <div style={{ fontSize: 10, color: "#8E8E93", marginTop: 1 }}>
                      {r.source === "database" ? "📦 From DB" : "🤖 ML Analysis"}
                    </div>
                  </div>
                  <div style={{
                    textAlign: "center", fontSize: 15,
                    fontWeight: 800, color,
                    fontFamily: "'DM Mono',monospace",
                  }}>{r.ensemble_score?.toFixed(1)}%</div>
                  <div style={{
                    textAlign: "center", fontSize: 12,
                    color: "#0A84FF", fontFamily: "'DM Mono',monospace",
                  }}>{r.xgb_score?.toFixed(0)}%</div>
                  <div style={{
                    textAlign: "center", fontSize: 12,
                    color: "#BF5AF2", fontFamily: "'DM Mono',monospace",
                  }}>{r.anomaly_score?.toFixed(0)}%</div>
                  <div style={{
                    textAlign: "center", fontSize: 12,
                    color: "#FF9F0A", fontFamily: "'DM Mono',monospace",
                  }}>{r.graph_risk_score?.toFixed(0)}%</div>
                  <div style={{ textAlign: "center" }}>
                    <span style={{
                      padding: "3px 10px", borderRadius: 20,
                      fontSize: 10, fontWeight: 700,
                      background: riskBg(r.risk_level), color,
                      border: `1px solid ${color}35`,
                    }}>{r.risk_level}</span>
                  </div>
                </div>
              );
            })}

            {results.results.length > 50 && (
              <div style={{
                padding: "12px 20px", textAlign: "center",
                fontSize: 12, color: "#8E8E93",
                borderTop: "1px solid rgba(255,255,255,0.06)",
              }}>
                Showing 50 of {results.results.length} results.
                Download the full CSV report to see all.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}