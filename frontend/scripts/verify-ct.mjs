// Run from frontend: node scripts/verify-ct.mjs [path/to/manifest.json]
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { NIFTI1 } from 'nifti-reader-js';
import vtkImageData from '@kitware/vtk.js/Common/DataModel/ImageData.js';
import { decodeCT, geometry, presets } from '../lib/ct-volume.ts';

const affine = [[0, -2, 0, 100], [1, 0, 0, -20], [0, 0, 3, 7], [0, 0, 0, 1]];
assert.deepEqual(geometry(affine).spacing, [1, 2, 3]);
assert.throws(() => geometry([[1, .5, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]), /Sheared/);
let checks = 1;
for (const littleEndian of [true, false]) for (const slope of [0, 2]) for (const compressed of [true, false]) {
  const h = new NIFTI1();
  Object.assign(h, { littleEndian, dims: [3, 2, 2, 2, 1, 1, 1, 1], pixDims: [1, 1, 2, 3, 1, 1, 1, 1], datatypeCode: 4, numBitsPerVoxel: 16, vox_offset: 352, xyzt_units: 2, sform_code: 1, affine, scl_slope: slope, scl_inter: 10, magic: 'n+1\0' });
  const buffer = new ArrayBuffer(368);
  new Uint8Array(buffer).set(new Uint8Array(h.toArrayBuffer()));
  const view = new DataView(buffer);
  for (let i = 0; i < 8; i++) view.setInt16(352 + i * 2, i - 4, littleEndian);
  const bytes = compressed ? Uint8Array.from(gzipSync(buffer)).buffer : buffer;
  const expected = { affine, shape: [2, 2, 2] };
  const ct = await decodeCT(bytes, expected);
  assert.deepEqual(Array.from(ct.values), Array.from({ length: 8 }, (_, i) => slope ? (i - 4) * 2 + 10 : i - 4));
  await assert.rejects(decodeCT(bytes, { ...expected, shape: [3, 2, 2] }), /dimensions/);
  const image = vtkImageData.newInstance();
  image.setOrigin(ct.origin); image.setSpacing(ct.spacing); image.setDirection(ct.direction); image.setDimensions(ct.dimensions);
  assert.deepEqual(Array.from(image.indexToWorld([1, 1, 1])), [98, -19, 10]); image.delete();
  checks++;
}
console.log(`${checks} geometry / endian / scaling / compression combinations passed.`);
if (process.argv[2]) {
  const manifestPath = resolve(process.argv[2]);
  const manifest = JSON.parse(readFileSync(manifestPath));
  const file = readFileSync(resolve(dirname(manifestPath), manifest.input.path));
  const sha256 = createHash('sha256').update(file).digest('hex');
  assert.equal(sha256, manifest.input.sha256);
  const ct = await decodeCT(Uint8Array.from(file).buffer, manifest.input);
  const image = vtkImageData.newInstance();
  image.setOrigin(ct.origin); image.setSpacing(ct.spacing); image.setDirection(ct.direction); image.setDimensions(ct.dimensions);
  const corners = [];
  for (const x of [0, ct.dimensions[0] - 1]) for (const y of [0, ct.dimensions[1] - 1]) for (const z of [0, ct.dimensions[2] - 1]) {
    const ijk = [x, y, z], ras = Array.from(image.indexToWorld(ijk));
    const expected = ct.affine.slice(0, 3).map(row => row[0] * x + row[1] * y + row[2] * z + row[3]);
    ras.forEach((v, i) => assert.ok(Math.abs(v - expected[i]) < 1e-5));
    corners.push({ ijk, ras });
  }
  const report = { checks, manifestPath, source: resolve(dirname(manifestPath), manifest.input.path), sha256, dimensions: ct.dimensions, spacing: ct.spacing, affine: ct.affine, range: ct.range, corners, float32VoxelSHA256: createHash('sha256').update(new Uint8Array(ct.values.buffer)).digest('hex'), presets };
  writeFileSync('../results/milestone-f-volume.json', JSON.stringify(report, null, 2)); image.delete();
  console.log('Real CT decoded; all 8 physical corners match. Evidence: results/milestone-f-volume.json');
}
