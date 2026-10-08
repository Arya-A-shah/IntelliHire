import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Home, Briefcase, Users, Calendar } from "lucide-react";

const items = [
  { key: "overview", label: "Overview", icon: Home },
  { key: "jobs", label: "Jobs", icon: Briefcase },
  { key: "candidates", label: "Candidates", icon: Users },
  { key: "interviews", label: "Interviews", icon: Calendar },
];

export function RecruiterSidebar({ active, onChange, className }) {
  return (
    <aside
      className={cn(
        "rounded-2xl border border-border/60 bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/50 p-3 lg:p-4 h-fit sticky top-4",
        className
      )}
      aria-label="Recruiter navigation"
    >
      <div className="flex flex-col gap-1">
        {items.map((it) => {
          const Icon = it.icon;
          const isActive = active === it.key;
          return (
            <Button
              key={it.key}
              variant="ghost"
              className={cn(
                "justify-start gap-2 rounded-xl",
                isActive
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
              onClick={() => onChange(it.key)}
              aria-current={isActive ? "page" : undefined}
            >
              {Icon ? <Icon className="h-4 w-4" /> : null}
              <span className="text-sm lg:text-[0.95rem]">{it.label}</span>
            </Button>
          );
        })}
      </div>
    </aside>
  );
}
