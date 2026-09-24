"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import * as api from "@/lib/api";
import type { CaseResult, CaseStage } from "@/types/heartai";
import UploadCard from "@/components/UploadCard";
import ProcessingStatus from "@/components/ProcessingStatus";
import ResultsWorkspace from "@/components/ResultsWorkspace";

export default function Home() {
  const [server, setServer] = useState<{ demo_available: boolean; max_upload_bytes: number } | null>(null);
  const [healthAttempt, setHealthAttempt] = useState(0);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [stage, setStage] = useState<CaseStage | "uploading">("queued");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CaseResult | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [openId, setOpenId] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api.health(controller.signal).then(setServer).catch(e => { if (e.name !== "AbortError") setServer(null); });
    return () => controller.abort();
  }, [healthAttempt]);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("case");
    if (!id || !/^[a-f0-9]{8,32}$/.test(id)) return;
    const controller = new AbortController();
    api.getCaseStatus(id, controller.signal).then(value => { setCaseId(id); setStage(value.status); }).catch(e => { if (e.name !== "AbortError") setError(e.message); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!caseId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const status = await api.getCaseStatus(caseId!, controller.signal);
        if (controller.signal.aborted) return;
        setStage(status.status);
        if (status.status === "failed") { setError(status.error || "Analysis failed. Please check the scan and try again."); return; }
        if (status.status === "complete") { const data = await api.getCase(caseId!, controller.signal); if (!controller.signal.aborted) setResult(data); return; }
        timer = setTimeout(poll, 1500);
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Could not read analysis status."); }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [caseId, retry]);
  function remember(id: string) { window.history.replaceState(null, "", `?case=${encodeURIComponent(id)}`); setCaseId(id); }
  async function start(file?: File) {
    setError(""); setResult(null); setCaseId(null); setUploading(true); setStage("uploading");
    try { const response = file ? await api.createCase(file) : await api.createDemo(); remember(response.case_id); setStage(response.status); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not submit scan."); }
    finally { setUploading(false); }
  }
  function reset() { setCaseId(null); setResult(null); setError(""); setStage("queued"); window.history.replaceState(null, "", "/"); }
  function openCase() { if (!/^[a-f0-9]{8,32}$/.test(openId.trim())) { setError("Enter an 8–32 character hexadecimal case ID."); return; } setError(""); setResult(null); remember(openId.trim()); setRetry(v => v + 1); }
  return <div className="app-shell">
    <header className="app-header"><Link href="/" onClick={reset} className="brand" aria-label="HeartAI home"><span className="brand-mark"><svg viewBox="0 0 32 32" fill="none" aria-hidden><path d="M5 17h5l3-7 5 14 3-7h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>Heart<span className="brand-ai">AI</span></span><span className="version">V1</span></Link>
      <span className="header-context">CARDIAC CT WORKSPACE</span>
      <div className="header-right"><span className={`connection ${server ? "online" : ""}`}><span className="status-dot" />{server ? "Analysis engine online" : "Analysis engine offline"}</span>{(caseId || result) && <button className="secondary compact" onClick={reset}>New analysis <span aria-hidden>↗</span></button>}</div></header>
    <main>{result ? <ResultsWorkspace key={result.case_id} result={result} /> : <>
      <div className="intro"><div className="eyebrow"><span className="eyebrow-rule" /> PATIENT-SPECIFIC RECONSTRUCTION <span className="intro-index">01 / START</span></div><h1>From cardiac CT<br />to <em>3D anatomy.</em></h1><p>Load a CT volume. Inspect the model’s segmentation, reconstructed structures, and measurements in one place.</p></div>
      {error ? <section className="error-card" role="alert"><div className="eyebrow">ATTENTION NEEDED</div><h2>Let’s get back on track.</h2><p>{error}</p>{caseId && <p className="small-note">Case {caseId}. A connection error does not cancel a running analysis.</p>}<div className="button-row">{caseId && stage !== "failed" && <button className="primary" onClick={() => { setError(""); setRetry(v => v + 1); }}>Retry connection</button>}<button className="secondary" onClick={reset}>Back to upload</button></div></section> :
        uploading || caseId ? <ProcessingStatus status={stage} caseId={caseId} /> : <div className="start-layout"><UploadCard onAnalyze={file => void start(file)} onDemo={() => void start()} connected={!!server} demoAvailable={server?.demo_available ?? false} maxBytes={server?.max_upload_bytes ?? 256*1024*1024} onReconnect={() => setHealthAttempt(v => v + 1)} />
          <aside className="workflow-card"><div className="eyebrow">THE ANALYSIS PATH <span className="workflow-number">02 / PROCESS</span></div><h2>One scan.<br />Seven supported structures.</h2><ol><li><span>01</span><div><strong>Segment the CT</strong><p>Use the published MONAI whole-body CT model and its required preprocessing.</p></div></li><li><span>02</span><div><strong>Reconstruct anatomy</strong><p>Turn predicted labels into separate meshes in physical patient space.</p></div></li><li><span>03</span><div><strong>Inspect the result</strong><p>Compare CT overlays, explore 3D anatomy, and review measured volumes.</p></div></li></ol><div className="local-note"><span className="local-symbol">◈</span><div><strong>Local analysis</strong><p>The CT goes to the analysis server configured for this browser. The published 3 mm model is a research tool, not a diagnostic system.</p></div></div>
          <form className="reopen" onSubmit={e => { e.preventDefault(); openCase(); }}><label htmlFor="case-id">Reopen an existing case</label><div><input id="case-id" value={openId} onChange={e => setOpenId(e.target.value)} placeholder="Enter case ID" autoComplete="off" /><button type="submit" aria-label="Open case">→</button></div></form></aside></div>}
    </>}</main>
    <footer><span>HeartAI <b>·</b> Research prototype — not for clinical use.</span><span>Model-generated anatomy. No diagnostic claims.</span></footer>
  </div>;
}
