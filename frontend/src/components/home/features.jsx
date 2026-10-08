import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function Features() {
  const items = [
    {
      title: "Candidate experience",
      body: "Guided sessions with clear expectations and instant feedback.",
    },
    {
      title: "Recruiter efficiency",
      body: "Automate screening and compare candidates with structured scorecards.",
    },
    {
      title: "Team alignment",
      body: "Shared rubrics keep interviewers calibrated and consistent.",
    },
    {
      title: "Privacy-first",
      body: "Enterprise-grade security with role-based access controls.",
    },
    {
      title: "Integrations",
      body: "Connect calendars, ATS, and communication tools seamlessly.",
    },
    {
      title: "Analytics",
      body: "Spot bottlenecks and improve processes with data-driven insights.",
    },
  ]

  return (
    <section id="features" className="mx-auto w-full max-w-6xl px-4 py-12 md:py-16">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-balance text-3xl font-semibold md:text-4xl">
          Everything you need to run world-class interviews
        </h2>
        <p className="mt-2 text-base text-muted-foreground md:text-lg">
          Thoughtful design, smart automation, and reliable insights—all in one place.
        </p>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {items.map((f, i) => (
          <Card
            key={i}
            className="rounded-2xl border-border/40 bg-card/60 shadow-lg backdrop-blur-xl transition-transform hover:scale-[1.01]"
          >
            <CardHeader>
              <CardTitle className="text-lg">{f.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base text-muted-foreground">{f.body}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
