import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { formatPHP, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { CheckCircleIcon, ArrowRightIcon } from "@phosphor-icons/react";

export default function Pricing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const { data } = await api.get("/billing/plans");
      setPlans(data);
    })();
  }, []);

  const subscribe = async (plan) => {
    if (!user) {
      navigate("/register");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post("/billing/checkout", { plan });
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        toast.success(data.message || "Subscribed!");
        navigate("/dashboard");
      }
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const FEATURES = {
    solo: ["1 business profile", "Unlimited 1701Q + 2551Q filings", "Deadline calendar (30/7/1d)", "AI tax assistant", "Filing history archive"],
    pro: ["Up to 3 business profiles", "Everything in Solo", "Payroll module (1604C ready)", "AI assistant priority", "Email + chat support"],
    reseller: ["Up to 25 client filings", "Dedicated CPA dashboard", "Bulk deadline tracking", "Per-client filing history", "Reseller revenue share"],
  };

  return (
    <div className="min-h-screen bg-sand-100 paper-grain">
      <header className="border-b border-sand-300 bg-sand-100/85 backdrop-blur-xl">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="pricing-logo-link">
            <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white font-display font-bold">C</div>
            <div className="font-display font-bold text-olive-900">CompliPH</div>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-sand-800">
            <Link to="/" className="hover:text-olive-900">Home</Link>
            <Link to="/faq" className="hover:text-olive-900">FAQ</Link>
            <Link to={user ? "/dashboard" : "/login"} className="hover:text-olive-900" data-testid="pricing-account-link">
              {user ? "Dashboard" : "Log in"}
            </Link>
          </nav>
          <Link
            to={user ? "/dashboard" : "/login"}
            className="md:hidden text-sm font-medium text-olive-800 hover:text-olive-900"
            data-testid="pricing-account-link-mobile"
          >
            {user ? "Dashboard" : "Log in"}
          </Link>
        </div>
      </header>

      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 py-20 text-center">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-4">Simple pricing</div>
        <h1 className="font-display font-bold text-olive-900 text-4xl lg:text-6xl tracking-tight max-w-3xl mx-auto leading-tight">
          Pay less than one freelancer hour. Save four every quarter.
        </h1>
        <p className="mt-6 text-lg text-sand-700 max-w-2xl mx-auto">
          Monthly billing in PHP via PayMongo. GCash, GrabPay, Maya, and cards accepted.
        </p>
      </section>

      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 pb-24 grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(plans).map(([k, p]) => {
          const featured = k === "pro";
          return (
            <div
              key={k}
              data-testid={`plan-card-${k}`}
              className={`rounded-2xl p-8 border-2 transition-all duration-300 ${
                featured ? "bg-olive-900 border-olive-900 text-white" : "bg-white border-sand-200"
              }`}
            >
              <div className={`text-xs tracking-[0.25em] uppercase font-bold mb-3 ${featured ? "text-terracotta-400" : "text-terracotta-600"}`}>
                {p.name}
              </div>
              <div className={`font-display text-5xl font-bold tracking-tight ${featured ? "text-white" : "text-olive-900"}`}>
                {formatPHP(p.amount_php)}
              </div>
              <div className={`text-sm mt-1 ${featured ? "text-sand-300" : "text-sand-700"}`}>per month · ${p.amount_usd} USD</div>
              <p className={`mt-4 text-sm ${featured ? "text-sand-200" : "text-sand-700"}`}>{p.description}</p>
              <ul className="mt-7 space-y-3">
                {(FEATURES[k] || []).map(f => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <CheckCircleIcon size={18} weight="duotone" className={featured ? "text-terracotta-400 shrink-0 mt-0.5" : "text-olive-600 shrink-0 mt-0.5"} />
                    <span className={featured ? "text-sand-100" : "text-sand-800"}>{f}</span>
                  </li>
                ))}
              </ul>
              <Button
                onClick={() => subscribe(k)}
                disabled={busy}
                data-testid={`plan-subscribe-${k}`}
                className={`mt-8 w-full py-6 ${
                  featured ? "bg-terracotta-500 hover:bg-terracotta-600 text-white" : "bg-olive-600 hover:bg-olive-700 text-white"
                }`}
              >
                {busy ? "Working…" : (<>Subscribe <ArrowRightIcon size={16} /></>)}
              </Button>
              {k !== "reseller" && (
                <div className={`mt-3 text-[11px] uppercase tracking-widest font-semibold text-center ${featured ? "text-sand-300" : "text-sand-600"}`}>
                  Charged immediately · cancel anytime
                </div>
              )}
            </div>
          );
        })}
      </section>

      <section className="bg-olive-900 text-sand-50 py-14 text-center">
        <p className="font-display text-xl">
          Questions? Email <a href="mailto:hello@complipph.app" className="underline">hello@complipph.app</a>
          {" "}or{" "}
          <Link to="/faq" className="underline">read the FAQ</Link>
        </p>
      </section>
    </div>
  );
}
