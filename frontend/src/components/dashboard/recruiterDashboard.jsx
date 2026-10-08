import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { RecruiterSidebar } from "@/components/recruiter/sidebar";
import { StatsCards } from "@/components/recruiter/stats-cards";
import { PipelineChart } from "@/components/recruiter/pipeline-chart";
import { JobPostingsTable } from "@/components/recruiter/job-postings-table";
import { CandidateTable } from "@/components/recruiter/candidate-table";
import { PostJobDialog } from "@/components/recruiter/post-job-dialog";
import { useNavigate } from "react-router";
import { ArrowLeft } from "lucide-react";
import { InterviewsTable } from "@/components/recruiter/interviews-table";
import { useRecruiterStats } from "@/hooks/useJobs";
import { useRecruiterApplications } from "@/hooks/applicationHooks";
import { candidateCsvColumns, downloadCsv } from "@/lib/csv";
import { toast } from "sonner";

export default function Page() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("overview");
  const [openPost, setOpenPost] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [editingJob, setEditingJob] = useState(null); // job being edited, or null

  const { data: stats, isLoading: statsLoading } = useRecruiterStats();
  const { data: allApplications = [] } = useRecruiterApplications();

  // FIX: "Import Candidates" had no onClick and there is no import feature
  // in the backend, so it is replaced by a working "Export Candidates".
  const exportAll = () => {
    if (allApplications.length === 0) {
      toast.info("No candidates to export yet");
      return;
    }
    const date = new Date().toISOString().slice(0, 10);
    downloadCsv(`all-candidates-${date}.csv`, candidateCsvColumns, allApplications);
  };

  const handleViewCandidates = (job) => {
    setSelectedJobId(job.id);
    setTab("candidates");
  };

  return (
    <main className="min-h-[100dvh]">
      <div className="container mx-auto px-4 py-6 lg:py-8">
        <header className="mb-4 lg:mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              className="rounded-full"
              onClick={() => navigate(-1)}
              aria-label="Go back"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>

            <div>
              <h1 className="text-balance text-2xl lg:text-3xl font-semibold">
                Recruiter Dashboard
              </h1>
              <p className="text-muted-foreground mt-1 text-sm lg:text-base">
                Manage roles, review candidates, and streamline your hiring
                pipeline.
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <Button variant="secondary" className="rounded-xl" onClick={exportAll}>
              Export Candidates
            </Button>
            <Button className="rounded-xl" onClick={() => setOpenPost(true)}>
              Post Job
            </Button>
          </div>
        </header>

        <div className="grid gap-4 lg:gap-6 lg:grid-cols-[260px_1fr]">
          <RecruiterSidebar
            active={tab}
            onChange={(k) => {
              setTab(k);
              // Reset job filter when changing tabs
              if (k !== "candidates") {
                setSelectedJobId(null);
              }
            }}
            className="hidden lg:block"
          />

          <Card className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/50 p-3 lg:p-5">
            <Tabs
              value={tab}
              onValueChange={(v) => {
                setTab(v);
                // Reset job filter when changing tabs
                if (v !== "candidates") {
                  setSelectedJobId(null);
                }
              }}
              className="w-full"
            >
              <div className="flex items-center justify-between gap-2">
                <TabsList className="rounded-xl">
                  <TabsTrigger value="overview" className="rounded-lg">
                    Overview
                  </TabsTrigger>
                  <TabsTrigger value="jobs" className="rounded-lg">
                    Jobs
                  </TabsTrigger>
                  <TabsTrigger value="candidates" className="rounded-lg">
                    Candidates
                  </TabsTrigger>
                  <TabsTrigger value="interviews" className="rounded-lg">
                    Interviews
                  </TabsTrigger>
                </TabsList>
                <div className="lg:hidden">
                  <Button
                    size="sm"
                    variant="secondary"
                    className="rounded-lg"
                    onClick={() => setOpenPost(true)}
                  >
                    Post Job
                  </Button>
                </div>
              </div>

              <TabsContent
                value="overview"
                className="mt-4 focus-visible:outline-none"
              >
                <div className="flex flex-col gap-4">
                  <StatsCards data={stats} isLoading={statsLoading} />
                  <PipelineChart data={stats?.pipeline} />
                </div>
              </TabsContent>

              <TabsContent
                value="jobs"
                className="mt-4 focus-visible:outline-none"
              >
                <JobPostingsTable
                  onViewCandidates={handleViewCandidates}
                  onPostJob={() => setOpenPost(true)}
                  onEditJob={(job) => {
                    setEditingJob(job);
                    setOpenPost(true);
                  }}
                />
              </TabsContent>

              <TabsContent
                value="candidates"
                className="mt-4 focus-visible:outline-none"
              >
                <CandidateTable
                  jobId={selectedJobId}
                  onClearFilter={() => setSelectedJobId(null)}
                />
              </TabsContent>

              <TabsContent
                value="interviews"
                className="mt-4 focus-visible:outline-none"
              >
                {/* FIX: was a hard-coded "No interviews scheduled" message */}
                <InterviewsTable />
              </TabsContent>
            </Tabs>
          </Card>
        </div>
      </div>
      <PostJobDialog
        open={openPost}
        setOpen={(open) => {
          setOpenPost(open);
          if (!open) setEditingJob(null);
        }}
        job={editingJob}
        onCreated={() => {
          setTab("jobs");
        }}
      />
    </main>
  );
}
