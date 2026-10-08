import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { ResumePreview } from "./resume-preview";
import { useUpdateApplicationStatus } from "@/hooks/applicationHooks";
import { useInterviewReport } from "@/hooks/interviewHooks"; // ✅ import new hook
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { ReportText } from "./report-text";

export function CandidateDrawer({ open, onOpenChange, application }) {
  const candidate = application?.candidate;
  const job = application?.job;

  const [selectedStage, setSelectedStage] = useState(
    application?.status ?? "applied"
  );
  const [hasChanges, setHasChanges] = useState(false);

  const { mutate: updateStatus, isPending } = useUpdateApplicationStatus();

  // ✅ Only fetch report if candidate is in "interview" stage
  const {
    data: reportData,
    isLoading: reportLoading,
    isError: reportError,
  } = useInterviewReport(
    // FIX: fetch for every stage. Before, moving a candidate from "interview"
    // to "offer" or "rejected" hid their interview report.
    application?._id
  );

  useEffect(() => {
    if (application) {
      setSelectedStage(application.status ?? "applied");
      setHasChanges(false);
    }
  }, [application, open]);

  const handleStageChange = (value) => {
    setSelectedStage(value);
    setHasChanges(application?.status ? value !== application.status : false);
  };

  const handleSave = () => {
    if (!application?._id) {
      toast.error("No application selected");
      return;
    }

    updateStatus(
      { applicationId: application._id, status: selectedStage },
      {
        onSuccess: () => {
          toast.success(`Stage updated to "${selectedStage}" successfully 🎉`);
          setHasChanges(false);
        },
        onError: (err) => {
          toast.error(`Failed to update stage: ${err.message}`);
        },
      }
    );
  };

  // FIX: the integrity "score" is the AVERAGE NUMBER OF ALERTS per 30 seconds,
  // so LOWER is better. The old card treated it like a 0-10 score: a clean
  // candidate (0 alerts) got an empty red bar and a bad one got a green bar.
  const gradeColor = {
    A: "bg-green-500",
    B: "bg-lime-500",
    C: "bg-yellow-500",
    D: "bg-orange-500",
    F: "bg-red-500",
  };

  const renderIntegrityCard = (score) => {
    if (!score || score.score === undefined) return null;
    const alertLevel = Math.min(score.score / 5, 1) * 100; // 5+ alerts = full bar

    return (
      <div className="rounded-2xl border border-border/60 bg-card/60 p-4 mt-4">
        <div className="text-sm text-muted-foreground mb-2">Integrity</div>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-3xl font-bold">Grade {score.grade}</div>
            <div className="text-sm text-muted-foreground">
              {score.status} - {score.score} alerts per 30 s on average
            </div>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <div>Total alerts: {score.total_alerts ?? "-"}</div>
            <div>Windows: {score.total_windows}</div>
            <div>Worst window: {score.max} alerts</div>
          </div>
        </div>
        <div className="mt-3 h-2 rounded-full bg-muted" title="Alert level (lower is better)">
          <div
            className={`h-2 rounded-full ${gradeColor[score.grade] ?? "bg-muted-foreground"}`}
            style={{ width: `${Math.max(alertLevel, 3)}%` }}
          />
        </div>
      </div>
    );
  };

  const renderScoreCard = (data) => {
    if (data.score === null || data.score === undefined) return null;
    return (
      <div className="rounded-2xl border border-border/60 bg-card/60 p-4">
        <div className="text-sm text-muted-foreground mb-2">Interview score</div>
        <div className="text-3xl font-bold">
          {data.score}
          <span className="text-base font-normal text-muted-foreground"> / 100</span>
        </div>
        <div className="text-sm text-muted-foreground capitalize">{data.performance}</div>
        {data.details?.length > 0 && (
          <div className="mt-3 space-y-2">
            {data.details.map((d, i) => (
              <div key={i} className="text-xs border rounded-xl p-2 bg-background/50">
                <div className="flex justify-between font-medium">
                  <span className="capitalize">
                    Q{i + 1} - {d.category}, {d.difficulty}
                  </span>
                  <span>{d.score} / 10</span>
                </div>
                {d.reasonings?.[0] && (
                  <div className="text-muted-foreground mt-1">{d.reasonings[0]}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderReport = () => {
    if (reportLoading) {
      return (
        <div className="flex items-center justify-center py-10 text-muted-foreground">
          <Loader2 className="animate-spin mr-2" />
          Fetching interview report...
        </div>
      );
    }

    // Never shortlisted for an interview: nothing to show.
    if (reportData?.report_status === "no_interview") return null;

    if (reportError || !reportData) {
      return (
        <div className="text-red-500 text-sm">
          Failed to load interview report. Try again later.
        </div>
      );
    }

    // FIX: the backend now says which state the report is in instead of
    // returning a 404 error while it is still being written.
    if (reportData.report_status === "pending") {
      const done = reportData.status === "completed";
      return (
        <div className="rounded-2xl border border-border/60 p-4 text-sm text-muted-foreground flex items-center">
          {done && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
          {done
            ? "Interview finished. The report is being written..."
            : "The candidate has not completed the interview yet."}
        </div>
      );
    }

    const { report, integrity_score, integrity_report } = reportData;

    return (
      <div className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur p-4 space-y-4 mt-6">
        {renderScoreCard(reportData)}

        <div>
          <div className="text-sm text-muted-foreground mb-2">
            AI Interview Evaluation
          </div>
          {reportData.report_status === "failed" ? (
            <div className="text-sm text-red-500">
              The written report could not be generated: {reportData.error}
            </div>
          ) : (
            <ReportText text={report} />
          )}
        </div>

        {renderIntegrityCard(integrity_score)}

        {integrity_report?.windows?.length > 0 && (
          <div>
            <div className="text-sm text-muted-foreground mb-2">
              Alert Timeline
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {integrity_report.windows.map((win) => (
                <div
                  key={win.window_number}
                  className="border rounded-xl p-2 text-xs bg-background/50"
                >
                  <div className="flex justify-between text-muted-foreground font-medium">
                    <span>Window #{win.window_number}</span>
                    <span>{win.alert_count} alerts</span>
                  </div>
                  <div className="mt-1 space-y-1">
                    {win.alerts?.map((a, i) => (
                      <div key={i} className="text-muted-foreground">
                        • {a.type.replaceAll("_", " ")} (
                        {new Date(a.timestamp).toLocaleTimeString()})
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl lg:max-w-3xl p-0"
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <div className="h-full grid grid-rows-[auto_1fr]">
          {/* Header */}
          <SheetHeader className="px-4 lg:px-6 py-4 border-b border-border/60">
            <SheetTitle className="flex items-center justify-between">
              <span className="text-pretty">{candidate?.name}</span>
              <Badge className="rounded-full" variant="secondary">
                {selectedStage || "Applied"}
              </Badge>
            </SheetTitle>
          </SheetHeader>

          {/* Body */}
          <div className="grid lg:grid-cols-2 gap-4 p-4 lg:p-6 overflow-auto">
            {/* Left column */}
            <div className="flex flex-col gap-4">
              {/* Contact */}
              <div className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur p-4">
                <div className="text-sm text-muted-foreground">Contact</div>
                <div className="mt-2 text-sm">{candidate?.email}</div>
              </div>

              {/* Role & Stage */}
              <div className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur p-4">
                <div className="text-sm text-muted-foreground mb-2">
                  Role & Stage
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Applied for</Label>
                    <Input
                      value={job?.title ?? ""}
                      readOnly
                      className="rounded-xl mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Stage</Label>
                    <Select
                      value={selectedStage}
                      onValueChange={handleStageChange}
                      disabled={isPending}
                    >
                      <SelectTrigger className="rounded-xl mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="applied">Applied</SelectItem>
                        <SelectItem value="reviewed">Screening</SelectItem>
                        <SelectItem value="interview">Interview</SelectItem>
                        <SelectItem value="offer">Offer</SelectItem>
                        <SelectItem value="rejected">Rejected</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {hasChanges && (
                  <div className="flex justify-end mt-4">
                    <Button
                      onClick={handleSave}
                      disabled={isPending}
                      className="rounded-xl"
                    >
                      {isPending ? "Saving..." : "Save Changes"}
                    </Button>
                  </div>
                )}
              </div>

              {/* Applied On */}
              <div className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur p-4">
                <div className="text-sm text-muted-foreground mb-2">
                  Applied On
                </div>
                <div className="text-sm">
                  {application?.applied_at
                    ? new Date(application.applied_at).toLocaleString()
                    : "N/A"}
                </div>
              </div>

              {/* ✅ Report shown only if in INTERVIEW stage */}
              {renderReport()}
            </div>

            {/* Right column */}
            <div className="flex flex-col gap-4">
              {/* AI Match Score */}
              <div className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur p-4">
                <div className="text-sm text-muted-foreground mb-2">
                  AI Match Score
                </div>
                {application?.match_score !== null &&
                application?.match_score !== undefined ? (
                  <>
                    <div className="text-3xl font-semibold leading-none">
                      {Math.round(application.match_score)}%
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-muted">
                      <div
                        className="h-2 rounded-full bg-primary"
                        style={{ width: `${application.match_score}%` }}
                        aria-label="Match score progress"
                      />
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-muted-foreground">
                    Score is being calculated...
                  </div>
                )}
              </div>

              {/* Resume Preview */}
              <ResumePreview url={application?.resume_url} />
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
