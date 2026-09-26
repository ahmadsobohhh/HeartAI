"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import "@kitware/vtk.js/Rendering/Profiles/Volume";
import "@kitware/vtk.js/Rendering/Profiles/Geometry";
import vtkActor from "@kitware/vtk.js/Rendering/Core/Actor";
import vtkMapper from "@kitware/vtk.js/Rendering/Core/Mapper";
import vtkCellPicker from "@kitware/vtk.js/Rendering/Core/CellPicker";
import vtkPlane from "@kitware/vtk.js/Common/DataModel/Plane";
import vtkGenericRenderWindow from "@kitware/vtk.js/Rendering/Misc/GenericRenderWindow";
import vtkImageData from "@kitware/vtk.js/Common/DataModel/ImageData";
import vtkDataArray from "@kitware/vtk.js/Common/Core/DataArray";
import vtkVolume from "@kitware/vtk.js/Rendering/Core/Volume";
import vtkVolumeMapper from "@kitware/vtk.js/Rendering/Core/VolumeMapper";
import vtkColorTransferFunction from "@kitware/vtk.js/Rendering/Core/ColorTransferFunction";
import vtkPiecewiseFunction from "@kitware/vtk.js/Common/DataModel/PiecewiseFunction";
import { decodeCT, presets, type Preset } from "@/lib/ct-volume";
import { parseSurface, verifyArtifact, displayName, type SurfaceState } from "@/lib/segmentation-surfaces";
import { clippingGeometry, clipAxisIndex, defaultClip, cardiacAvailability, artifactHash, type ClipState, type ClipAxis, type ViewerManifest, type Measurement } from "@/lib/viewer-controls";
import CaseInspector from "./CaseInspector";
import styles from "./VolumeViewer.module.css";

const base = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
type Manifest = ViewerManifest;
type Mode = "combined" | "ct" | "segmentation";
type Viewer = { preset: (p: Preset) => void; reset: () => void; pan: (amount: number) => void; surface: (name: string, patch: Partial<SurfaceState>) => void; select: (name: string | null) => void; mode: (mode: Mode) => void; ctOpacity: (value: number) => void; clip: (state: ClipState) => void; cardiac: () => void; focus: () => void };

