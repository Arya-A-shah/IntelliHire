import { API_URL as BASE_URL } from "./config";

export async function applyToJobApi({ job_id, file }) {
  if (!file || !(file instanceof File)) {
    throw new Error("Invalid file provided");
  }

  const token = localStorage.getItem("token");

  const formData = new FormData();
  formData.append("job_id", job_id);
  formData.append("resume", file);

  const res = await fetch(`${BASE_URL}/applications`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to apply");
  }

  return res.json();
}

export async function fetchApplications() {
  const token = localStorage.getItem("token");

  const res = await fetch(`${BASE_URL}/applications`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch applications");
  }

  return res.json();
}

export async function fetchRankedApplications(jobId) {
  const token = localStorage.getItem("token");

  const res = await fetch(`${BASE_URL}/jobs/${jobId}/ranked`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch ranked applications");
  }

  return res.json();
}

export async function updateApplicationStatusApi({ applicationId, status }) {
  const token = localStorage.getItem("token");

  const res = await fetch(`${BASE_URL}/applications/${applicationId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ status }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update application status");
  }

  return res.json();
}

function authHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function getJson(url, fallback) {
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || fallback);
  }
  return res.json();
}

// All applications across the recruiter's jobs (Candidates tab without a job filter)
export function fetchRecruiterApplications() {
  return getJson(`${BASE_URL}/applications/recruiter`, "Failed to fetch candidates");
}
