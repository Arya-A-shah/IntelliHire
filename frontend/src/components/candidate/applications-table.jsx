import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";

function StatusBadge({ status }) {
  const normalized = status?.toLowerCase();
  const variant =
    normalized === "accepted"
      ? "default"
      : normalized === "rejected"
      ? "destructive"
      : normalized === "reviewed"
      ? "secondary"
      : "outline";
  return (
    <Badge
      variant={variant}
      className={cn(
        normalized === "applied" && "text-foreground border-border"
      )}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

// FIX: a candidate could only reach their interview through the email link.
// The new Interview column has a "Start interview" button when one is waiting.
function InterviewCell({ interview }) {
  if (!interview) return <span className="text-muted-foreground">-</span>;
  if (interview.status === "completed") {
    return <Badge variant="secondary">Completed</Badge>;
  }
  if (["scheduled", "in_progress"].includes(interview.status)) {
    return (
      <Button asChild size="sm">
        <Link to={`/interview/${interview.id}`}>
          {interview.status === "in_progress" ? "Rejoin interview" : "Start interview"}
        </Link>
      </Button>
    );
  }
  return <span className="text-muted-foreground capitalize">{interview.status}</span>;
}

export function ApplicationsTable({ items }) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-border p-8 text-center text-muted-foreground">
        You haven't applied to any jobs yet.
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-border bg-card/70 backdrop-blur supports-[backdrop-filter]:bg-card/70">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="text-muted-foreground">Position</TableHead>
            <TableHead className="text-muted-foreground">Company</TableHead>
            <TableHead className="text-muted-foreground">Applied</TableHead>
            <TableHead className="text-muted-foreground">Status</TableHead>
            <TableHead className="text-muted-foreground">Interview</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((a) => (
            <TableRow key={a.id} className="transition-colors">
              <TableCell className="font-medium text-foreground">
                {a.title}
              </TableCell>
              <TableCell className="text-foreground">{a.company}</TableCell>
              <TableCell className="text-foreground">{a.appliedAt}</TableCell>
              <TableCell>
                <StatusBadge status={a.status} />
              </TableCell>
              <TableCell>
                <InterviewCell interview={a.interview} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