export default function VolumeViewer() {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const [caseInput, setCaseInput] = useState("PUBLIC-001-D-final");
  const [caseId, setCaseId] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState("Open a completed case to explore its original CT.");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [preset, setPreset] = useState<Preset>("contrast");
  const [details, setDetails] = useState<Record<string, unknown> | null>(null);
  const [surfaces, setSurfaces] = useState<SurfaceState[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("combined");
  const [ctOpacity, setCtOpacity] = useState(.15);
  const [surfaceError, setSurfaceError] = useState("");
  const [surfaceStatus, setSurfaceStatus] = useState("");
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [measurements, setMeasurements] = useState<Record<string, Measurement> | null>(null);
  const [measurementError, setMeasurementError] = useState("");
  const [clip, setClip] = useState<ClipState>(defaultClip);
  const [bounds, setBounds] = useState<number[]>([-1, 1, -1, 1, -1, 1]);
  const [focusMessage, setFocusMessage] = useState("");
  const [surfaceReady, setSurfaceReady] = useState(false);

  useEffect(() => {
    if (!caseId || !host.current) return;
    const controller = new AbortController();
    let dispose = () => {};
    let cancelled = false;
    setReady(false); setError(""); setDetails(null);
    setSurfaces([]); setSelected(null); setSurfaceError(""); setSurfaceStatus(""); setMode("combined"); setCtOpacity(.15);
    setManifest(null); setMeasurements(null); setMeasurementError(""); setClip(defaultClip); setFocusMessage(""); setSurfaceReady(false);
    async function load() {
      try {
        const request = async (suffix: string) => {
          const response = await fetch(`${base}/api/cases/${encodeURIComponent(caseId)}${suffix}`, { signal: controller.signal });
          if (!response.ok) throw new Error(`Case request failed (${response.status}). Check the case ID and backend.`);
          return response;
        };
        setStatus("Loading case manifest…");
        const manifest: Manifest = await (await request("")).json();
        if (manifest.status !== "complete" || !manifest.input?.affine) throw new Error("A completed TotalSegmentator case is required.");
        if (cancelled) return;
        setManifest(manifest);
        void (async () => {
          try {
            const bytes = await (await request("/measurements")).arrayBuffer();
            await verifyArtifact(bytes, artifactHash(manifest, manifest.artifacts.measurements));
            const values = JSON.parse(new TextDecoder().decode(bytes));
            if (!values || typeof values !== "object" || Array.isArray(values)) throw new Error("Invalid measurements file.");
            if (!cancelled) setMeasurements(values);
          } catch (e) { if (!cancelled) setMeasurementError(e instanceof Error ? e.message : "Measurements unavailable."); }
        })();
        setStatus("Downloading original CT…");
        const buffer = await (await request("/volume")).arrayBuffer();
        const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", buffer)), b => b.toString(16).padStart(2, "0")).join("");
        if (sha256 !== manifest.input.sha256) throw new Error("CT checksum does not match the case manifest.");
        setStatus("Decoding CT and checking physical coordinates…");
        const ct = await decodeCT(buffer, manifest.input);
        if (cancelled || !host.current) return;
        const probe = document.createElement("canvas");
        const gl = probe.getContext("webgl2");
        if (!gl || gl.getParameter(gl.MAX_3D_TEXTURE_SIZE) < Math.max(...ct.dimensions)) throw new Error("WebGL 2 with sufficient 3D texture capacity is required.");
        const debug = gl.getExtension("WEBGL_debug_renderer_info");
        const rendererName = debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
        gl.getExtension("WEBGL_lose_context")?.loseContext();
        const window = vtkGenericRenderWindow.newInstance({ background: [.035, .055, .08], listenWindowResize: false });
        const image = vtkImageData.newInstance();
        const scalars = vtkDataArray.newInstance({ name: "CT intensity", values: ct.values, numberOfComponents: 1 });
        const mapper = vtkVolumeMapper.newInstance();
        const actor = vtkVolume.newInstance();
        const color = vtkColorTransferFunction.newInstance();
        const opacity = vtkPiecewiseFunction.newInstance();
        const resize = new ResizeObserver(() => window.resize());
        dispose = () => { resize.disconnect(); viewer.current = null; window.delete(); actor.delete(); mapper.delete(); image.delete(); scalars.delete(); color.delete(); opacity.delete(); };
        window.setContainer(host.current);
        image.setDimensions(ct.dimensions); image.setOrigin(ct.origin as [number, number, number]); image.setSpacing(ct.spacing); image.setDirection(ct.direction as [number, number, number, number, number, number, number, number, number]);
        image.getPointData().setScalars(scalars);
        const worldBounds = Array.from(image.getBounds()); setBounds(worldBounds);
        mapper.setInputData(image); mapper.setSampleDistance(Math.min(...ct.spacing) * .75);
        mapper.setMaximumSamplesPerRay(Math.ceil(Math.hypot(...ct.dimensions.map((n, i) => n * ct.spacing[i])) / mapper.getSampleDistance()) + 1);
        actor.setMapper(mapper);
        const property = actor.getProperty();
        property.setRGBTransferFunction(0, color); property.setScalarOpacity(0, opacity);
        property.setScalarOpacityUnitDistance(0, 1); property.setInterpolationTypeToLinear();
        property.setShade(true); property.setAmbient(.25); property.setDiffuse(.7); property.setSpecular(.15);
        const renderer = window.getRenderer();
        renderer.addVolume(actor);
        const entries = new Map<string, { actor: ReturnType<typeof vtkActor.newInstance>; mapper: ReturnType<typeof vtkMapper.newInstance>; parsed: ReturnType<typeof parseSurface>; state: SurfaceState; sha256: string }>();
        const picker = vtkCellPicker.newInstance();
        const plane = vtkPlane.newInstance();
        let currentClip = { ...defaultClip };
        picker.setPickFromList(true);
        let currentMode: Mode = "combined", currentSelection: string | null = null, ctAlpha = .15, currentPreset: Preset = "contrast";
        const surfaceHost = host.current;
        let pointerStart: [number, number] | null = null;
        const pointerDown = (event: PointerEvent) => { pointerStart = event.button === 0 ? [event.clientX, event.clientY] : null; };
        const pointerUp = (event: PointerEvent) => {
          if (!pointerStart || event.button !== 0 || event.shiftKey || event.ctrlKey || event.altKey || Math.hypot(event.clientX - pointerStart[0], event.clientY - pointerStart[1]) > 4) return;
          pointerStart = null;
          const canvas = surfaceHost.querySelector("canvas");
          if (!canvas) return;
          const rect = canvas.getBoundingClientRect();
          picker.pick([(event.clientX - rect.left) * canvas.width / rect.width, (rect.bottom - event.clientY) * canvas.height / rect.height, 0], renderer);
          const picked = picker.getActors()[0];
          selectSurface(Array.from(entries).find(([, entry]) => entry.actor === picked)?.[0] ?? null);
        };
        surfaceHost.addEventListener("pointerdown", pointerDown);
        surfaceHost.addEventListener("pointerup", pointerUp);
        const baseCleanup = dispose;
        dispose = () => {
          surfaceHost.removeEventListener("pointerdown", pointerDown); surfaceHost.removeEventListener("pointerup", pointerUp);
          picker.delete(); plane.delete();
          for (const entry of entries.values()) { renderer.removeActor(entry.actor); entry.actor.delete(); entry.mapper.delete(); entry.parsed.poly.delete(); entry.parsed.reader.delete(); }
          entries.clear(); baseCleanup();
        };
        const render = () => window.getRenderWindow().render();
        const syncSurfaces = () => {
          picker.initializePickList();
          for (const [name, entry] of entries) {
            const visible = currentMode !== "ct" && entry.state.visible;
            entry.actor.setVisibility(visible);
            entry.actor.getProperty().setOpacity(entry.state.opacity);
            entry.actor.getProperty().setAmbient(name === currentSelection ? .5 : .15);
            entry.actor.getProperty().setSpecular(name === currentSelection ? .5 : .2);
            if (visible && entry.state.opacity > 0) picker.addPickList(entry.actor);
          }
          setSurfaces(Array.from(entries.values(), entry => ({ ...entry.state })));
          setDetails(previous => previous ? { ...previous, segmentation: Array.from(entries.values(), entry => ({ ...entry.state, rendered: entry.actor.getVisibility(), actualOpacity: entry.actor.getProperty().getOpacity(), boundsRAS: entry.parsed.bounds, sha256: entry.sha256 })), selected: currentSelection, mode: currentMode, ctOpacity: ctAlpha } : previous);
          setDetails(previous => previous ? { ...previous, clipping: { ...currentClip, normal: Array.from(plane.getNormal()), origin: Array.from(plane.getOrigin()), ctPlanes: mapper.getNumberOfClippingPlanes(), surfacePlanes: Array.from(entries.values(), e => e.mapper.getNumberOfClippingPlanes()) } } : previous);
          render();
        };
        const selectSurface = (name: string | null) => { currentSelection = name; setSelected(name); syncSurfaces(); };
        const camera = renderer.getActiveCamera();
        const recordCamera = () => setDetails(previous => previous ? { ...previous, camera: { position: Array.from(camera.getPosition()), focalPoint: Array.from(camera.getFocalPoint()), viewUp: Array.from(camera.getViewUp()) } } : previous);
        const interaction = window.getInteractor().getInteractorStyle().onEndInteractionEvent(recordCamera);
        const cleanup = dispose;
        dispose = () => { interaction.unsubscribe(); cleanup(); };
        const applyPreset = (p: Preset) => {
          currentPreset = p;
          color.removeAllPoints(); opacity.removeAllPoints();
          for (const [hu, r, g, b, alpha] of presets[p].points) { color.addRGBPoint(hu, r, g, b); opacity.addPoint(hu, alpha * ctAlpha); }
          render();
        };
        const reset = () => {
          const center = image.getCenter();
          camera.setFocalPoint(...center); camera.setPosition(center[0], center[1] + 1000, center[2]); camera.setViewUp(0, 0, 1);
          renderer.resetCamera(); renderer.resetCameraClippingRange(); render(); recordCamera();
        };
        const applyClip = (value: ClipState) => {
          const geometry = clippingGeometry(value, worldBounds);
          currentClip = { ...value, position: geometry.position }; setClip(currentClip);
          plane.setNormal(...geometry.normal); plane.setOrigin(...geometry.origin);
          for (const target of [mapper, ...Array.from(entries.values(), e => e.mapper)]) {
            target.removeAllClippingPlanes(); if (value.enabled) target.addClippingPlane(plane);
          }
          syncSurfaces();
        };
        const focus = (name: string | null) => {
          const target = name ? entries.get(name) : undefined;
          if (!target) return;
          const b = target.parsed.bounds;
          const center = [0, 1, 2].map(i => (b[2 * i] + b[2 * i + 1]) / 2);
          camera.setFocalPoint(...center as [number, number, number]); camera.setPosition(center[0], center[1] + 1000, center[2]); camera.setViewUp(0, 0, 1);
          renderer.resetCamera(b as [number, number, number, number, number, number]); renderer.resetCameraClippingRange(); render(); recordCamera();
        };
        const pan = (amount: number) => {
          const forward = camera.getDirectionOfProjection(), up = camera.getViewUp();
          const right = [forward[1] * up[2] - forward[2] * up[1], forward[2] * up[0] - forward[0] * up[2], forward[0] * up[1] - forward[1] * up[0]];
          const offset = right.map(v => v * amount / Math.hypot(...right));
          camera.setPosition(...camera.getPosition().map((v, i) => v + offset[i]) as [number, number, number]);
          camera.setFocalPoint(...camera.getFocalPoint().map((v, i) => v + offset[i]) as [number, number, number]);
          renderer.resetCameraClippingRange(); render(); recordCamera();
        };
        viewer.current = { preset: applyPreset, reset, pan,
          clip: applyClip, focus: () => focus(currentSelection),
          cardiac: () => {
            const available = cardiacAvailability(Array.from(entries.keys()));
            if (!available.available.length) { setFocusMessage("No reconstructed cardiac structures are available."); return; }
            for (const [name, entry] of entries) { entry.state.visible = available.available.includes(name); entry.state.opacity = .85; }
            currentMode = "combined"; setMode("combined"); actor.setVisibility(true); ctAlpha = .08; setCtOpacity(.08); setPreset("contrast"); applyPreset("contrast");
            applyClip(defaultClip); selectSurface(entries.has("heart") ? "heart" : available.available[0]); focus(currentSelection);
            setFocusMessage(available.missing.length ? `Unavailable: ${available.missing.map(displayName).join(", ")}.` : "Available cardiac structures shown.");
          },
          surface: (name, patch) => { const entry = entries.get(name); if (entry) { Object.assign(entry.state, patch); syncSurfaces(); } },
          select: selectSurface,
          mode: value => { currentMode = value; actor.setVisibility(value !== "segmentation"); syncSurfaces(); },
          ctOpacity: value => { ctAlpha = value; applyPreset(currentPreset); syncSurfaces(); },
        };
        window.resize(); applyPreset("contrast"); reset(); resize.observe(host.current);
        const corners = [[0, 0, 0], ct.dimensions.map(n => n - 1)].map(ijk => ({ ijk, ras: Array.from(image.indexToWorld(ijk as [number, number, number])) }));
        setDetails({ caseId, sha256, dimensions: ct.dimensions, spacingMm: ct.spacing, originRAS: ct.origin, direction: ct.direction, boundsRAS: image.getBounds(), range: ct.range, corners, renderer: rendererName });
        recordCamera();
        setPreset("contrast"); setReady(true); setStatus("Original CT · physical RAS coordinates · millimetres");
        try {
          if (manifest.segmentation?.engine !== "TotalSegmentator" || !manifest.coordinates?.stl?.startsWith("RAS millimeters")) throw new Error("This case does not declare TotalSegmentator surfaces in RAS millimetres.");
          const specs = manifest.structures.filter(spec => spec.stl);
          if (!specs.length) throw new Error("No reconstructed surfaces are available in this case.");
          for (const spec of specs) {
            setSurfaceStatus(`Loading ${displayName(spec.name)}…`);
            const bytes = await (await request(`/mesh/${encodeURIComponent(spec.name)}?format=stl`)).arrayBuffer();
            const expectedHash = Object.entries(manifest.artifact_sha256).find(([path]) => path.replaceAll("\\", "/") === spec.stl.replaceAll("\\", "/"))?.[1];
            const surfaceHash = await verifyArtifact(bytes, expectedHash);
            if (cancelled) return;
            const parsed = parseSurface(bytes, spec);
            const surfaceActor = vtkActor.newInstance(), surfaceMapper = vtkMapper.newInstance();
            surfaceMapper.setInputData(parsed.poly); surfaceMapper.setScalarVisibility(false); surfaceActor.setMapper(surfaceMapper);
            const rgb = /^#[0-9a-f]{6}$/i.test(spec.color) ? [1, 3, 5].map(i => parseInt(spec.color.slice(i, i + 2), 16) / 255) : [.7, .7, .7];
            surfaceActor.getProperty().setColor(...rgb as [number, number, number]);
            surfaceActor.getProperty().setDiffuse(.75);
            entries.set(spec.name, { actor: surfaceActor, mapper: surfaceMapper, parsed, state: { name: spec.name, color: spec.color, visible: true, opacity: .85 }, sha256: surfaceHash });
            if (currentClip.enabled) surfaceMapper.addClippingPlane(plane);
            renderer.addActor(surfaceActor); syncSurfaces();
          }
          setSurfaceStatus(`${entries.size} verified surfaces loaded`);
          setSurfaceReady(true);
        } catch (e) { if (!cancelled) { setSurfaceStatus(""); setSurfaceError(e instanceof Error ? e.message : "Surface loading failed."); } }
      } catch (e) {
        if (!cancelled) { dispose(); dispose = () => {}; setError(e instanceof Error ? e.message : "CT viewer failed."); setStatus("Unable to render CT."); }
      }
    }
    void load();
    return () => { cancelled = true; controller.abort(); dispose(); };
  }, [caseId, attempt]);

  return <div className={styles.shell}>
    <header className={styles.header}><Link href="/">Heart<span>AI</span></Link><span>ANATOMY WORKSTATION</span><span>{manifest?.case_id ?? "No case loaded"} · Research prototype</span></header>
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.eyebrow}>SCAN-DERIVED ANATOMY</div><h1>Explore. Inspect.</h1>
        <form onSubmit={e => { e.preventDefault(); if (/^[A-Za-z0-9_-]{1,64}$/.test(caseInput)) { setCaseId(caseInput); setAttempt(a => a + 1); } else setError("Use a valid case ID: letters, numbers, underscores or hyphens."); }}>
          <label htmlFor="case-id">Completed case ID</label><input id="case-id" value={caseInput} onChange={e => setCaseInput(e.target.value)} />
          <button type="submit">Open CT</button>
        </form>
        <details className={styles.controls}><summary>CT preset & camera controls</summary><label htmlFor="ct-preset">Rendering preset</label>
        <select id="ct-preset" disabled={!ready} value={preset} onChange={e => { const p = e.target.value as Preset; setPreset(p); viewer.current?.preset(p); }}>
          {Object.entries(presets).map(([key, p]) => <option key={key} value={key}>{p.label}</option>)}
        </select>
        <button disabled={!ready} onClick={() => viewer.current?.reset()}>Reset anterior view</button>
        <div style={{ display: "flex", gap: 8 }}><button disabled={!ready} onClick={() => viewer.current?.pan(-25)}>Pan left</button><button disabled={!ready} onClick={() => viewer.current?.pan(25)}>Pan right</button></div></details>
        <label htmlFor="viewer-mode">View</label><select id="viewer-mode" disabled={!ready} value={mode} onChange={e => { const value = e.target.value as Mode; setMode(value); viewer.current?.mode(value); }}><option value="combined">CT + segmentation</option><option value="ct">CT only</option><option value="segmentation">Segmentation only</option></select>
        <label htmlFor="ct-opacity">CT opacity · {Math.round(ctOpacity * 100)}%</label><input id="ct-opacity" type="range" min="0" max="1" step=".01" value={ctOpacity} disabled={!ready || mode === "segmentation"} onChange={e => { const value = Number(e.target.value); setCtOpacity(value); viewer.current?.ctOpacity(value); }} />
        <details className={styles.controls} open><summary>Cutaway plane</summary>
          <label className={styles.checkLabel}><input type="checkbox" checked={clip.enabled} disabled={!ready} onChange={e => viewer.current?.clip({ ...clip, enabled: e.target.checked })} />Enable clipping</label>
          <label htmlFor="clip-axis">Plane orientation</label><select id="clip-axis" disabled={!ready} value={clip.axis} onChange={e => { const axis = e.target.value as ClipAxis, i = clipAxisIndex[axis]; viewer.current?.clip({ ...clip, axis, position: (bounds[i * 2] + bounds[i * 2 + 1]) / 2 }); }}><option value="axial">Axial · S</option><option value="coronal">Coronal · A</option><option value="sagittal">Sagittal · R</option></select>
          <label htmlFor="clip-position">Position · {clip.position.toFixed(1)} mm RAS</label><input id="clip-position" type="range" disabled={!ready || !clip.enabled} min={bounds[clipAxisIndex[clip.axis] * 2]} max={bounds[clipAxisIndex[clip.axis] * 2 + 1]} step=".5" value={clip.position} onChange={e => viewer.current?.clip({ ...clip, position: Number(e.target.value) })} />
          <label className={styles.checkLabel}><input type="checkbox" checked={clip.inverted} disabled={!ready} onChange={e => viewer.current?.clip({ ...clip, inverted: e.target.checked })} />Invert retained side</label>
          <button disabled={!ready} onClick={() => viewer.current?.clip(defaultClip)}>Reset clipping</button>
          <p className={styles.note}>Cuts CT and surfaces together. Surface cuts are open; no invented caps or chambers.</p>
        </details>
        <section className={styles.anatomy} aria-label="Segmentation structures"><h2>Anatomy</h2><p role="status">{surfaceStatus}</p>{surfaceError && <p role="alert">{surfaceError} Reopen the case to retry.</p>}
          {surfaces.map(surface => <div key={surface.name} className={styles.structure} data-selected={selected === surface.name}>
            <input type="checkbox" aria-label={`Show ${displayName(surface.name)}`} checked={surface.visible} disabled={mode === "ct"} onChange={e => viewer.current?.surface(surface.name, { visible: e.target.checked })} />
            <button aria-pressed={selected === surface.name} onClick={() => viewer.current?.select(surface.name)}><span style={{ background: surface.color }} />{displayName(surface.name)}</button>
          </div>)}
          {selected && <div className={styles.selection}><p>Selected: <strong>{displayName(selected)}</strong></p><label htmlFor="surface-opacity">Structure opacity · {Math.round((surfaces.find(s => s.name === selected)?.opacity ?? 0) * 100)}%</label><input id="surface-opacity" type="range" min="0" max="1" step=".05" value={surfaces.find(s => s.name === selected)?.opacity ?? 0} onChange={e => viewer.current?.surface(selected, { opacity: Number(e.target.value) })} /><button onClick={() => viewer.current?.select(null)}>Clear selection</button></div>}
        </section>
        <div className={styles.help}><h2>Move through the scan</h2><p>Drag to rotate<br />Shift + drag to pan<br />Scroll to zoom</p><p>Reset view: patient right appears on the left; superior is up.</p></div>
        <p className={styles.note}>Click a surface or its name to select it. Only reconstructed structures in this case are listed. Coronary arteries and separate heart chambers are unavailable in this default task. Research prototype; not for clinical use.</p>
        {details && <details><summary>Verified source & geometry</summary><pre>{JSON.stringify(details, null, 2)}</pre></details>}
      </aside>
      <section className={styles.stage} aria-label="Interactive CT volume">
        <div className={styles.viewport} ref={host} />
        <div className={styles.toolbar}><button disabled={!surfaceReady} onClick={() => viewer.current?.cardiac()}>Cardiac Focus</button><button disabled={!selected} onClick={() => viewer.current?.focus()}>Focus selected</button><button disabled={!ready} onClick={() => viewer.current?.reset()}>Fit full CT</button></div>
        <div className={styles.caption}><span className={ready ? styles.dot : ""} />{status}</div>
        {focusMessage && <div className={styles.focusMessage} role="status">{focusMessage}</div>}
        {(!ready || error) && <div className={styles.message} role={error ? "alert" : "status"}>{error || status}</div>}
        <div className={styles.footer}>VTK.js · WebGL 2<span>{ready ? presets[preset].label : "Awaiting CT"}</span></div>
      </section>
      <CaseInspector key={`${caseId}-${attempt}`} manifest={manifest} selected={selected} measurements={measurements} measurementError={measurementError} base={base} />
    </div>
  </div>;
}
