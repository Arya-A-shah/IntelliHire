import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function RoleToggle({ role, onChange, className }) {
  return (
    <div
      className={cn(
        "inline-flex w-full items-center justify-center rounded-lg bg-muted p-1 ring-1 ring-ring/20",
        className
      )}
      role="tablist"
      aria-label="User type"
    >
      <Button
        type="button"
        variant="ghost"
        className={cn(
          "w-1/2 rounded-md transition-all",
          role === "candidate"
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
        )}
        aria-pressed={role === "candidate"}
        onClick={() => onChange("candidate")}
      >
        I’m a Candidate
      </Button>
      <Button
        type="button"
        variant="ghost"
        className={cn(
          "w-1/2 rounded-md transition-all",
          role === "recruiter"
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
        )}
        aria-pressed={role === "recruiter"}
        onClick={() => onChange("recruiter")}
      >
        I’m a Recruiter
      </Button>
    </div>
  );
}
