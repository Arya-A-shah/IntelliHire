import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CandidateDrawer } from "./candidate-drawer";
import { X } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useRankedApplications,
  useRecruiterApplications,
} from "@/hooks/applicationHooks";
import { candidateCsvColumns, downloadCsv } from "@/lib/csv";
import CandidateTableSkeleton from "../skeletons/CandidateTableSkeleton";

export function CandidateTable({ jobId, onClearFilter }) {
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("all");
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState();

  // A job selected -> that job's applicants; otherwise -> every applicant.
  // FIX: before, with no job selected the query was disabled and the table
  // stayed empty, so the Candidates tab looked blank.
  const perJob = useRankedApplications(jobId);
  const all = useRecruiterApplications({ enabled: !jobId });
  const { data: applications = [], isLoading, isError } = jobId ? perJob : all;

  const filtered = useMemo(() => {
    return applications.filter((app) => {
      const mQ = q
        ? app.candidate?.name?.toLowerCase().includes(q.toLowerCase()) ||
          app.candidate?.email?.toLowerCase().includes(q.toLowerCase()) ||
          app.job?.title?.toLowerCase().includes(q.toLowerCase())
        : true;
      const mS = stage === "all" ? true : app.status?.toLowerCase() === stage;
      return mQ && mS;
    });
  }, [applications, q, stage]);

  const exportCsv = () => {
    const date = new Date().toISOString().slice(0, 10);
    downloadCsv(`candidates-${date}.csv`, candidateCsvColumns, filtered);
  };

  const openDrawer = (app) => {
    setCurrent(app);
    setOpen(true);
  };

  if (isLoading) {
    return <CandidateTableSkeleton />;
  }

  if (isError) {
    return (
      <Card className="p-6 text-center text-destructive">
        Failed to load candidates. Please try again later.
      </Card>
    );
  }

  return (
    <>
      <Card className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/50 p-3 lg:p-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-2 lg:gap-3 mb-3">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by candidate or role"
            className="rounded-xl"
          />
          <div className="flex gap-2">
            <Select value={stage} onValueChange={setStage}>
              <SelectTrigger className="w-40 rounded-xl">
                <SelectValue placeholder="Stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                <SelectItem value="applied">Applied</SelectItem>
                <SelectItem value="reviewed">Screening</SelectItem>
                <SelectItem value="interview">Interview</SelectItem>
                <SelectItem value="offer">Offer</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            {/* FIX: this button had no onClick. Exports what's shown (search + stage filter). */}
            <Button
              variant="secondary"
              className="rounded-xl"
              onClick={exportCsv}
              disabled={filtered.length === 0}
            >
              Export CSV
            </Button>
          </div>
        </div>

        {jobId && (
          <div className="mb-3 flex items-center gap-2">
            <Badge variant="secondary" className="rounded-full">
              Filtered by Job
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 rounded-full"
              onClick={onClearFilter}
            >
              <X className="h-3 w-3 mr-1" />
              Clear filter
            </Button>
          </div>
        )}

        {filtered.length === 0 ? (
          <div className="rounded-xl border border-border/60 p-8 text-center">
            <div className="text-muted-foreground">
              {jobId
                ? "No candidates have applied to this job yet."
                : "No candidates found."}
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-border/60 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Candidate</TableHead>
                  <TableHead>Job Applied</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Match Score</TableHead>
                  <TableHead>Applied Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((app, index) => (
                  <TableRow key={app._id || `app-${index}`}>
                    <TableCell className="font-medium">
                      {app.candidate?.name || "N/A"}{" "}
                      <span className="text-muted-foreground">
                        ({app.candidate?.email || "N/A"})
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {app.job?.title || "N/A"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        className="rounded-full"
                        variant={
                          app.status === "offer"
                            ? "default"
                            : app.status === "interview"
                            ? "secondary"
                            : app.status === "rejected"
                            ? "outline"
                            : "secondary"
                        }
                      >
                        {app.status || "Applied"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {app.match_score !== null &&
                      app.match_score !== undefined ? (
                        <div className="flex items-center gap-2">
                          <div className="text-sm font-medium">
                            {Math.round(app.match_score)}
                          </div>
                          <div className="w-24 h-2 rounded-full bg-muted">
                            <div
                              className="h-2 rounded-full bg-primary"
                              style={{ width: `${app.match_score}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">
                          Calculating...
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(app.applied_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        className="rounded-xl"
                        variant="secondary"
                        onClick={() => openDrawer(app)}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      <CandidateDrawer
        open={open}
        onOpenChange={setOpen}
        application={current}
      />
    </>
  );
}
