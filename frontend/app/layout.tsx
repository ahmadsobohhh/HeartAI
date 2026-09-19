import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "HeartAI · Cardiac reconstruction", description: "Local cardiac CT segmentation and anatomy exploration. Research prototype." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
