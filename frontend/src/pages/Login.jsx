import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { formatApiError } from "@/lib/api";
import { GoogleLogoIcon, ArrowRightIcon } from "@phosphor-icons/react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const u = await login(email.trim(), password);
      toast.success("Welcome back!");
      navigate(u.onboarded ? "/dashboard" : "/onboarding");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const handleGoogle = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex bg-sand-100">
      <div className="flex-1 grid place-items-center px-6 py-16">
        <div className="w-full max-w-md">
          <Link to="/" className="inline-flex items-center gap-2 mb-12" data-testid="login-back-home-link">
            <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white font-display font-bold">B</div>
            <div className="font-display font-bold text-olive-900">BIR Filipino</div>
          </Link>
          <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Welcome back</div>
          <h1 className="font-display font-bold text-olive-900 text-4xl tracking-tight leading-tight mb-2">Log in</h1>
          <p className="text-sand-700 mb-10">Continue where your last filing left off.</p>

          <Button
            type="button"
            onClick={handleGoogle}
            variant="outline"
            data-testid="login-google-button"
            className="w-full bg-white border-sand-300 text-olive-900 hover:bg-sand-200 py-6 mb-6"
          >
            <GoogleLogoIcon size={20} weight="bold" /> Continue with Google
          </Button>

          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-px bg-sand-300" />
            <div className="text-xs tracking-widest uppercase text-sand-600 font-semibold">or with email</div>
            <div className="flex-1 h-px bg-sand-300" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="email" className="text-olive-900 font-semibold">Email</Label>
              <Input
                id="email" type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="login-email-input"
                className="mt-2 bg-white border-sand-300 py-6"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <Label htmlFor="password" className="text-olive-900 font-semibold">Password</Label>
              <Input
                id="password" type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="login-password-input"
                className="mt-2 bg-white border-sand-300 py-6"
                placeholder="••••••••"
              />
            </div>
            <Button
              type="submit"
              disabled={busy}
              data-testid="login-submit-button"
              className="w-full bg-olive-600 hover:bg-olive-700 text-white py-6"
            >
              {busy ? "Logging in..." : (<>Log in <ArrowRightIcon size={18} /></>)}
            </Button>
          </form>

          <p className="mt-8 text-sm text-sand-700">
            New to BIR Filipino?{" "}
            <Link to="/register" className="text-olive-700 font-semibold hover:text-olive-900 underline" data-testid="login-register-link">
              Create an account
            </Link>
          </p>
        </div>
      </div>

      <div className="hidden lg:block flex-1 bg-olive-900 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-olive-700 via-olive-900 to-olive-900" />
        <div className="relative h-full flex flex-col justify-end p-16">
          <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-400 mb-4">Why we exist</div>
          <h2 className="font-display font-bold text-white text-4xl tracking-tight leading-tight">
            "I used to spend a Saturday on my 1701Q. Now it's done before my coffee gets cold."
          </h2>
          <p className="mt-6 text-sand-300">— Maria, freelance designer · Quezon City</p>
        </div>
      </div>
    </div>
  );
}
