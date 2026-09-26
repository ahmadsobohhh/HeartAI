"""Opt-in live HTTP smoke test: uploads the public CT and runs real inference."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--scan', type=Path, default=Path('data/demo/CTA-cardio.nii.gz'))
    parser.add_argument('--report', type=Path, default=Path('results/milestone-e-http.json'))
    parser.add_argument('--case-id', help='Resume verification of an already submitted case; does not rerun inference')
    args = parser.parse_args()
    started = time.perf_counter()
    evidence = {'status': 'running', 'url': args.url, 'observed_states': []}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Avoid a keep-alive expiry race during long-running inference polling.
        with httpx.Client(base_url=args.url, timeout=120,
                          limits=httpx.Limits(max_keepalive_connections=0)) as client:
            assert client.get('/health').json()['status'] == 'ok'
            evidence['config'] = client.get('/api/config').json()
            assert evidence['config']['engine'] == 'totalseg'
            if args.case_id:
                case_id = args.case_id
                evidence['resumed_existing_case'] = True
            else:
                with args.scan.open('rb') as scan:
                    begin = time.perf_counter()
                    response = client.post('/api/cases', files={'file': ('public-demo.nii.gz', scan, 'application/gzip')})
                assert response.status_code == 202, response.text
                evidence['upload_and_accept_seconds'] = time.perf_counter()-begin
                case_id = response.json()['case_id']
            evidence['case_id'] = case_id
            print('Accepted real upload:', case_id, flush=True)
            args.report.write_text(json.dumps(evidence, indent=2))
            deadline = time.monotonic()+1800
            while time.monotonic() < deadline:
                response = client.get(f'/api/cases/{case_id}/status')
                response.raise_for_status()
                state = response.json()
                if not evidence['observed_states'] or evidence['observed_states'][-1] != state['status']:
                    evidence['observed_states'].append(state['status'])
                    args.report.write_text(json.dumps(evidence, indent=2))
                    print(state['status'], flush=True)
                assert client.get('/health').status_code == 200
                if state['status'] == 'failed':
                    raise RuntimeError(state.get('error'))
                if state['status'] == 'complete':
                    break
                time.sleep(5)
            else:
                raise TimeoutError('Backend did not finish within 30 minutes')
            manifest_response = client.get(f'/api/cases/{case_id}/manifest')
            manifest_response.raise_for_status()
            manifest = manifest_response.json()
            hashes = {path.replace('\\', '/'): value for path, value in manifest['artifact_sha256'].items()}
            assert manifest['segmentation']['engine'] == 'TotalSegmentator'
            endpoints = {'volume': manifest['input']['path'], 'measurements': 'measurements.json',
                         'mesh/cardiac': 'meshes/cardiac.glb'}
            endpoints.update({f'preview/{plane}': path for plane, path in manifest['artifacts']['previews'].items()})
            endpoints.update({f'segmentation/{name}': f'segmentations/{name}.nii.gz'
                              for name in manifest['segmentation']['structures']})
            for structure in manifest['structures']:
                for kind in ('glb', 'stl'):
                    endpoints[f'mesh/{structure["name"]}?format={kind}'] = structure[kind]
            evidence['downloads'] = {}
            for endpoint, path in endpoints.items():
                response = client.get(f'/api/cases/{case_id}/{endpoint}')
                response.raise_for_status()
                digest = hashlib.sha256(response.content).hexdigest()
                assert digest == hashes[path], endpoint
                evidence['downloads'][endpoint] = {'bytes': len(response.content), 'sha256': digest}
            evidence.update(status='complete', structures=len(manifest['structures']),
                            mask_files=len(manifest['segmentation']['structures']), pipeline_timing=manifest['timing'])
            print('Verified downloaded bytes against manifest for', len(endpoints), 'artifacts', flush=True)
    except Exception as exc:
        evidence.update(status='failed', error=str(exc))
        raise
    finally:
        evidence['http_test_seconds'] = time.perf_counter()-started
        args.report.write_text(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
