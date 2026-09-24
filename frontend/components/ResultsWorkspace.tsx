"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { artifactUrl, meshUrl } from "@/lib/api";
import type { CaseResult, ViewSettings } from "@/types/heartai";
import StructureControls from "./StructureControls";
import MeasurementsPanel from "./MeasurementsPanel";
const HeartViewer = dynamic(() => import("./HeartViewer"), { ssr: false, loading: () => <div className="viewer-message">Preparing 3D viewer…</div> });

export default function ResultsWorkspace({ result }: { result: CaseResult }) {
  const [tab, setTab] = useState<"3d" | "preview">("3d");
  const [previewFailed, setPreviewFailed] = useState(false);
  const [selected, setSelected] = useState(result.structures.find(s => s.name === "myocardium")?.name || result.structures[0]?.name || "");
  const [views, setViews] = useState<ViewSettings>(() => Object.fromEntries(result.structures.map(s => [s.name, { visible: true, opacity: s.name === "myocardium" ? 0.55 : 1 }])));
  const [focus, setFocus] = useState<{ name: string | null; sequence: number }>({ name: selected || null, sequence: 0 });
  const structure = result.structures.find(s => s.name === selected);
  function update(name: string, patch: Partial<ViewSettings[string]>) { setViews(v => ({ ...v, [name]: { ...v[name], ...patch } })); }
  return <>
    <div className="result-heading"><div><div className="eyebrow">CASE WORKSPACE / RECONSTRUCTION COMPLETE</div><h1>Cardiac anatomy <em>explorer</em></h1><p>Predicted structures from a cardiac CT volume</p></div><div className="case-tag"><span className="status-dot" /> CASE {result.case_id}</div></div>
    <div className="case-strip" aria-label="Case summary"><div><span>MODEL GRID</span><strong>3 mm</strong><small>Published low-resolution checkpoint</small></div><div><span>SOURCE CT</span><strong>{result.input.shape.join(" × ")}</strong><small>voxels · {result.input.orientation.join("")}</small></div><div><span>ANATOMY</span><strong>{result.structures.length} structures</strong><small>Present in this prediction</small></div><div><span>ANALYSIS TIME</span><strong>{result.timing.total_seconds.toFixed(1)} s</strong><small>{result.model.device.toUpperCase()} · {result.timing.inference_seconds.toFixed(1)} s inference</small></div></div>
    <div className="workspace">
      <section className="viewer-panel">
        <div className="viewer-toolbar"><div className="tabs" role="tablist" aria-label="Result view"><button role="tab" aria-selected={tab === "3d"} onClick={() => setTab("3d")}>01 &nbsp; 3D anatomy</button><button role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")}>02 &nbsp; CT overlay</button></div>
          <button className="text-button" onClick={() => setFocus(f => ({ name: null, sequence: f.sequence + 1 }))} disabled={tab !== "3d"}>Fit all ↺</button></div>
        <div className="viewer-area" role="tabpanel" aria-label={tab === "3d" ? "3D anatomy viewer" : "Segmentation preview"}>
          {tab === "3d" ? <><HeartViewer caseId={result.case_id} structures={result.structures} views={views} selected={selected} onSelect={setSelected} focus={focus} />
            <div className="viewer-label"><span className="eyebrow">PATIENT SPACE / PHYSICAL SCALE</span><span>Drag to rotate · Scroll to zoom</span></div><div className="viewer-corner">R &nbsp;·&nbsp; S &nbsp;·&nbsp; −A</div></> : previewFailed ? <div className="viewer-message" role="alert">Preview could not load. Check the backend connection and reopen this case.</div> :
            /* A local API image is displayed directly; no external image service is used. */
            // eslint-disable-next-line @next/next/no-img-element
            <img className="overlay-image" src={artifactUrl(result.case_id, "overlay")} alt="Three axial CT slices, predicted cardiac structures, and segmentation overlays" onError={() => setPreviewFailed(true)} />}
        </div>
        <div className="viewer-footer"><span>{tab === "3d" ? "MOUSE  ROTATE / ZOOM / PAN" : "THREE AXIAL LEVELS · ORIGINAL / LABELS / OVERLAY"}</span><span>{result.structures.length} predicted structures</span></div>
        <div className="export-bar"><span className="eyebrow">DOWNLOAD</span><a href={artifactUrl(result.case_id, "segmentation")}>Segmentation <span>NIfTI ↗</span></a><a href={meshUrl(result.case_id)}>Combined anatomy <span>GLB ↗</span></a><a href={artifactUrl(result.case_id, "measurements")}>Measurements <span>JSON ↗</span></a></div>
      </section>
      <aside className="results-sidebar"><StructureControls structures={result.structures} views={views} selected={selected} onSelect={setSelected} onChange={update}
        onFocus={name => { setSelected(name); update(name, { visible: true }); setTab("3d"); setFocus(f => ({ name, sequence: f.sequence + 1 })); }} />
        <MeasurementsPanel structure={structure} measurement={result.measurements[selected]} caseId={result.case_id} />
      </aside>
    </div>
    <div className="result-details"><section><div className="eyebrow">MODEL PROVENANCE</div><strong>{result.model.name}</strong><p>Version {result.model.version} · {result.model.device.toUpperCase()} inference. Segmentation comes from the unchanged published checkpoint.</p></section>
      <section><div className="eyebrow">SOURCE GEOMETRY</div><strong>{result.input.spacing_mm.map(v => v.toFixed(3)).join(" × ")} mm</strong><p>Original CT spacing · {result.input.orientation.join("")} orientation · physical scale retained in exports</p></section></div>
    {result.warnings.length > 0 && <details className="quality-notes" open><summary>Prediction notes <span>{result.warnings.length}</span></summary><ul>{result.warnings.map(w => <li key={w}>{w}</li>)}</ul></details>}
    {result.absent_structures.length > 0 && <p className="small-note">Not predicted in this scan: {result.absent_structures.join(", ")}</p>}
  </>;
}
