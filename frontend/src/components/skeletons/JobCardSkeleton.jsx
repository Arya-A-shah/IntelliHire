import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function JobCardSkeleton({ className }) {
  return (
    <Card
      className={cn(
        "bg-card/70 backdrop-blur supports-[backdrop-filter]:bg-card/70 border-border animate-pulse",
        className
      )}
    >
      <CardHeader className="space-y-2">
        <div className="h-6 w-3/4 bg-muted rounded-md" />
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <div className="h-4 w-16 bg-muted rounded-md" />
          <div className="h-4 w-16 bg-muted rounded-md" />
          <div className="h-4 w-16 bg-muted rounded-md" />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          <div className="h-6 w-16 bg-muted rounded-full" />
          <div className="h-6 w-16 bg-muted rounded-full" />
          <div className="h-6 w-16 bg-muted rounded-full" />
        </div>
        <div className="h-10 w-full bg-muted rounded-md" />
      </CardContent>
    </Card>
  );
}
