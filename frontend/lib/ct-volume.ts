import * as nifti from "nifti-reader-js";

export function geometry(affine: number[][]) {
  if (affine.length !== 4 || affine.some(row => row.length !== 4 || row.some(v => !Number.isFinite(v)))) throw new Error("Invalid CT affine.");
  const spacing = [0, 1, 2].map(c => Math.hypot(...affine.slice(0, 3).map(row => row[c])));
  if (spacing.some(v => v <= 0)) throw new Error("Invalid CT spacing.");
  const direction = [0, 1, 2].flatMap(c => [0, 1, 2].map(r => affine[r][c] / spacing[c]));
  for (let a = 0; a < 3; a++) for (let b = a + 1; b < 3; b++) {
    if (Math.abs([0, 1, 2].reduce((s, r) => s + direction[a * 3 + r] * direction[b * 3 + r], 0)) > 1e-5) throw new Error("Sheared CT grids require resampling before viewing.");
  }
  return { origin: affine.slice(0, 3).map(row => row[3]), spacing, direction };
}

export async function decodeCT(buffer: ArrayBuffer, expected: { affine: number[][]; shape: number[] }) {
  const raw = nifti.isCompressed(buffer) ? await nifti.decompressAsync(buffer) : buffer;
  const header = nifti.readHeader(raw);
  if (header.dims[0] !== 3 || (header.xyzt_units & 7) !== 2) throw new Error("Expected a 3D CT in millimetres.");
  // The manifest is produced by nibabel (sform preferred). Reject disagreements
  // rather than silently displaying a differently oriented scan.
  const affine = header.affine;
  if (affine.some((row, r) => row.some((v, c) => Math.abs(v - expected.affine[r][c]) > 1e-4))) throw new Error("CT affine does not match the verified case manifest.");
  const dimensions = header.dims.slice(1, 4);
  if (dimensions.some((v, i) => v !== expected.shape[i])) throw new Error("CT dimensions do not match the case manifest.");
  const data = new DataView(nifti.readImage(header, raw));
  const readers: Record<number, [number, (offset: number) => number]> = {
    2: [1, o => data.getUint8(o)], 4: [2, o => data.getInt16(o, header.littleEndian)],
    8: [4, o => data.getInt32(o, header.littleEndian)], 16: [4, o => data.getFloat32(o, header.littleEndian)],
    64: [8, o => data.getFloat64(o, header.littleEndian)], 256: [1, o => data.getInt8(o)],
    512: [2, o => data.getUint16(o, header.littleEndian)], 768: [4, o => data.getUint32(o, header.littleEndian)],
  };
  const reader = readers[header.datatypeCode];
  if (!reader) throw new Error("Unsupported CT scalar type.");
  const [bytes, read] = reader;
  const count = dimensions.reduce((a, b) => a * b, 1);
  if (data.byteLength !== count * bytes) throw new Error("Incomplete CT voxel data.");
  const slope = header.scl_slope || 1;
  const intercept = header.scl_slope ? header.scl_inter : 0;
  const values = new Float32Array(count);
  let min = Infinity, max = -Infinity;
  for (let i = 0; i < count; i++) {
    values[i] = read(i * bytes) * slope + intercept;
    if (!Number.isFinite(values[i])) throw new Error("CT contains non-finite intensities.");
    min = Math.min(min, values[i]); max = Math.max(max, values[i]);
  }
  return { ...geometry(affine), affine, dimensions, values, range: [min, max] };
}

export const presets = {
  contrast: { label: "Contrast CT", points: [[-1024, 0, 0, 0, 0], [100, .55, .19, .12, 0], [180, .8, .36, .21, .025], [350, 1, .73, .48, .16], [700, 1, .94, .84, .38], [3532, 1, 1, 1, .65]] },
  bone: { label: "Bone", points: [[-1024, 0, 0, 0, 0], [250, .5, .3, .2, 0], [500, .9, .77, .58, .12], [1000, 1, .95, .85, .5], [3532, 1, 1, 1, .8]] },
  tissue: { label: "Soft tissue", points: [[-1024, 0, 0, 0, 0], [-150, .5, .25, .15, 0], [40, .8, .4, .25, .018], [150, .95, .65, .4, .045], [400, 1, .9, .8, .12], [3532, 1, 1, 1, .4]] },
};
export type Preset = keyof typeof presets;
