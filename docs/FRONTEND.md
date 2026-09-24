# Frontend checkpoint

The Next.js application connects to the existing FastAPI server. It does not run inference in the browser or contain substitute anatomy. All displayed structures, measurements, timings, warnings, meshes, and overlays come from the completed case manifest and artifact endpoints.

## Run locally

Complete the root README Python setup and asset download first. From the repository root in terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In terminal 2 (Node.js 22 or newer):

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:3000. Keep both terminals running. The backend permits frontend origins on localhost/127.0.0.1 port 3000. Use a single backend worker.

Production checks and launch, from `frontend/`:

```powershell
npm run typecheck
npm run lint
npm run build
npm start
```

The default API address is `http://127.0.0.1:8000`. If needed, copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_URL`, then restart development or rebuild production. This is a browser-visible address, not a private server-side proxy. An alternative origin also requires matching backend CORS configuration.

## Workflow

1. Upload a `.nii` or `.nii.gz` CT (up to 256 MiB), or choose **Try demo scan** to analyze the downloaded public Slicer CTACardio scan.
2. Watch actual backend stages. There are no estimated percentages. A connection failure offers retry; it does not cancel the server's analysis.
3. Explore the combined GLB's separately named structures. Drag to rotate, scroll to zoom, and right-drag to pan. Toggle visibility, select anatomy, adjust its opacity, focus it, or reset the camera.
4. Review the selected structure's voxel-based volume in mL, full bounding dimensions in mm, and RAS centroid in mm. Boundary clipping and disconnected-component warnings remain visible.
5. Switch to the segmentation preview to inspect three original CT slices, labels, and overlays. Download segmentation NIfTI, combined GLB, individual GLB/STL, or measurements JSON.

Cases can be reopened using the home form or `http://127.0.0.1:3000/?case=<case_id>`. Files persist on the backend filesystem. Viewer visibility, opacity, and camera settings are session state and reset when the page is reloaded.

## Verification

TypeScript compilation, ESLint, and the production build passed. The production frontend was exercised against the real local backend in the browser on September 19, 2026.

The **Try demo scan** workflow created case `e5414db0dd2b`. The actual pipeline completed in **33.12 seconds** on CPU, with **11.56 seconds** of neural inference. All seven supported structures loaded as real 3D meshes. Browser checks covered structure selection and measurements, aorta visibility, myocardium focus, opacity changed to 20%, camera manipulation/reset, the CT overlay tab, and reopening the completed case after reloading its URL. For example, the myocardium displayed 112.57 mL from the case's calculated measurements.

The browser file chooser selected the public `CTA-cardio.nii.gz` (60.3 MiB), and **Analyze scan** uploaded it and created case `788812d5bc03`. The real pipeline completed in **32.56 seconds**, including **11.24 seconds** of neural inference, and the results workspace displayed all seven structures and their measurements. The measurements JSON link triggered a browser download. The backend's separate HTTP smoke test verifies downloadable artifact contents; see `BACKEND.md`.

The interface was revised into a CT analysis workspace with a larger dark 3D viewport, a visible 3 mm model-grid badge, a case summary, direct access to overlays and exports, and the anatomy/measurement controls beside the viewer. The initial camera frames the cardiac region; **Fit all** shows the full exported extent. The layout was visually checked at desktop width and a 390 px mobile viewport.

## Limits

- WebGL is required for 3D rendering. A viewer failure leaves the preview and download controls available.
- The model's 3 mm inference grid produces visibly coarse surfaces. Rendering does not improve segmentation accuracy; no smoothing conceals this limitation.
- The demo aorta reaches the scan boundary, and its left ventricle contains three disconnected components. These are preserved and reported.
- This is a local research prototype, without accounts, clinical validation, or cancellation of running jobs. Browser refresh can resume monitoring by case ID.
- Docker packaging is outside this frontend checkpoint. No model training or fine-tuning was performed.
