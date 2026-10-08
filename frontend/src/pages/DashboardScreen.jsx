import { useMemo } from "react";
import { useAuthStore } from "@/store/useAuthStore";
import CandidateDashboard from "@/components/dashboard/candidateDashboard";
import RecruiterDashboard from "@/components/dashboard/recruiterDashboard";

export default function DashboardScreen() {
  const { user } = useAuthStore();

  const DashboardComponent = useMemo(() => {
    if (!user) return null;

    switch (user.role) {
      case "candidate":
        return <CandidateDashboard />;
      case "recruiter":
        return <RecruiterDashboard />;
      default:
        return <div>Unknown role</div>;
    }
  }, [user]);

  return (
    <div className="min-h-screen w-full">
      {DashboardComponent ? DashboardComponent : <div>Loading...</div>}
    </div>
  );
}
