import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Octavia | Universal AI Translation",
  description: "The world's most advanced AI dubbing and translation platform. Translate video, audio, and subtitles with perfect lip-sync.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppress hydration warnings on the root html element to avoid
    // client extension-injected attribute mismatches that block hydration
    // (see React hydration-mismatch docs).
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-bg-dark text-white`}
      >
        {children}
      </body>
    </html>
  );
}
