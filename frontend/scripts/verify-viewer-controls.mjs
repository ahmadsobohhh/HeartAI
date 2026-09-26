import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import vtkPlane from '@kitware/vtk.js/Common/DataModel/Plane.js';
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper.js';
import vtkVolumeMapper from '@kitware/vtk.js/Rendering/Core/VolumeMapper.js';
import { clippingGeometry, cardiacAvailability, measured } from '../lib/viewer-controls.ts';

const ct = JSON.parse(readFileSync('../results/milestone-f-volume.json'));
const bounds = [0, 1, 2].flatMap(axis => [Math.min(...ct.corners.map(c => c.ras[axis])), Math.max(...ct.corners.map(c => c.ras[axis]))]);
const checks = [];
for (const [axis, index] of [['sagittal', 0], ['coronal', 1], ['axial', 2]]) for (const inverted of [false, true]) {
  const geometry = clippingGeometry({ axis, inverted, enabled: true, position: 0 }, bounds);
  const plane = vtkPlane.newInstance(); plane.setNormal(...geometry.normal); plane.setOrigin(...geometry.origin);
  const surface = vtkMapper.newInstance(), volume = vtkVolumeMapper.newInstance();
  surface.addClippingPlane(plane); volume.addClippingPlane(plane);
  const retained = [0, 0, 0], discarded = [0, 0, 0]; retained[index] = inverted ? -10 : 10; discarded[index] = -retained[index];
  assert.ok(plane.evaluateFunction(retained) > 0); assert.ok(plane.evaluateFunction(discarded) < 0);
  assert.equal(surface.getClippingPlanes()[0], volume.getClippingPlanes()[0]);
  surface.removeAllClippingPlanes(); volume.removeAllClippingPlanes();
  assert.equal(surface.getNumberOfClippingPlanes(), 0); assert.equal(volume.getNumberOfClippingPlanes(), 0);
  checks.push({ axis, inverted, sharedWorldPlane: true, retainedSideCorrect: true, reset: true });
  plane.delete(); surface.delete(); volume.delete();
}
assert.equal(clippingGeometry({axis:'axial',inverted:false,enabled:true,position:1e6},bounds).position,bounds[5]);
assert.throws(()=>clippingGeometry({axis:'axial',inverted:false,enabled:true,position:NaN},bounds));
assert.deepEqual(cardiacAvailability(['heart','aorta','liver']).available,['heart','aorta']);
assert.ok(cardiacAvailability(['heart']).missing.includes('pulmonary_artery'));
assert.deepEqual(cardiacAvailability([]).available,[]);
assert.equal(measured(undefined),'Not measured'); assert.equal(measured(NaN),'Not measured'); assert.equal(measured(0),'0.00');
const measurements=JSON.parse(readFileSync('../results/cases/PUBLIC-001-D-final/measurements.json'));
assert.equal(measured(measurements.heart.volume_ml),'495.03');
writeFileSync('../results/milestone-h-controls.json',JSON.stringify({checks,bounds,cardiacSubsetAndMissingLabels:true,measurementFormatting:true},null,2));
console.log('All 6 world-plane/inversion combinations, reset, bounds, cardiac subset, and measurement formatting passed.');
