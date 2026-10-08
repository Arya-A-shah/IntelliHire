import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export function ResultsList({ items }) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-border p-8 text-center text-muted-foreground">
        No results yet. They appear here after you finish an AI interview.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {items.map((r) => (
        <Card
          key={r.id}
          className="bg-card/70 backdrop-blur supports-[backdrop-filter]:bg-card/70 border-border transition-colors"
        >
          <CardHeader className="space-y-1">
            <CardTitle className="text-pretty text-lg md:text-xl text-foreground">
              {r.title}
            </CardTitle>
            <div className="text-sm text-muted-foreground">{r.company}</div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Interview Score
              </span>
              <span className="text-sm font-medium text-foreground">
                {r.score !== null && r.score !== undefined ? `${r.score} / 100` : "Scoring…"}
              </span>
            </div>
            <Progress value={r.score ?? 0} />
            <div>
              <Badge
                variant={
                  r.outcome === "Accepted"
                    ? "default"
                    : r.outcome === "Rejected"
                    ? "destructive"
                    : "secondary"
                }
              >
                {r.outcome}
              </Badge>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
