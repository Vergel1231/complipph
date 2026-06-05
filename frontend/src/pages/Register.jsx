import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { formatApiError } from "@/lib/api";
import { ArrowRightIcon } from "@phosphor-icons/react";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await register(email.trim(), password, name.trim());
      toast.success("Account created. Let's set up your business.");
      navigate("/onboarding");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-sand-100">
      <div className="flex-1 grid place-items-center px-6 py-16">
        <div className="w-full max-w-md">
          <Link to="/" className="inline-flex items-center gap-2 mb-12">
            <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white font-display font-bold">B</div>
            <div className="font-display font-bold text-olive-900">BIR Filipino</div>
          </Link>
          <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Start filing in 60 seconds</div>
          <h1 className="font-display font-bold text-olive-900 text-4xl tracking-tight leading-tight mb-2">Create your account</h1>
          <p className="text-sand-700 mb-10">No spreadsheets. No calculator. Just your numbers.</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="name" className="text-olive-900 font-semibold">Full name</Label>
              <Input
                id="name" type="text" required value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-2 bg-white border-sand-300 py-6"
                placeholder="Maria Reyes"
              />
            </div>
            <div>
              <Label htmlFor="email" className="text-olive-900 font-semibold">Email</Label>
              <Input
                id="email" type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2 bg-white border-sand-300 py-6"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <Label htmlFor="password" className="text-olive-900 font-semibold">Password</Label>
              <Input
                id="password" type="password" required value={password} minLength={8}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2 bg-white border-sand-300 py-6"
                placeholder="At least 8 characters"
              />
            </div>
            <Button
              type="submit"
              disabled={busy}
              className="w-full bg-olive-600 hover:bg-olive-700 text-white py-6"
            >
              {busy ? "Creating account..." : (<>Create account <ArrowRightIcon size={18} /></>)}
            </Button>
          </form>

          <p className="mt-8 text-sm text-sand-700">
            Already have an account?{" "}
            <Link to="/login" className="text-olive-700 font-semibold hover:text-olive-900 underline">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
