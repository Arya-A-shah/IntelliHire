import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { useMyInterviews } from "@/hooks/interviewHooks";
import { CandidateDrawer } from "./candidate-drawer";
import CandidateTableSkeleton from "../skeletons/CandidateTableSkeleton";

// FIX: the Interviews tab used to be a fixed "No interviews scheduled"
// message. This lists every interview from GET /interviews/my.

const STATUS_LABEL = {
  scheduled: "Scheduled",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
  no_show: "No show",
  rescheduled: "Rescheduled",
};

function reportText(row) {
  if (row.status !== "completed") return "-";
  if (row.report_status === "ready") return "Ready";
  if (row.report_status === "failed") return "Failed";
  return "Writing…";
}

export function InterviewsTable() {
  const { data: rows = [], isLoading, isError } = useMyInterviews();
  const [current, setCurrent] = useState(null);

  const copyLink = async (url) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Interview link copied");
    } catch {
      toast.error("Could not copy the link");
    }
  };

  if (isLoading) return <CandidateTableSkeleton />;
  if (isError) {
    return (
      <Card className="p-6 text-center text-destructive">
        Failed to load interviews. Please try again later.
      </Card>
    );
  }

  return (
    <>
      <Card className="rounded-2xl border border-border/60 bg-card/60 p-3 lg:p-4">
        {rows.length === 0 ? (
          <div className="rounded-xl border border-border/60 p-8 text-center text-muted-foreground">
            No interviews yet. Move a candidate to the "Interview" stage to send
            them an AI interview.
          </div>
        ) : (
          <div className="rounded-xl border border-border/60 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Candidate</TableHead>
                  <TableHead>Job</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Integrity</TableHead>
                  <TableHead>Report</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.interview_id}>
                    <TableCell className="font-medium">
                      {row.application?.candidate?.name ?? "Unknown"}
                      <div className="text-xs text-muted-foreground">
                        {row.application?.candidate?.email}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {row.application?.job?.title ?? "-"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={row.status === "completed" ? "default" : "secondary"}
                        className="rounded-full"
                      >
                        {STATUS_LABEL[row.status] ?? row.status}
                      </Badge>
                      {row.status === "scheduled" && !row.questions_ready && (
                        <div className="text-[11px] text-muted-foreground mt-1">
                          Preparing questions…
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      {row.score !== null && row.score !== undefined
                        ? `${row.score} / 100`
                        : "-"}
                    </TableCell>
                    <TableCell>{row.integrity_grade ?? "-"}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {reportText(row)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {row.meeting_url && row.status !== "completed" && (
                          <Button
                            variant="ghost"
                            className="rounded-xl"
                            onClick={() => copyLink(row.meeting_url)}
                          >
                            Copy link
                          </Button>
                        )}
                        <Button
                          variant="secondary"
                          className="rounded-xl"
                          disabled={!row.application}
                          onClick={() => setCurrent(row.application)}
                        >
                          View
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      <CandidateDrawer
        open={!!current}
        onOpenChange={(open) => !open && setCurrent(null)}
        application={current}
      />
    </>
  );
}
