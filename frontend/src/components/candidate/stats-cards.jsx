import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatsCards({ stats, className }) {
  return (
    <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-3", className)}>
      {stats.map((s) => (
        <Card
          key={s.label}
          className="bg-card/70 backdrop-blur supports-[backdrop-filter]:bg-card/70 border-border transition-colors"
        >
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">{s.label}</p>
            <div className="mt-1 text-2xl md:text-3xl font-semibold text-foreground">
              {s.value}
            </div>
            {s.hint ? (
              <p className="mt-1 text-xs text-muted-foreground">{s.hint}</p>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
