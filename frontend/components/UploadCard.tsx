"use client";
import { useRef, useState } from "react";

interface Props { onAnalyze: (file: File) => void; onDemo: () => void; demoAvailable: boolean; connected: boolean; maxBytes: number; onReconnect: () => void }
export default function UploadCard({ onAnalyze, onDemo, demoAvailable, connected, maxBytes, onReconnect }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  function choose(candidate?: File) {
    if (!candidate) return;
    if (!/\.nii(\.gz)?$/i.test(candidate.name)) { setFile(null); setError("Choose a NIfTI volume (.nii or .nii.gz)."); return; }
    if (candidate.size > maxBytes || candidate.size === 0) { setFile(null); setError(`Choose a nonempty file smaller than ${Math.round(maxBytes / 1024 / 1024)} MiB.`); return; }
    setError(""); setFile(candidate);
  }
  return <div className="upload-card">
    <div className="eyebrow">START A NEW ANALYSIS</div>
    <h2>Your scan. A new perspective.</h2>
    <p>Upload a cardiac CT to reconstruct and explore its predicted anatomy.</p>
    <input ref={input} type="file" accept=".nii,.nii.gz" aria-label="Cardiac CT file" className="file-input" onChange={e => choose(e.target.files?.[0])} />
    <button className={`drop-zone ${dragging ? "dragging" : ""}`} onClick={() => input.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files.length > 1) { setError("Choose one CT volume at a time."); return; } choose(e.dataTransfer.files[0]); }}>
      <span className="upload-symbol" aria-hidden>↑</span>
      <strong>{file ? file.name : "Drop your CT scan here"}</strong>
      <span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MiB · Click to replace` : "or click to browse your files"}</span>
      <small>.nii / .nii.gz · up to {Math.round(maxBytes / 1024 / 1024)} MiB</small>
    </button>
    {error && <p className="error-message" role="alert">{error}</p>}
    {!connected && <p className="error-message">Analysis server is offline. <button className="text-button" onClick={onReconnect}>Check connection</button></p>}
    <button className="primary wide" disabled={!file || !connected} onClick={() => file && onAnalyze(file)}>Analyze scan <span>→</span></button>
    <div className="or-divider"><span>or explore a public example</span></div>
    <button className="secondary wide" disabled={!demoAvailable || !connected} onClick={onDemo}>Try demo scan <span>↗</span></button>
    <p className="small-note">3D Slicer CTACardio · Runs real pretrained inference</p>
  </div>;
}
