import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import {
  applyToJobApi,
  fetchApplications,
  fetchRankedApplications,
  fetchRecruiterApplications,
  updateApplicationStatusApi,
} from "@/lib/api/applications";
import { toast } from "sonner";

export function useApplyToJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ["applyToJob"], // unique key
    mutationFn: ({ job_id, file }) => applyToJobApi({ job_id, file }),
    onSuccess: () => {
      toast.success("Application submitted successfully!");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => {
      toast.error(`Failed to apply: ${err.message}`);
    },
  });
}

export function useApplications() {
  return useQuery({
    queryKey: ["applications"],
    queryFn: fetchApplications,
    // FIX: onError on useQuery was removed in v5 (see App.jsx QueryCache)
    meta: { errorMessage: "Failed to load applications" },
  });
}
export function useRankedApplications(jobId) {
  return useQuery({
    queryKey: ["rankedApplications", jobId],
    queryFn: () => fetchRankedApplications(jobId),
    enabled: !!jobId, // only fetch when jobId is provided
    meta: { errorMessage: "Failed to load ranked candidates" },
  });
}

export function useUpdateApplicationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateApplicationStatusApi,
    onSuccess: () => {
      // Everything that shows an application's stage must refresh
      queryClient.invalidateQueries({ queryKey: ["rankedApplications"] });
      queryClient.invalidateQueries({ queryKey: ["recruiterApplications"] });
      queryClient.invalidateQueries({ queryKey: ["recruiterStats"] });
      queryClient.invalidateQueries({ queryKey: ["myInterviews"] });
    },
  });
}

// FIX: the Candidates tab used only the per-job query, which is disabled when
// no job is selected, so opening the tab directly showed an empty table.
export function useRecruiterApplications({ enabled = true } = {}) {
  return useQuery({
    queryKey: ["recruiterApplications"],
    queryFn: fetchRecruiterApplications,
    enabled,
    meta: { errorMessage: "Failed to load candidates" },
  });
}
