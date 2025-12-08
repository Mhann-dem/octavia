
"use client";

import { Navbar } from "@/components/landing/Navbar";
import { HeroSection } from "@/components/landing/HeroSection";
import { PartnersSlider } from "@/components/landing/PartnersSlider";
import { FeaturesGrid } from "@/components/landing/FeaturesGrid";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { LiveDemo } from "@/components/landing/LiveDemo";
import { GlobalScale } from "@/components/landing/GlobalScale";
import { PricingPreview } from "@/components/landing/PricingPreview";
import { CTAFooter } from "@/components/landing/CTAFooter";
import { useEffect, useState } from "react";
import { fetchSession } from "@/lib/auth";
import Link from "next/link";

// Main Landing Page
export default function Home() {
  const [session, setSession] = useState<any | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchSession().then((data) => {
      if (!mounted) return;
      setSession(data);
    });
    return () => { mounted = false };
  }, []);
  return (
    <main className="min-h-screen selection:bg-primary-purple/30 selection:text-white">
      <Navbar />
      {session && session.authenticated && (
        <div className="container mx-auto px-6 mt-6">
          <div className="rounded-md bg-green-900/60 p-3 text-sm text-green-200 flex items-center justify-between">
            <div>You're signed in. <Link href="/dashboard" className="underline">Go to dashboard</Link></div>
            <div className="text-xs opacity-80">Welcome back</div>
          </div>
        </div>
      )}
      <HeroSection />
      <PartnersSlider />
      <FeaturesGrid />
      <HowItWorks />
      <LiveDemo />
      <GlobalScale />
      <PricingPreview />
      <CTAFooter />
    </main>
  );
}
