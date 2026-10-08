import { useQuery } from "@tanstack/react-query";
import { fetchJobs, fetchRecruiterJobs, fetchRecruiterStats } from "@/lib/api/jobs";

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
  });
}

export function useRecruiterJobs() {
  return useQuery({
    queryKey: ["recruiter-jobs"],
    queryFn: fetchRecruiterJobs,
    // FIX: TanStack Query v5 removed onError from useQuery, so this toast
    // never fired (and `toast` was not even imported). App.jsx now shows
    // a toast for any failed query that sets meta.errorMessage.
    meta: { errorMessage: "Failed to load jobs" },
  });
}

export function useRecruiterStats() {
  return useQuery({
    queryKey: ["recruiterStats"],
    queryFn: fetchRecruiterStats,
    meta: { errorMessage: "Failed to load stats" },
  });
}
