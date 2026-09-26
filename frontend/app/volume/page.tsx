"use client";
import dynamic from "next/dynamic";
const VolumeViewer = dynamic(() => import("@/components/VolumeViewer"), { ssr: false, loading: () => <main>Loading CT viewer…</main> });
export default function VolumePage() { return <VolumeViewer />; }
