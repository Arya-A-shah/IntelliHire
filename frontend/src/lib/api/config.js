// FIX: one place for the backend address. Several files hard-coded
// "http://localhost:8000", so deploying meant hunting them all down.
// Set VITE_API_URL in frontend/.env to point somewhere else.
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
