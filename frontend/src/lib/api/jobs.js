import { API_URL as BASE_URL } from "./config";

export async function fetchJobs() {
  const token = localStorage.getItem("token");

  const res = await fetch(`${BASE_URL}/jobs`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch jobs");
  }

  return res.json();
}

export async function createJobApi(data) {
  const token = localStorage.getItem("token");

  const res = await fetch(`${BASE_URL}/jobs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to create job");
  }

  return res.json();
}

export async function fetchRecruiterJobs() {
  const token = localStorage.getItem("token");

  const res = await fetch(`${BASE_URL}/jobs/my`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch recruiter jobs");
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

// Real numbers for the recruiter Overview tab
export function fetchRecruiterStats() {
  return getJson(`${BASE_URL}/jobs/stats`, "Failed to fetch stats");
}

export async function updateJobApi({ id, ...data }) {
  const res = await fetch(`${BASE_URL}/jobs/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update job");
  }
  return res.json();
}
