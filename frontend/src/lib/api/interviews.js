import { useAuthStore } from "@/store/useAuthStore";

import { API_URL as BASE_URL } from "./config";

export async function getInterviewReport(applicationId) {
  if (!applicationId) throw new Error("Application ID is required");

  const token = useAuthStore.getState().token;

  const res = await fetch(`${BASE_URL}/interviews/report/${applicationId}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch report: ${res.status} - ${text}`);
  }

  return res.json();
}

// Every interview for the logged-in recruiter (Interviews tab)
export async function fetchMyInterviews() {
  const token = useAuthStore.getState().token;
  const res = await fetch(`${BASE_URL}/interviews/my`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Failed to fetch interviews: ${res.status}`);
  return res.json();
}
