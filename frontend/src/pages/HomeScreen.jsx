import { Hero } from "@/components/home/hero"
import { Features } from "@/components/home/features"
import { CTA } from "@/components/home/cta"

export default function HomePage() {
  return (
    <div className="min-h-dvh bg-background">
      <Hero />
      <Features />
      <CTA />
      <footer className="mx-auto w-full max-w-6xl px-4 pb-8 pt-4 text-center text-xs text-muted-foreground">
        <p>© {new Date().getFullYear()} IntelliHire. All rights reserved.</p>
      </footer>
    </div>
  )
}