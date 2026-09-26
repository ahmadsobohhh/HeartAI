// Execute from frontend. This verifies the exact loader used by the browser.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { parseSurface, verifyArtifact } from '../lib/segmentation-surfaces.ts';

const manifestPath = resolve(process.argv[2] ?? '../results/cases/PUBLIC-001-D-final/manifest.json');
const manifest = JSON.parse(readFileSync(manifestPath));
const records = [];
for (const spec of manifest.structures) {
  const bytes = Uint8Array.from(readFileSync(resolve(dirname(manifestPath), spec.stl))).buffer;
  const expected = Object.entries(manifest.artifact_sha256).find(([path]) => path.replaceAll('\\', '/') === spec.stl.replaceAll('\\', '/'))[1];
  const sha256 = await verifyArtifact(bytes, expected);
  const parsed = parseSurface(bytes, spec);
  const points = parsed.poly.getPoints().getData(), raw = new DataView(bytes);
  // Independently check every triangle vertex, not just the bounding box.
  for (let face = 0; face < spec.mesh.faces; face++) for (let coordinate = 0; coordinate < 9; coordinate++) {
    assert.equal(points[face * 9 + coordinate], raw.getFloat32(84 + face * 50 + 12 + coordinate * 4, true));
  }
  const corrupt = bytes.slice(0); new Uint8Array(corrupt)[100] ^= 1;
  await assert.rejects(verifyArtifact(corrupt, expected), /checksum mismatch/);
  await assert.rejects(verifyArtifact(bytes, undefined), /Missing/);
  assert.throws(() => parseSurface(bytes.slice(0, -1), spec), /invalid binary/);
  assert.throws(() => parseSurface(bytes, { ...spec, mesh: { ...spec.mesh, faces: 1 } }), /triangle count/);
  const shifted = structuredClone(spec); shifted.mesh.bounds_mm[0][0] += 10;
  assert.throws(() => parseSurface(bytes, shifted), /bounds mismatch/);
  records.push({ name: spec.name, sha256, triangles: spec.mesh.faces, boundsRAS: parsed.bounds, everyVertexMatchesSTL: true, corruptionAndGeometryRejections: true });
  parsed.poly.delete(); parsed.reader.delete();
}
writeFileSync('../results/milestone-g-surfaces.json', JSON.stringify({ manifestPath, checks: records }, null, 2));
console.log(`${records.length} real surfaces: checksums, all triangle vertices, bounds, counts and rejection checks passed.`);
