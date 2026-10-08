import { useState } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { JobCard } from "@/components/candidate/job-card";
import { StatsCards } from "@/components/candidate/stats-cards";
import { ApplicationsTable } from "@/components/candidate/applications-table";
import { ResultsList } from "@/components/candidate/results-list";
import LogoPNG from "@/assets/logo.png";
import { useJobs } from "@/hooks/useJobs";
import { JobCardSkeleton } from "../skeletons/JobCardSkeleton";
import { ApplicationsSkeleton } from "@/components/skeletons/ApplicationsSkeleton";
import { useAuthStore } from "@/store/useAuthStore";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApplyToJob } from "@/hooks/applicationHooks";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/spinner";
import { useApplications } from "@/hooks/applicationHooks";

export default function CandidateDashboardPage() {
  const navigate = useNavigate();
  const { data: jobs = [], isLoading } = useJobs();
  const { data: applications = [], isLoading: isLoadingApplications } =
    useApplications();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [tab, setTab] = useState("browse");

  // FIX: these were hard-coded (128 jobs, 12 applications, 3 interviews).
  const upcoming = applications.filter(
    (a) => a.interview && ["scheduled", "in_progress"].includes(a.interview.status)
  );
  const stats = [
    { label: "Open Jobs", value: isLoading ? "…" : jobs.length, hint: "Jobs you haven't applied to" },
    { label: "Applications", value: isLoadingApplications ? "…" : applications.length, hint: "All time" },
    { label: "Interviews", value: isLoadingApplications ? "…" : upcoming.length, hint: "Waiting for you" },
  ];

  // FIX: the Results tab was always given an empty list.
  const results = applications
    .filter((a) => a.interview?.status === "completed")
    .map((a) => ({
      id: a.id,
      title: a.title,
      company: a.company,
      score: a.interview.score,
      outcome:
        a.status === "Offer" ? "Accepted" : a.status === "Rejected" ? "Rejected" : "Under review",
    }));

  const [selectedJob, setSelectedJob] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);

  const { mutateAsync: applyToJob, isPending: isApplying } = useApplyToJob();

  const handleApply = (job) => setSelectedJob(job);

  const handleSubmitApplication = async () => {
    if (!resumeFile) {
      toast.error("Please upload a resume before applying!");
      return;
    }

    try {
      await applyToJob({ job_id: selectedJob.id, file: resumeFile });
      setSelectedJob(null);
      setResumeFile(null);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <main className="min-h-[calc(100vh-0px)] bg-background">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 md:py-10">
        {/* Header */}
        <header className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-5 w-5" />
            </Button>

            <img
              src={LogoPNG}
              alt="IntelliHire"
              width={32}
              height={32}
              className="rounded-md border border-border"
            />
            <div>
              <h1 className="text-xl md:text-2xl font-semibold text-foreground">
                {`Welcome ${user?.name ?? ""}!`}
              </h1>
              <p className="text-sm text-muted-foreground">
                Track jobs, applications, and results in one place.
              </p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2">
            {/* FIX: both buttons linked to the login page */}
            <Button variant="outline" onClick={() => setTab("profile")}>
              Account
            </Button>
            <Button onClick={() => setTab("browse")}>Find Jobs</Button>
          </div>
        </header>

        <Separator className="my-6" />
        <StatsCards stats={stats} className="mb-6" />

        {/* Tabs */}
        <Tabs value={tab} onValueChange={setTab} className="mt-2">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="browse">Browse Jobs</TabsTrigger>
            <TabsTrigger value="applications">My Applications</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
            <TabsTrigger value="profile">Profile</TabsTrigger>
          </TabsList>

          <TabsContent value="browse" className="space-y-4">
            {!isLoading && jobs.length === 0 && (
              <div className="rounded-xl border border-border p-8 text-center text-muted-foreground">
                No new jobs right now. You've applied to everything open.
              </div>
            )}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {isLoading
                ? Array.from({ length: 4 }).map((_, i) => (
                    <JobCardSkeleton key={i} />
                  ))
                : jobs.map((job) => (
                    <JobCard
                      key={job.id}
                      job={job}
                      onApply={() => handleApply(job)}
                    />
                  ))}
            </div>
          </TabsContent>

          <TabsContent value="applications" className="space-y-4">
            {isLoadingApplications ? (
              <ApplicationsSkeleton />
            ) : (
              <ApplicationsTable items={applications} />
            )}
          </TabsContent>

          <TabsContent value="results" className="space-y-4">
            <ResultsList items={results} />
          </TabsContent>

          <TabsContent value="profile" className="space-y-4">
            {/* FIX: "Edit Profile" and "Upload Resume" did nothing. The tab now
                shows the account and a working Log out. */}
            <div className="rounded-xl border border-border bg-card/70 backdrop-blur p-5">
              <h3 className="text-lg md:text-xl font-semibold text-foreground">
                Profile
              </h3>
              <dl className="mt-3 grid gap-2 text-sm">
                <div className="flex gap-2">
                  <dt className="text-muted-foreground w-16">Name</dt>
                  <dd className="text-foreground">{user?.name}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="text-muted-foreground w-16">Email</dt>
                  <dd className="text-foreground">{user?.email}</dd>
                </div>
              </dl>
              <p className="mt-3 text-sm text-muted-foreground">
                You upload a resume with each application, so it can be tailored to the job.
              </p>
              <div className="mt-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    logout();
                    navigate("/auth");
                  }}
                >
                  Log out
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Job Details Modal */}
      <Dialog open={!!selectedJob} onOpenChange={() => setSelectedJob(null)}>
        <DialogContent className="max-w-lg">
          {selectedJob && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedJob.title}</DialogTitle>
                <DialogDescription>
                  {selectedJob.location} • {selectedJob.type}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3 mt-4">
                <div className="max-h-96 overflow-y-auto rounded-md border p-3 bg-muted/10">
                  <p className="text-sm text-muted-foreground whitespace-pre-line">
                    {selectedJob.description}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2 mt-3">
                  {selectedJob.tags?.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>

                <div className="mt-4 space-y-2">
                  <Label htmlFor="resume">Upload Resume</Label>
                  <Input
                    id="resume"
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>

              <DialogFooter className="mt-6 flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setSelectedJob(null)}
                  disabled={isApplying}
                >
                  Cancel
                </Button>
                <Button onClick={handleSubmitApplication} disabled={isApplying}>
                  {isApplying && <Spinner />}
                  Apply
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </main>
  );
}
