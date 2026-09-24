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
    <div className="eyebrow">01 / INPUT VOLUME</div>
    <h2>Load a cardiac CT</h2>
    <p>Choose one 3D NIfTI volume with CT intensities and millimetre spatial metadata.</p>
    <input ref={input} type="file" accept=".nii,.nii.gz" aria-label="Cardiac CT file" className="file-input" onChange={e => choose(e.target.files?.[0])} />
    <button className={`drop-zone ${dragging ? "dragging" : ""}`} onClick={() => input.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files.length > 1) { setError("Choose one CT volume at a time."); return; } choose(e.dataTransfer.files[0]); }}>
      <span className="upload-symbol" aria-hidden>↥</span>
      <strong>{file ? file.name : "Drop CT volume here"}</strong>
      <span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MiB · Click to replace` : "or browse files"}</span>
      <small>ACCEPTED FORMAT <b>.nii / .nii.gz</b> <i /> MAX <b>{Math.round(maxBytes / 1024 / 1024)} MiB</b></small>
    </button>
    {error && <p className="error-message" role="alert">{error}</p>}
    {!connected && <p className="error-message">Analysis server is offline. <button className="text-button" onClick={onReconnect}>Check connection</button></p>}
    <button className="primary wide" disabled={!file || !connected} onClick={() => file && onAnalyze(file)}>Run analysis <span>↗</span></button>
    <div className="or-divider"><span>NO SCAN AT HAND?</span></div>
    <button className="secondary wide" disabled={!demoAvailable || !connected} onClick={onDemo}>Analyze public demo CT <span>→</span></button>
    <p className="small-note">3D Slicer CTACardio · Actual inference, segmentation, and reconstruction</p>
  </div>;
}
