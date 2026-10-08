import { useQuery } from "@tanstack/react-query";
import { fetchMyInterviews, getInterviewReport } from "@/lib/api/interviews";

export function useInterviewReport(applicationId) {
  return useQuery({
    queryKey: ["interviewReport", applicationId],
    queryFn: () => getInterviewReport(applicationId),
    enabled: !!applicationId, // only run if id exists
    // FIX: the report is written in the background after the interview, so
    // the first fetch often comes too early. Old code cached that empty
    // answer for 5 minutes. Now: ask again every 5 s while it's "pending",
    // stop as soon as it's ready or failed.
    refetchInterval: (query) =>
      query.state.data?.report_status === "pending" &&
      query.state.data?.status === "completed"
        ? 5000
        : false,
    meta: { errorMessage: "Failed to load interview report" },
  });
}

export function useMyInterviews() {
  return useQuery({
    queryKey: ["myInterviews"],
    queryFn: fetchMyInterviews,
    meta: { errorMessage: "Failed to load interviews" },
  });
}
