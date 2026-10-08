import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// FIX: these numbers used to be hard-coded ("12", "48", "19", "27%").
// They now come from GET /jobs/stats.
export function StatsCards({ data, isLoading }) {
  const show = (v, suffix = "") => (isLoading ? "…" : `${v ?? 0}${suffix}`);
  const stats = [
    { label: "Active Jobs", value: show(data?.active_jobs) },
    { label: "New Candidates (7d)", value: show(data?.new_candidates_7d) },
    { label: "Interviews Scheduled", value: show(data?.interviews_scheduled) },
    { label: "Offer Rate", value: show(data?.offer_rate, "%") },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
      {stats.map((s) => (
        <Card
          key={s.label}
          className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/50"
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">
              {s.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl lg:text-2xl font-semibold tracking-tight">
              {s.value}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
