import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DEV_CORE Platform",
  description: "Modern operational interface for DEV_CORE.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
