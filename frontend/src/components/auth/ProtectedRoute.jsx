import { Navigate, Outlet, useLocation } from "react-router";
import { useAuthStore } from "@/store/useAuthStore";

export default function ProtectedRoute() {
  const token = useAuthStore((s) => s.token);
  const location = useLocation();
  if (!token) {
    // Remember where the user was going, so login can send them back there.
    return <Navigate to="/auth" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
