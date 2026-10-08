import { API_URL as BASE_URL } from "./config";

async function getErrorMessage(res, fallback) {
  try {
    const error = await res.json();
    const { detail } = error;

    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((issue) => issue?.msg)
        .filter(Boolean)
        .join(" ") || fallback;
    }
  } catch {
    // Use the request-specific fallback when the response has no JSON body.
  }

  return fallback;
}

export async function loginApi(data) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(await getErrorMessage(res, "Login failed"));
  }

  return res.json();
}

export async function signupApi(data) {
  const res = await fetch(`${BASE_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(await getErrorMessage(res, "Signup failed"));
  }

  return res.json();
}
