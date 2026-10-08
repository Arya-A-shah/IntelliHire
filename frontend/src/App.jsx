import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { BrowserRouter, Routes, Route } from "react-router";
import NotFound from "./pages/NotFound";
import HomeScreen from "./pages/HomeScreen";
import AuthScreen from "./pages/AuthScreen";
import { useThemeStore } from "./store/useThemeStore";
import { useEffect } from "react";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import DashboardScreen from "./pages/DashboardScreen";
import InterviewScreen from "./pages/InterviewScreen";

// FIX: TanStack Query v5 removed `onError` from useQuery. One global handler
// shows a toast for any failed query that sets `meta.errorMessage`.
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.meta?.errorMessage) {
        toast.error(`${query.meta.errorMessage}: ${error.message}`);
      }
    },
  }),
});

const App = () => {
  const { theme, setTheme } = useThemeStore();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    setTheme(theme);
  }, [theme, setTheme]);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomeScreen />} />
            <Route path="/auth" element={<AuthScreen />} />
            {/* FIX: the interview page was outside ProtectedRoute, so a
                logged-out visitor landed on a page that could never work. */}
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardScreen />} />
              <Route
                path="/interview/:interviewId"
                element={<InterviewScreen />}
              />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};

export default App;
