import { meshUrl } from "@/lib/api";
import type { Measurement, Structure } from "@/types/heartai";
export default function MeasurementsPanel({ structure, measurement, caseId }: { structure?: Structure; measurement?: Measurement; caseId: string }) {
  if (!structure || !measurement) return <p>Select a structure to inspect its measurements.</p>;
  return <section className="measurement-panel"><div className="eyebrow">SELECTED STRUCTURE</div><h3>{structure.label}</h3>
    <div className="volume">{measurement.volume_ml.toFixed(2)} <span>mL</span></div><div className="small-note">Predicted segmentation volume</div>
    <dl><dt>Bounding dimensions <span>R × A × S</span></dt><dd>{measurement.bounding_dimensions_mm?.map(v => v.toFixed(1)).join(" × ") ?? "Unavailable"} {measurement.bounding_dimensions_mm && "mm"}</dd>
      <dt>Centroid <span>RAS</span></dt><dd>{measurement.centroid_mm?.map(v => v.toFixed(1)).join(", ") ?? "Unavailable"} {measurement.centroid_mm && "mm"}</dd></dl>
    {measurement.connected_components > 1 && <p className="inline-warning">{measurement.connected_components} disconnected regions. All regions contribute to these measurements.</p>}
    {structure.touches_scan_boundary && <p className="inline-warning">Reaches the scan boundary. The mesh is capped at the field of view.</p>}
    <div className="download-row"><a href={meshUrl(caseId, structure.name)}>Download GLB ↗</a><a href={meshUrl(caseId, structure.name, "stl")}>STL ↗</a></div>
  </section>;
}
