export type ClipAxis = "axial" | "coronal" | "sagittal";
export type ClipState = { enabled: boolean; axis: ClipAxis; position: number; inverted: boolean };
export const clipAxisIndex = { sagittal: 0, coronal: 1, axial: 2 };
export const defaultClip: ClipState = { enabled: false, axis: "coronal", position: 0, inverted: true };
export function clippingGeometry(state: ClipState, bounds: number[]) {
  const axis = clipAxisIndex[state.axis];
  if (bounds.length !== 6 || bounds.some(v => !Number.isFinite(v)) || !Number.isFinite(state.position)) throw new Error("Invalid clipping geometry.");
  const position = Math.max(bounds[axis * 2], Math.min(bounds[axis * 2 + 1], state.position));
  const normal: [number, number, number] = [0, 0, 0];
  const origin: [number, number, number] = [0, 0, 0];
  normal[axis] = state.inverted ? -1 : 1; origin[axis] = position;
  // VTK retains normal · (RAS - origin) >= 0, in world millimetres.
  return { normal, origin, position };
}
export const cardiacStructures = ["heart", "aorta", "pulmonary_vein", "atrial_appendage_left", "superior_vena_cava", "inferior_vena_cava", "pulmonary_artery"];
export function cardiacAvailability(names: string[]) {
  return { available: names.filter(name => cardiacStructures.includes(name)), missing: cardiacStructures.filter(name => !names.includes(name)) };
}
export type Measurement = { volume_ml?: number; surface_area_cm2?: number; bounding_dimensions_mm?: number[]; centroid_mm?: number[] };
export type ViewerManifest = {
  case_id: string; status: string;
  input: { affine: number[][]; shape: number[]; sha256: string };
  structures: (import("./segmentation-surfaces").SurfaceSpec & { mask?: string; glb?: string })[];
  artifact_sha256: Record<string, string>; artifacts: { measurements: string };
  coordinates: { stl: string };
  segmentation: { engine: string; version?: string; task?: string; device?: string; fast_mode?: boolean };
  timing?: { inference_seconds?: number; total_seconds?: number };
};
export function artifactHash(manifest: ViewerManifest, path: string) {
  return Object.entries(manifest.artifact_sha256).find(([key]) => key.replaceAll("\\", "/") === path.replaceAll("\\", "/"))?.[1];
}
export function measured(value: number | undefined, digits = 2) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "Not measured";
}
