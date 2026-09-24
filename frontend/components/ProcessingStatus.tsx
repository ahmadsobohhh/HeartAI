import type { CaseStage } from "@/types/heartai";
const stages = ["uploading", "queued", "inspecting", "segmenting", "reconstructing", "measuring", "complete"] as const;
const names = ["Sending scan to the local server", "Waiting for analysis", "Checking the CT volume", "Preprocessing & AI segmentation", "Reconstructing 3D anatomy", "Calculating measurements", "Analysis complete"];
export default function ProcessingStatus({ status, caseId }: { status: CaseStage | "uploading"; caseId: string | null }) {
  const current = stages.indexOf(status as typeof stages[number]);
  return <section className="processing" aria-live="polite">
    <div className="eyebrow">PROCESSING / LIVE STATUS</div><h2>Building the anatomy</h2>
    <p>These stages come from the local analysis engine. The case will open automatically when processing finishes.</p>
    <ol className="stage-list">{names.map((name, index) => <li key={name} className={index < current ? "done" : index === current ? "active" : ""}>
      <span className="stage-mark">{index < current ? "✓" : index === current ? "●" : String(index + 1).padStart(2, "0")}</span>{name}
      {index === current && <span className="stage-label">In progress</span>}
    </li>)}</ol>
    {caseId && <p className="small-note">Case {caseId} · Progress is reported by the analysis engine</p>}
  </section>;
}
