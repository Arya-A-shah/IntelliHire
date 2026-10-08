import { Link } from "react-router"
import { Button } from "@/components/ui/button"

export function CTA() {
  return (
    <section className="mx-auto w-full max-w-5xl px-4 pb-16 md:pb-24">
      <div className="rounded-2xl border border-border/40 bg-card/60 p-6 text-center shadow-lg backdrop-blur-xl md:p-10">
        <h3 className="text-balance text-3xl font-semibold md:text-4xl">Ready to interview smarter?</h3>
        <p className="mx-auto mt-2 max-w-xl text-pretty text-base text-muted-foreground md:text-lg">
          Join teams using IntelliHire to streamline interviews and make confident, fair hiring decisions.
        </p>
        <div className="mt-6 flex items-center justify-center gap-2">
          <Link href="/auth">
            <Button className="rounded-xl">Create account</Button>
          </Link>
          <Link href="/auth">
            <Button variant="secondary" className="rounded-xl">
              Sign in
            </Button>
          </Link>
        </div>
      </div>
    </section>
  )
}
