export type CaseStage = "queued" | "inspecting" | "segmenting" | "reconstructing" | "measuring" | "complete" | "failed";
export interface CaseStatus { case_id: string; status: CaseStage; error?: string | null; failed_stage?: string | null; history?: { stage: string; at: string }[] }
export interface Measurement {
  volume_ml: number; volume_mm3: number; voxel_count: number;
  bounding_dimensions_mm: [number, number, number] | null;
  centroid_mm: [number, number, number] | null;
  connected_components: number;
}
export interface Structure { name: string; label: string; label_id: number; color: string; touches_scan_boundary: boolean }
export interface ModelInfo { name: string; version: string; device: string; checkpoint_sha256: string }
export interface Artifacts { segmentation: string; overlay: string; combined_glb: string; measurements: string; meshes: Record<string, { glb: string; stl: string }> }
export interface CaseResult extends CaseStatus {
  status: "complete"; structures: Structure[]; absent_structures: string[];
  measurements: Record<string, Measurement>; model: ModelInfo; artifacts: Artifacts;
  timing: { inference_seconds: number; total_seconds: number }; warnings: string[];
  input: { shape: number[]; spacing_mm: number[]; orientation: string[] };
}
export interface StructureView { visible: boolean; opacity: number }
export type ViewSettings = Record<string, StructureView>;
