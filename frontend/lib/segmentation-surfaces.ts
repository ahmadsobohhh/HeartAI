import vtkSTLReader from "@kitware/vtk.js/IO/Geometry/STLReader.js";

export type SurfaceSpec = {
  name: string; color: string; stl: string;
  mesh: { faces: number; bounds_mm: number[][] };
};
export type SurfaceState = { name: string; color: string; visible: boolean; opacity: number };
export const displayName = (name: string) => name.replaceAll("_", " ").replace(/^./, c => c.toUpperCase());

export async function verifyArtifact(buffer: ArrayBuffer, expected: string | undefined) {
  if (!expected || !/^[a-f0-9]{64}$/i.test(expected)) throw new Error("Missing artifact checksum in case manifest.");
  const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", buffer)), b => b.toString(16).padStart(2, "0")).join("");
  if (digest !== expected.toLowerCase()) throw new Error("Segmentation surface checksum mismatch.");
  return digest;
}

export function parseSurface(buffer: ArrayBuffer, spec: SurfaceSpec) {
  // HeartAI's binary STL stores raw RAS millimetres. STL has no standard units;
  // never apply the GLB Y-up/metre transform or VTK's SPACE=... conversion here.
  if (buffer.byteLength < 84 || buffer.byteLength !== 84 + new DataView(buffer).getUint32(80, true) * 50) throw new Error(`${spec.name}: invalid binary STL.`);
  if (new TextDecoder().decode(buffer.slice(0, 80)).includes("SPACE=")) throw new Error(`${spec.name}: unexpected STL coordinate header.`);
  const reader = vtkSTLReader.newInstance();
  try {
    reader.parseAsArrayBuffer(buffer);
    const poly = reader.getOutputData();
    const points = poly.getPoints().getData();
    if (!points.length || points.some((v: number) => !Number.isFinite(v))) throw new Error(`${spec.name}: invalid surface points.`);
    if (poly.getNumberOfPolys() !== spec.mesh.faces) throw new Error(`${spec.name}: triangle count mismatch.`);
    const bounds = poly.getBounds();
    const expected = [0, 1, 2].flatMap(axis => [spec.mesh.bounds_mm[0][axis], spec.mesh.bounds_mm[1][axis]]);
    if (bounds.some((v: number, i: number) => !Number.isFinite(expected[i]) || Math.abs(v - expected[i]) > .001)) throw new Error(`${spec.name}: RAS bounds mismatch.`);
    return { reader, poly, bounds: Array.from(bounds) as number[] };
  } catch (error) { reader.getOutputData()?.delete(); reader.delete(); throw error; }
}
