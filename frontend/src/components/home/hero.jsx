import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router";
import LogoPNG from "@/assets/logo.png";
import { ThemeToggle } from "../theme/ThemeToggle";
import { useAuthStore } from "@/store/useAuthStore";

export function Hero() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const isLoggedIn = !!token;

  return (
    <header className="relative">
      {/* Navbar */}
      <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 md:py-5">
        <div className="flex items-center gap-2">
          <img
            src={LogoPNG}
            alt="IntelliHire logo"
            width={28}
            height={28}
            className="rounded-sm"
          />
          <span className="text-base font-medium tracking-tight">
            IntelliHire
          </span>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />

          {isLoggedIn ? (
            <>
              <Button
                variant="secondary"
                className="transition-all"
                onClick={() => navigate("dashboard")}
              >
                Dashboard
              </Button>
              <Button
                variant="ghost"
                className="transition-all"
                onClick={() => {
                  useAuthStore.getState().logout();
                  navigate("/");
                }}
              >
                Logout
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="ghost"
                className="transition-all"
                onClick={() => navigate("/auth")}
              >
                Sign in
              </Button>
              <Button
                className="transition-all"
                onClick={() => navigate("/auth")}
              >
                Get started
              </Button>
            </>
          )}
        </div>
      </nav>

      {/* Hero content */}
      <main className="mx-auto grid max-w-6xl place-items-center px-4 pb-16 pt-8 md:pt-16">
        <div className="ih-fade-up text-center">
          <span className="inline-flex items-center rounded-full border border-border/50 bg-card/60 px-3 py-1 text-xs text-muted-foreground backdrop-blur-md">
            Your AI Interview Partner
          </span>

          <h1 className="mt-4 text-balance text-4xl font-semibold leading-tight md:text-6xl">
            Interview smarter.{" "}
            <span className="text-[color:var(--color-intelli-indigo)]">
              Hire faster.
            </span>
          </h1>

          <p className="mx-auto mt-3 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground md:mt-4 md:text-lg">
            IntelliHire streamlines candidate screening with AI-driven insights,
            structured interviews, and fair, consistent evaluations.
          </p>

          <div className="mt-6 flex items-center justify-center gap-2">
            {isLoggedIn ? (
              <Button
                className="rounded-xl transition-transform hover:scale-[1.02]"
                onClick={() => navigate("/dashboard")}
              >
                Go to Dashboard
              </Button>
            ) : (
              <Button
                className="rounded-xl transition-transform hover:scale-[1.02]"
                onClick={() => navigate("/auth")}
              >
                Start free
              </Button>
            )}

            <Link to="#features">
              <Button variant="secondary" className="rounded-xl">
                Learn more
              </Button>
            </Link>
          </div>
        </div>

        {/* Glass hero card */}
        <div className="ih-fade-up mt-8 w-full max-w-4xl rounded-2xl border border-border/40 bg-card/60 p-4 shadow-lg backdrop-blur-xl md:p-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-border/40 bg-background/40 p-4">
              <p className="text-base font-medium">AI-structured interviews</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Consistent question sets and scoring rubrics.
              </p>
            </div>
            <div className="rounded-xl border border-border/40 bg-background/40 p-4">
              <p className="text-base font-medium">Real-time insights</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Highlight strengths, risks, and follow-ups.
              </p>
            </div>
            <div className="rounded-xl border border-border/40 bg-background/40 p-4">
              <p className="text-base font-medium">Fair, unbiased reviews</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Calibrated, transparent evaluations at scale.
              </p>
            </div>
          </div>
        </div>
      </main>
    </header>
  );
}
