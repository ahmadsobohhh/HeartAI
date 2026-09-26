"use client";
import { useEffect, useRef, useState } from "react";
import { artifactHash, measured, type Measurement, type ViewerManifest } from "@/lib/viewer-controls";
import { displayName, verifyArtifact } from "@/lib/segmentation-surfaces";
import styles from "./VolumeViewer.module.css";

export default function CaseInspector({ manifest, selected, measurements, measurementError, base }: { manifest: ViewerManifest | null; selected: string | null; measurements: Record<string, Measurement> | null; measurementError: string; base: string }) {
  const [downloadStatus, setDownloadStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const spec = manifest?.structures.find(s => s.name === selected);
  const measurement = selected ? measurements?.[selected] : undefined;
  async function download(suffix: string, filename: string, path?: string) {
    if (!manifest) return;
    controller.current?.abort();
    const request = new AbortController(); controller.current = request;
    setBusy(true); setDownloadStatus("Verifying download…");
    try {
      const response = await fetch(`${base}/api/cases/${encodeURIComponent(manifest.case_id)}${suffix}`, { signal: request.signal });
      if (!response.ok) throw new Error(`Download failed (${response.status}).`);
      const bytes = await response.arrayBuffer();
      const hash = path ? await verifyArtifact(bytes, artifactHash(manifest, path)) : null;
      if (!path && JSON.parse(new TextDecoder().decode(bytes)).case_id !== manifest.case_id) throw new Error("Manifest case mismatch.");
      if (request.signal.aborted) return;
      const url = URL.createObjectURL(new Blob([bytes]));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDownloadStatus(`${filename} · ${bytes.byteLength.toLocaleString()} bytes · ${hash ? `SHA-256 verified ${hash.slice(0, 12)}…` : "case verified"}`);
    } catch (error) { if (!request.signal.aborted) setDownloadStatus(error instanceof Error ? error.message : "Download failed."); }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  return <aside className={styles.inspector} aria-label="Case information">
    <div className={styles.eyebrow}>SELECTED STRUCTURE</div><h2>{selected ? displayName(selected) : "Select anatomy"}</h2>
    <p className={styles.note}>Measurements describe the original prediction, including portions hidden by clipping.</p>
    {selected && <dl className={styles.metrics}>
      <div><dt>Mask volume</dt><dd>{measured(measurement?.volume_ml)}{Number.isFinite(measurement?.volume_ml) && <small> mL</small>}</dd></div>
      <div><dt>Surface area</dt><dd>{measured(measurement?.surface_area_cm2)}{Number.isFinite(measurement?.surface_area_cm2) && <small> cm²</small>}</dd></div>
      <div><dt>Bounding dimensions · R / A / S</dt><dd className={styles.dimensions}>{measurement?.bounding_dimensions_mm?.length === 3 && measurement.bounding_dimensions_mm.every(Number.isFinite) ? `${measurement.bounding_dimensions_mm.map(v => measured(v, 1)).join(" × ")} mm` : "Not measured"}</dd></div>
    </dl>}
    {measurementError && <p role="alert">{measurementError}</p>}
    <section className={styles.infoSection}><h3>Model & provenance</h3>{manifest ? <dl>
      <dt>Engine</dt><dd>{manifest.segmentation.engine} {manifest.segmentation.version}</dd>
      <dt>Task</dt><dd>{manifest.segmentation.task ?? "Not recorded"}</dd>
      <dt>Inference device</dt><dd>{manifest.segmentation.device ?? "Not recorded"}</dd>
      <dt>Fast mode</dt><dd>{manifest.segmentation.fast_mode === undefined ? "Not recorded" : manifest.segmentation.fast_mode ? "Yes" : "No"}</dd>
      <dt>Inference / total pipeline</dt><dd>{measured(manifest.timing?.inference_seconds, 1)} s / {measured(manifest.timing?.total_seconds, 1)} s</dd>
    </dl> : <p>Open a completed case.</p>}</section>
    <section className={styles.infoSection}><h3>Download original outputs</h3><p className={styles.note}>Clipping changes the view only. Exports retain the full anatomy; source CT is not included.</p>
      <div className={styles.downloads}>
        {spec?.glb && <button disabled={busy} onClick={() => void download(`/mesh/${encodeURIComponent(spec.name)}?format=glb`, `${spec.name}.glb`, spec.glb)}>Selected GLB</button>}
        {spec?.stl && <button disabled={busy} onClick={() => void download(`/mesh/${encodeURIComponent(spec.name)}?format=stl`, `${spec.name}.stl`, spec.stl)}>Selected STL</button>}
        {spec?.mask && <button disabled={busy} onClick={() => void download(`/segmentation/${encodeURIComponent(spec.name)}`, `${spec.name}.nii.gz`, spec.mask)}>Selected mask</button>}
        <button disabled={!manifest || busy} onClick={() => void download("/measurements", "measurements.json", manifest?.artifacts.measurements)}>Measurements JSON</button>
        <button disabled={!manifest || busy} onClick={() => void download("/manifest", "manifest.json")}>Case manifest</button>
      </div><p className={styles.downloadStatus} role="status">{downloadStatus}</p>
    </section><p className={styles.note}>Research prototype · Not for clinical use.<br />Pretrained TotalSegmentator. No model training or fine-tuning by HeartAI.</p>
  </aside>;
}
