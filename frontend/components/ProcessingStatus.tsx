import type { CaseStage } from "@/types/heartai";
const stages = ["uploading", "queued", "inspecting", "segmenting", "reconstructing", "measuring", "complete"] as const;
const names = ["Sending scan to the local server", "Waiting for analysis", "Checking the CT volume", "Preprocessing & AI segmentation", "Reconstructing 3D anatomy", "Calculating measurements", "Analysis complete"];
export default function ProcessingStatus({ status, caseId }: { status: CaseStage | "uploading"; caseId: string | null }) {
  const current = stages.indexOf(status as typeof stages[number]);
  return <section className="processing" aria-live="polite">
    <div className="eyebrow">ANALYSIS IN PROGRESS</div><h2>From scan to structure.</h2>
    <p>The local engine is processing your volume. You can leave this tab open.</p>
    <ol className="stage-list">{names.map((name, index) => <li key={name} className={index < current ? "done" : index === current ? "active" : ""}>
      <span className="stage-mark">{index < current ? "✓" : index === current ? "●" : String(index + 1).padStart(2, "0")}</span>{name}
      {index === current && <span className="stage-label">In progress</span>}
    </li>)}</ol>
    {caseId && <p className="small-note">Case {caseId} · Progress is reported by the analysis engine</p>}
  </section>;
}
