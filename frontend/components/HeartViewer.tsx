"use client";
import { Component, Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, Html, OrbitControls, useBounds, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { meshUrl } from "@/lib/api";
import type { Structure, ViewSettings } from "@/types/heartai";

interface Props { caseId: string; structures: Structure[]; views: ViewSettings; selected: string; onSelect: (name: string) => void; focus: { name: string | null; sequence: number } }
class ViewerBoundary extends Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <div className="viewer-message" role="alert"><strong>The 3D viewer could not load.</strong><p>Check that the analysis server is running and your browser supports WebGL. The segmentation preview and downloads are still available.</p><button className="secondary" onClick={() => this.setState({ failed: false })}>Retry viewer</button></div> : this.props.children; }
}

function Anatomy({ source, structure, visible, opacity, selected, onSelect }: { source: THREE.Object3D; structure: Structure; visible: boolean; opacity: number; selected: boolean; onSelect: () => void }) {
  const object = useMemo(() => {
    const clone = source.clone(true);
    clone.traverse(child => { if (child instanceof THREE.Mesh) child.material = new THREE.MeshStandardMaterial({ color: structure.color, roughness: 0.55, metalness: 0.04 }); });
    return clone;
  }, [source, structure.color]);
  useEffect(() => {
    object.traverse(child => {
      if (child instanceof THREE.Mesh) {
        const material = child.material as THREE.MeshStandardMaterial;
        material.opacity = opacity; material.transparent = opacity < 1; material.depthWrite = opacity >= 1;
        material.emissive.set(structure.color); material.emissiveIntensity = selected ? 0.12 : 0;
      }
    });
  }, [object, opacity, selected, structure.color]);
  useEffect(() => () => { object.traverse(child => { if (child instanceof THREE.Mesh) (child.material as THREE.Material).dispose(); }); }, [object]);
  return <primitive object={object} visible={visible} onClick={(event: { stopPropagation: () => void }) => { event.stopPropagation(); onSelect(); }} />;
}

function Scene({ caseId, structures, views, selected, onSelect, focus }: Props) {
  const { scene } = useGLTF(meshUrl(caseId));
  const group = useRef<THREE.Group>(null);
  const bounds = useBounds();
  useEffect(() => {
    if (!group.current) return;
    const target = focus.name ? group.current.getObjectByName(focus.name) : group.current;
    if (target) bounds.refresh(target).reset().clip().fit();
  }, [bounds, scene, focus]);
  return <group ref={group}>{structures.map(structure => {
    const source = scene.getObjectByName(structure.name);
    if (!source) throw new Error(`Missing exported structure: ${structure.name}`);
    return <Anatomy key={structure.name} source={source} structure={structure} visible={views[structure.name]?.visible ?? true}
      opacity={views[structure.name]?.opacity ?? 1} selected={selected === structure.name} onSelect={() => onSelect(structure.name)} />;
  })}</group>;
}

export default function HeartViewer(props: Props) {
  return <ViewerBoundary><Canvas camera={{ position: [0.3, 0.16, -0.5], fov: 35, near: 0.001, far: 10 }} dpr={[1, 2]} gl={{ antialias: true }} fallback={<div className="viewer-message">WebGL is unavailable. Use the CT overlay or download the GLB.</div>}>
    <color attach="background" args={["#111b27"]} />
    <ambientLight intensity={1.45} /><directionalLight position={[2, 3, -4]} intensity={3.5} /><directionalLight position={[-2, 1, 3]} intensity={1.6} />
    <Suspense fallback={<Html center><div className="mesh-loading">Loading real anatomy…</div></Html>}>
      <Bounds margin={props.focus.name ? 2.6 : 1.2}><Scene {...props} /></Bounds>
    </Suspense>
    <OrbitControls makeDefault minDistance={0.025} maxDistance={3} enableDamping />
  </Canvas></ViewerBoundary>;
}
