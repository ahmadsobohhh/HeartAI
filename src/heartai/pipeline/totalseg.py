"""CLI orchestration around the executed A-C stages; no MONAI inference imports."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from uuid import uuid4

import nibabel as nib
import numpy as np

from heartai.preprocessing.loader import load_scan, scan_info
from heartai.reconstruction.totalseg_case import file_hash, reconstruct_package

ROOT = Path(__file__).resolve().parents[3]


def write_json(path, value):
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def run_script(python, script, arguments, log, *, timeout=14400):
    command = [str(python), '-u', str(ROOT / 'scripts' / script), *map(str, arguments)]
    with log.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'command': command}) + '\n')
        stream.flush()
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout, cwd=ROOT)


def create_overlays(package, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    ct = nib.as_closest_canonical(nib.load(package['ct_path']))
    # Canonical permutation preserves voxels. Oblique affines remain oblique;
    # titles explicitly describe voxel planes rather than resampled world planes.
    data = np.asarray(ct.dataobj)
    labels = np.zeros(ct.shape, dtype=np.uint8)
    for i, spec in enumerate(package['structures'], 1):
        mask = nib.as_closest_canonical(nib.load(spec['path']))
        labels[np.asarray(mask.dataobj) != 0] = i
    center = np.linalg.solve(ct.affine, np.r_[package['structures'][0]['review_center_ras_mm'], 1])[:3]
    spacing = nib.affines.voxel_sizes(ct.affine)
    colors = [s['color'] for s in package['structures']]
    for name, axis, horizontal, vertical in [('axial', 2, 0, 1), ('coronal', 1, 0, 2), ('sagittal', 0, 1, 2)]:
        index = int(np.clip(np.rint(center[axis]), 0, ct.shape[axis]-1))
        image = np.take(data, index, axis=axis).T
        overlay = np.take(labels, index, axis=axis).T
        extent = [0, image.shape[1]*spacing[horizontal], 0, image.shape[0]*spacing[vertical]]
        fig, ax = plt.subplots(figsize=(8, 7))
        ax.imshow(image, origin='lower', cmap='gray', vmin=-160, vmax=240, extent=extent)
        ax.imshow(np.ma.masked_equal(overlay, 0), origin='lower', interpolation='nearest',
                  cmap=ListedColormap(colors), vmin=.5, vmax=len(colors)+.5, alpha=.45, extent=extent)
        ax.set_title(f'TotalSegmentator | {name} canonical voxel plane {index}\nResearch prototype; not for clinical use')
        ax.set_xlabel(['R', 'A', 'S'][horizontal] + ' direction (mm from image edge)')
        ax.set_ylabel(['R', 'A', 'S'][vertical] + ' direction (mm from image edge)')
        fig.legend(handles=[Patch(color=s['color'], label=s['name'].replace('_', ' '))
                            for s in package['structures']], loc='lower center', ncol=2)
        fig.tight_layout(rect=(0, .13, 1, 1))
        fig.savefig(output / f'{name}_overlay.png', dpi=120)
        plt.close(fig)


def validate_artifacts(case, artifacts):
    """Reject missing, empty, or escaping artifact paths before completing."""
    hashes = {}
    for relative in artifacts:
        path = (case / relative).resolve()
        if not path.is_relative_to(case.resolve()) or not path.is_file() or not path.stat().st_size:
            raise ValueError(f'Invalid case artifact: {relative}')
        hashes[relative] = file_hash(path)
    return hashes


def analyze_case(scan_path, case_id=None, *, cases_dir=None, device='cpu', totalseg_python=None):
    case_id = case_id or ('case-' + uuid4().hex[:12])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', case_id) or case_id.upper().split('.')[0] in {
        'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        raise ValueError('case_id must be a safe 1-64 character alphanumeric/dash/underscore name')
    case = Path(cases_dir or ROOT / 'results/cases').resolve() / case_id
    case.mkdir(parents=True, exist_ok=False)
    python = Path(totalseg_python or os.environ.get('HEARTAI_TOTALSEG_PYTHON') or
                  ROOT / '.venv-totalseg' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')).resolve()
    started = time.perf_counter()
    manifest = {'schema_version': 2, 'case_id': case_id, 'status': 'validating',
                'history': [], 'timing': {}, 'structures': [], 'artifacts': {},
                'review': {'slicer': 'not_run', 'clinical_validation': False}}
    log = case / 'logs.txt'

    @contextmanager
    def stage(name):
        manifest['status'] = name
        entry = {'stage': name, 'started_utc': datetime.now(timezone.utc).isoformat(), 'seconds': None}
        manifest['history'].append(entry)
        write_json(case / 'manifest.json', manifest)
        begin = time.perf_counter()
        print(f'[{case_id}] {name}', flush=True)
        with log.open('a', encoding='utf-8') as stream:
            stream.write(f'START {name} {entry["started_utc"]}\n')
        try:
            yield
        finally:
            entry['seconds'] = time.perf_counter()-begin
            entry['finished_utc'] = datetime.now(timezone.utc).isoformat()
            manifest['timing'][name + '_seconds'] = entry['seconds']
            with log.open('a', encoding='utf-8') as stream:
                stream.write(f'END {name} {entry["seconds"]:.3f}s\n')
            write_json(case / 'manifest.json', manifest)

    try:
        with stage('validating'):
            source = Path(scan_path).resolve(strict=True)
            scan = load_scan(source)
            if scan.header.get_xyzt_units()[0] != 'mm':
                raise ValueError('TotalSegmentator pipeline requires NIfTI spatial units in mm')
            if device not in ('cpu', 'gpu'):
                raise ValueError('device must be cpu or gpu')
            if not python.is_file():
                raise FileNotFoundError(f'TotalSegmentator Python not found: {python}; set HEARTAI_TOTALSEG_PYTHON')
            (case / 'input').mkdir()
            saved = case / 'input' / ('scan.nii.gz' if source.name.lower().endswith('.gz') else 'scan.nii')
            shutil.copyfile(source, saved)
            if file_hash(source) != file_hash(saved):
                raise ValueError('Input copy checksum mismatch')
            manifest['input'] = {**scan_info(scan), 'path': saved.relative_to(case).as_posix(), 'sha256': file_hash(saved)}
            del scan
        with stage('segmenting'):
            temporary = case / 'inference'
            run_script(python, 'run_totalseg.py', [saved, '--output-dir', temporary, '--device', device], log,
                       timeout=14520)
            for artifact in temporary.iterdir():
                destination = case / ('inference.log' if artifact.name == 'logs.txt' else artifact.name)
                artifact.rename(destination)
            temporary.rmdir()  # Empty, pipeline-owned directory only.
            run = json.loads((case / 'run.json').read_text())
            manifest['segmentation'] = {k: run[k] for k in ('engine', 'version', 'task', 'device', 'fast_mode', 'roi_subset')}
            manifest['timing']['inference_seconds'] = run['runtime_seconds']
        with stage('validating_masks'):
            run_script(python, 'inspect_totalseg.py', [case], log)
            validation = json.loads((case / 'validation.json').read_text())
            if validation['status'] != 'passed':
                raise ValueError('Mask validation did not pass')
            run_script(python, 'prepare_totalseg_review.py', [case, case / 'cardiac'], log)
            package = json.loads((case / 'cardiac/cardiac_subset.json').read_text())
            manifest['segmentation'].update(structures=[s['name'] for s in validation['structures']],
                                            nonempty_count=validation['nonempty_structures'])
            manifest['unavailable_focus'] = package['unavailable_focus']
            manifest['absent_task_labels'] = package['absent_task_labels']
        with stage('reconstructing_and_measuring'):
            reconstruction = reconstruct_package(package, case / 'reconstruction')
            shutil.copytree(case / 'reconstruction/meshes', case / 'meshes')
            shutil.copyfile(case / 'reconstruction/measurements.json', case / 'measurements.json')
            manifest['coordinates'] = reconstruction['coordinates']
            manifest['warnings'] = reconstruction['warnings']
            manifest['structures'] = [{**{k: s[k] for k in ('name', 'label_id', 'color', 'mesh')},
                                       'mask': f'segmentations/{s["name"]}.nii.gz',
                                       'glb': f'meshes/{s["name"]}.glb', 'stl': f'meshes/{s["name"]}.stl'}
                                      for s in reconstruction['structures']]
        with stage('preparing_previews'):
            create_overlays(package, case / 'previews')
        with stage('validating_artifacts'):
            paths = [manifest['input']['path'], 'measurements.json', 'meshes/cardiac.glb',
                     'run.json', 'validation.json', 'installed_label_map.json', 'upstream_report.json',
                     'cardiac/cardiac_subset.json', 'reconstruction/reconstruction.json', 'inference.log']
            paths += [s['file'] for s in validation['structures']]
            paths += [s[k] for s in manifest['structures'] for k in ('glb', 'stl')]
            paths += [f'previews/{p}_overlay.png' for p in ('axial', 'coronal', 'sagittal', 'cardiac')]
            manifest['artifact_sha256'] = validate_artifacts(case, paths)
            if file_hash(saved) != manifest['input']['sha256']:
                raise ValueError('Source CT changed during analysis')
            manifest['artifacts'] = {'input': manifest['input']['path'], 'measurements': 'measurements.json',
                                     'combined_glb': 'meshes/cardiac.glb', 'logs': 'logs.txt',
                                     'previews': {p: f'previews/{p}_overlay.png' for p in ('axial', 'coronal', 'sagittal')}}
        manifest['status'] = 'complete'
        print(f'[{case_id}] complete: {len(manifest["segmentation"]["structures"])} masks; '
              f'{len(manifest["structures"])} reconstructed structures\nResults: {case}', flush=True)
    except Exception as exc:
        manifest.update(status='failed', failed_stage=manifest['status'], error=str(exc))
        raise
    finally:
        manifest['timing']['total_seconds'] = time.perf_counter()-started
        write_json(case / 'manifest.json', manifest)
    return manifest
