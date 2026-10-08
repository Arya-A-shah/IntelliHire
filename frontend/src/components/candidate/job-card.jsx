import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function JobCard({ job, className, onApply }) {
  return (
    <Card
      className={cn(
        "bg-card/70 backdrop-blur supports-[backdrop-filter]:bg-card/70 border-border transition-colors",
        className
      )}
    >
      <CardHeader className="space-y-1">
        <CardTitle className="text-pretty text-lg md:text-xl text-foreground">
          {job.title}
        </CardTitle>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          {job.recruiter_name && (
            <>
              <span className="font-medium text-foreground">{job.recruiter_name}</span>
              <span aria-hidden="true" className="text-muted-foreground">•</span>
            </>
          )}
          {job.location && <span>{job.location}</span>}
          {job.type && (
            <>
              <span aria-hidden="true" className="text-muted-foreground">•</span>
              <span>{job.type}</span>
            </>
          )}
          {job.postedAt && (
            <>
              <span aria-hidden="true" className="text-muted-foreground">•</span>
              <span>Posted {job.postedAt}</span>
            </>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {job.tags && job.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {job.tags.map((t) => (
              <Badge key={t} variant="secondary" className="rounded-full">
                {t}
              </Badge>
            ))}
          </div>
        )}
        <div className="flex items-center justify-end">
          <Button
            onClick={() => onApply?.(job.id)}
            className="transition-transform hover:scale-[1.02]"
          >
            Apply
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
