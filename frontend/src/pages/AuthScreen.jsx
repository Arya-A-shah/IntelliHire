import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { RoleToggle } from "@/components/auth/role-toggle";
import { Mail, Lock, User, Building2 } from "lucide-react";
import LogoPNG from "@/assets/logo.png";
import { toast } from "sonner";
import { useLogin, useSignup } from "@/hooks/useAuth";

export default function AuthScreen() {
  const [role, setRole] = useState("candidate");
  const [tab, setTab] = useState("login");

  const navigate = useNavigate();
  // After login, go back to the page that sent us here (e.g. the interview
  // link from the email) instead of always going to the dashboard.
  const location = useLocation();

  // Controlled form state
  const [loginData, setLoginData] = useState({ email: "", password: "" });
  const [signupData, setSignupData] = useState({
    name: "",
    email: "",
    password: "",
    confirm: "",
    org: "",
  });

  const { login, isLoading: isLoggingIn } = useLogin();
  const { signup, isLoading: isSigningUp } = useSignup();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      await login({ ...loginData, role });
      toast.success("Logged in successfully!");
      navigate(location.state?.from || "/dashboard");
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    const { name, email, password, confirm, org } = signupData;

    if (password !== confirm) {
      toast.error("Passwords do not match");
      return;
    }

    try {
      await signup({ name, email, password, role, org });
      toast.success("Account created successfully!");
      setTab("login");
    } catch (err) {
      toast.error(err.message);
    }
  };

  const subtitle = useMemo(() => {
    if (tab === "login") {
      return role === "candidate"
        ? "Sign in to continue your AI-powered interviews."
        : "Sign in to manage candidates and interviews.";
    }
    return role === "candidate"
      ? "Create your account to practice and ace interviews."
      : "Create your recruiter account to streamline hiring.";
  }, [role, tab]);

  return (
    <main className="min-h-dvh w-full bg-background">
      <div className="mx-auto flex min-h-dvh max-w-7xl items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Back Button */}
          <Button
            variant="ghost"
            asChild
            className="mb-6 text- hover:text-foreground transition-colors text-balance"
          >
            <Link to="/" className="inline-flex items-center gap-2">
              ← Back to Home
            </Link>
          </Button>

          {/* Header */}
          <header className="mb-6 flex flex-col items-center text-center">
            <div className="mb-2 flex items-center gap-2">
              <img
                src={LogoPNG}
                alt="IntelliHire Logo"
                className="h-7 w-7 rounded-md"
              />
              <span className="text-lg font-medium tracking-tight">
                IntelliHire
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Your AI Interview Partner
            </p>
          </header>

          {/* Glass Card */}
          <Card className="rounded-2xl border border-border/50 bg-card/70 shadow-xl backdrop-blur-xl ring-1 ring-ring/20">
            <CardHeader className="space-y-4">
              <RoleToggle role={role} onChange={setRole} />
              <div className="flex flex-col gap-1">
                <h1 className="text-balance text-center text-xl font-semibold">
                  {tab === "login" ? "Welcome back" : "Create your account"}
                </h1>
                <p className="text-center text-sm text-muted-foreground">
                  {subtitle}
                </p>
              </div>

              <Tabs
                value={tab}
                onValueChange={(v) => setTab(v)}
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="login" className="cursor-pointer">
                    Log in
                  </TabsTrigger>
                  <TabsTrigger value="signup" className="cursor-pointer">
                    Sign up
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* LOGIN */}
              {tab === "login" && (
                <form className="space-y-4" onSubmit={handleLogin}>
                  <div className="space-y-2">
                    <Label htmlFor="login-email">Email</Label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="login-email"
                        type="email"
                        autoComplete="email"
                        placeholder="you@example.com"
                        className="pl-9"
                        required
                        value={loginData.email}
                        onChange={(e) =>
                          setLoginData({ ...loginData, email: e.target.value })
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="login-password">Password</Label>
                      <Link
                        to="#"
                        className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                      >
                        Forgot password?
                      </Link>
                    </div>
                    <div className="relative">
                      <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="login-password"
                        type="password"
                        className="pl-9"
                        required
                        value={loginData.password}
                        onChange={(e) =>
                          setLoginData({
                            ...loginData,
                            password: e.target.value,
                          })
                        }
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={isLoggingIn}
                    className="w-full transition-all hover:scale-[1.01] disabled:opacity-70"
                  >
                    {isLoggingIn && <Spinner />}
                    Log In
                  </Button>
                </form>
              )}

              {/* SIGNUP */}
              {tab === "signup" && (
                <form className="space-y-4" onSubmit={handleSignup}>
                  <div className="space-y-2">
                    <Label htmlFor="signup-name">Name</Label>
                    <div className="relative">
                      <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="signup-name"
                        type="text"
                        placeholder="Your name"
                        className="pl-9"
                        required
                        value={signupData.name}
                        onChange={(e) =>
                          setSignupData({ ...signupData, name: e.target.value })
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="signup-email">Email</Label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="signup-email"
                        type="email"
                        placeholder="you@example.com"
                        className="pl-9"
                        required
                        value={signupData.email}
                        onChange={(e) =>
                          setSignupData({
                            ...signupData,
                            email: e.target.value,
                          })
                        }
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="signup-password">Password</Label>
                      <div className="relative">
                        <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          id="signup-password"
                          type="password"
                          className="pl-9"
                          required
                          value={signupData.password}
                          onChange={(e) =>
                            setSignupData({
                              ...signupData,
                              password: e.target.value,
                            })
                          }
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="signup-confirm">Confirm password</Label>
                      <div className="relative">
                        <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          id="signup-confirm"
                          type="password"
                          className="pl-9"
                          required
                          value={signupData.confirm}
                          onChange={(e) =>
                            setSignupData({
                              ...signupData,
                              confirm: e.target.value,
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>

                  {role === "recruiter" && (
                    <div className="space-y-2 animate-fade-in">
                      <Label htmlFor="signup-org">
                        Organization (optional)
                      </Label>
                      <div className="relative">
                        <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          id="signup-org"
                          type="text"
                          placeholder="Company or team"
                          className="pl-9"
                          value={signupData.org}
                          onChange={(e) =>
                            setSignupData({
                              ...signupData,
                              org: e.target.value,
                            })
                          }
                        />
                      </div>
                    </div>
                  )}

                  <Button
                    type="submit"
                    disabled={isSigningUp}
                    className="w-full transition-all hover:scale-[1.01] disabled:opacity-70"
                  >
                    {isSigningUp && <Spinner />}
                    Create Account
                  </Button>
                </form>
              )}

              {/* CTA footer */}
              <div className="pt-2 text-center text-sm text-muted-foreground">
                {tab === "login" ? (
                  <span>
                    New to IntelliHire?{" "}
                    <button
                      type="button"
                      className="font-medium text-foreground underline-offset-4 hover:underline"
                      onClick={() => setTab("signup")}
                    >
                      Create an account
                    </button>
                    .
                  </span>
                ) : (
                  <span>
                    Already have an account?{" "}
                    <button
                      type="button"
                      className="font-medium text-foreground underline-offset-4 hover:underline"
                      onClick={() => setTab("login")}
                    >
                      Log in
                    </button>
                    .
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
