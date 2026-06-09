import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import {
  CalculatorIcon, CalendarCheckIcon, FileTextIcon, ShieldCheckIcon,
  SparkleIcon, UsersThreeIcon, ArrowRightIcon, CheckCircleIcon, ClockCountdownIcon,
} from "@phosphor-icons/react";

const HERO_IMG = "https://images.pexels.com/photos/4683642/pexels-photo-4683642.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";
const AUDIENCE_IMG = "https://images.pexels.com/photos/32254665/pexels-photo-32254665.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

export default function Landing() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-sand-100 paper-grain">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-sand-100/85 backdrop-blur-xl border-b border-sand-300">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="landing-logo-link">
            <div className="h-9 w-9 rounded-md bg-olive-600 grid place-items-center text-white font-display font-bold">C</div>
            <div className="font-display font-bold text-olive-900 text-lg">CompliPH</div>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-sand-800">
            <a href="#how" className="hover:text-olive-900">How it works</a>
            <a href="#why" className="hover:text-olive-900">Why us</a>
            <Link to="/pricing" className="hover:text-olive-900" data-testid="landing-pricing-link">Pricing</Link>
            <a href="#cpas" className="hover:text-olive-900">For CPAs</a>
            <Link to="/faq" className="hover:text-olive-900">FAQ</Link>
          </nav>
          <div className="flex items-center gap-3">
            {user ? (
              <Button
                onClick={() => navigate("/dashboard")}
                data-testid="landing-go-to-dashboard-button"
                className="bg-olive-600 text-white hover:bg-olive-700"
              >
                Go to dashboard <ArrowRightIcon size={16} />
              </Button>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-olive-800 hover:text-olive-900" data-testid="landing-login-link">Log in</Link>
                <Button
                  onClick={() => navigate("/register")}
                  data-testid="landing-get-started-button"
                  className="bg-olive-600 text-white hover:bg-olive-700"
                >
                  Get started
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero — Tetris Grid */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 pt-12 pb-20 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">
        <div className="lg:col-span-7 flex flex-col justify-center">
          <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-5" data-testid="landing-overline">
            Quarterly ITR · 1701Q · 2551Q · for Filipinos
          </div>
          <h1 className="font-display font-bold text-olive-900 text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-[1.05]">
            Your BIR form,
            <br />
            <span className="text-terracotta-600">done in 60 seconds.</span>
          </h1>
          <p className="mt-7 text-lg text-sand-700 leading-relaxed max-w-xl">
            Built for Filipino consultants, designers, lawyers, and doctors. Stop spending 4 hours
            wrestling with BIR computations. Type your gross sales — we generate a pre-filled,
            ready-to-submit 1701Q or 2551Q.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Button
              onClick={() => navigate(user ? "/dashboard" : "/register")}
              data-testid="hero-cta-primary"
              size="lg"
              className="bg-olive-600 text-white hover:bg-olive-700 px-7 py-6 text-base"
            >
              Generate my first form <ArrowRightIcon size={18} />
            </Button>
            <Button
              onClick={() => navigate("/pricing")}
              data-testid="hero-cta-secondary"
              variant="outline"
              size="lg"
              className="border-sand-300 text-olive-900 hover:bg-sand-200 px-7 py-6 text-base"
            >
              See pricing
            </Button>
          </div>
          <div className="mt-10 flex items-center gap-6 text-sm text-sand-600">
            <div className="flex items-center gap-2"><CheckCircleIcon size={18} className="text-olive-600" /> 8% flat + Graduated</div>
            <div className="flex items-center gap-2"><CheckCircleIcon size={18} className="text-olive-600" /> Deadline reminders</div>
            <div className="flex items-center gap-2"><CheckCircleIcon size={18} className="text-olive-600" /> AI tax assistant</div>
          </div>
        </div>
        <div className="lg:col-span-5 relative">
          <div className="relative rounded-2xl overflow-hidden border border-sand-300 shadow-sm">
            <img src={HERO_IMG} alt="Filipino freelancer working from home" className="w-full h-[460px] object-cover" />
            <div className="absolute inset-0 bg-gradient-to-tr from-olive-900/40 via-transparent to-transparent" />
            <div className="absolute bottom-5 left-5 right-5 bg-white/95 backdrop-blur-sm rounded-xl p-4 border border-sand-200">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-olive-600 grid place-items-center text-white">
                  <CalculatorIcon size={20} weight="bold" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs uppercase tracking-wider text-terracotta-600 font-bold">1701Q · Q1 2026</div>
                  <div className="text-olive-900 font-display font-bold">Tax Payable: ₱4,800.00</div>
                </div>
                <div className="text-xs font-semibold text-olive-700">Generated</div>
              </div>
            </div>
          </div>
          <div className="absolute -top-5 -left-5 bg-terracotta-600 text-white rounded-xl px-4 py-3 shadow-lg rotate-[-3deg] hidden lg:block">
            <div className="text-[10px] tracking-widest uppercase font-bold opacity-90">Time saved</div>
            <div className="text-2xl font-display font-bold">3h 47m</div>
          </div>
        </div>
      </section>

      {/* Pain → Relief band */}
      <section className="bg-olive-900 text-sand-50 py-20" id="why">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 grid grid-cols-1 lg:grid-cols-3 gap-10">
          {[
            { stat: "2–4h", label: "wasted per filing period on manual forms" },
            { stat: "₱1,000+", label: "compromise penalty if you miss a BIR deadline" },
            { stat: "25%", label: "surcharge on top of unpaid tax for late filers" },
          ].map((s) => (
            <div key={s.label} className="border-l border-sand-50/20 pl-6">
              <div className="font-display text-5xl font-bold text-terracotta-400">{s.stat}</div>
              <div className="mt-3 text-sand-200 leading-relaxed">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 py-24" id="how">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-4">How it works</div>
        <h2 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight max-w-2xl">
          From BIR fear to BIR done — in 3 calm steps.
        </h2>
        <div className="mt-14 grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { n: "01", icon: UsersThreeIcon, title: "Set up your business profile", body: "Tell us your taxpayer classification — 8% flat or graduated. We lock in the right forms and schedule." },
            { n: "02", icon: SparkleIcon, title: "Type your numbers", body: "Gross sales, expenses, withholdings. Our engine maps each peso to the correct BIR line — never opens a calculator." },
            { n: "03", icon: FileTextIcon, title: "Download & submit", body: "Get a pre-filled 1701Q or 2551Q. We track the deadline, notify you 30/7/1 day ahead, and archive every filing." },
          ].map((s) => (
            <div
              key={s.n}
              className="bg-white rounded-2xl border border-sand-200 p-8 hover:border-olive-600 transition-all duration-300"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="text-terracotta-600 font-display text-3xl font-bold">{s.n}</div>
                <s.icon size={28} weight="duotone" className="text-olive-600" />
              </div>
              <h3 className="font-display font-semibold text-xl text-olive-900 mb-3">{s.title}</h3>
              <p className="text-sand-700 leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Audience showcase */}
      <section className="bg-sand-200 py-24">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 grid grid-cols-1 lg:grid-cols-12 gap-12">
          <div className="lg:col-span-5">
            <div className="rounded-2xl overflow-hidden border border-sand-300">
              <img src={AUDIENCE_IMG} alt="Solo professional" className="w-full h-[480px] object-cover" />
            </div>
          </div>
          <div className="lg:col-span-7 flex flex-col justify-center">
            <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-4">For solo professionals</div>
            <h2 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">
              Built for the people who hate filing taxes the most.
            </h2>
            <ul className="mt-8 space-y-4">
              {[
                "Consultants splitting time between projects",
                "Designers chasing client retainers",
                "Lawyers running solo practices",
                "Doctors with private clinics + HMO billings",
              ].map((p) => (
                <li key={p} className="flex items-start gap-3 text-lg text-sand-800">
                  <CheckCircleIcon size={22} weight="duotone" className="text-olive-600 mt-1 shrink-0" />
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Retention / lock-in band */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 py-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          <div>
            <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-4">Why people keep paying</div>
            <h2 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight leading-tight">
              Your filing history lives here. It gets <em className="text-terracotta-600 not-italic">smarter every quarter.</em>
            </h2>
            <p className="mt-7 text-lg text-sand-700 leading-relaxed">
              Each quarter, the app remembers your numbers, your forms, your deadlines. Q2 takes
              half the time of Q1. By Q4 you'll wonder how you ever did this manually. Cancel and
              you go back to spreadsheets and panic.
            </p>
          </div>
          <div className="bg-white rounded-2xl border border-sand-200 p-8 lg:p-10">
            <h3 className="font-display font-semibold text-2xl text-olive-900 mb-6">What you lose if you cancel</h3>
            <ul className="space-y-4">
              {[
                { icon: ClockCountdownIcon, t: "30/7/1 day deadline reminders" },
                { icon: FileTextIcon, t: "Archive of every BIR form you've filed" },
                { icon: CalculatorIcon, t: "Pre-filled returns from past quarters" },
                { icon: CalendarCheckIcon, t: "Your annual compliance paper trail" },
              ].map((x) => (
                <li key={x.t} className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-md bg-sand-200 grid place-items-center text-olive-700">
                    <x.icon size={20} weight="duotone" />
                  </div>
                  <div className="font-medium text-olive-900">{x.t}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* CPAs / Reseller */}
      <section className="bg-olive-900 text-sand-50 py-24" id="cpas">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 grid grid-cols-1 lg:grid-cols-2 gap-12">
          <div>
            <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-400 mb-4">For CPAs & bookkeepers</div>
            <h2 className="font-display font-bold text-3xl lg:text-5xl text-white tracking-tight">
              Manage 25 client filings from one calm dashboard.
            </h2>
            <p className="mt-6 text-sand-200 text-lg leading-relaxed">
              Reseller plan: bring your client roster, earn a recurring seat fee per active client,
              and never miss a quarterly deadline again — across all of them.
            </p>
            <div className="mt-8">
              <Button
                onClick={() => navigate("/pricing")}
                data-testid="cpa-cta"
                className="bg-terracotta-500 hover:bg-terracotta-600 text-white px-7 py-6 text-base"
              >
                See reseller plan <ArrowRightIcon size={18} />
              </Button>
            </div>
          </div>
          <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10">
            <div className="flex items-center gap-3 mb-6">
              <ShieldCheckIcon size={28} weight="duotone" className="text-terracotta-400" />
              <div className="font-display text-xl font-semibold">Reseller dashboard</div>
            </div>
            <div className="space-y-3">
              {["Client #1024 — Maria Cruz", "Client #1025 — Jaime Reyes", "Client #1026 — Aileen Tan"].map((c, i) => (
                <div key={c} className="flex items-center justify-between bg-white/10 rounded-lg px-4 py-3">
                  <div className="text-sm text-sand-100">{c}</div>
                  <div className={`text-xs font-semibold ${i === 1 ? "text-terracotta-400" : "text-sage-200"}`}>
                    {i === 1 ? "Due in 5 days" : "Filed"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-12 py-24 text-center">
        <h2 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight max-w-3xl mx-auto leading-tight">
          Stop dreading BIR season. Start your first filing today.
        </h2>
        <div className="mt-10">
          <Button
            onClick={() => navigate(user ? "/dashboard" : "/register")}
            data-testid="footer-cta-button"
            size="lg"
            className="bg-terracotta-500 hover:bg-terracotta-600 text-white px-9 py-7 text-base"
          >
            Generate my first BIR form <ArrowRightIcon size={18} />
          </Button>
        </div>
      </section>

      <footer className="bg-olive-900 text-sand-300 py-14">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-12 flex flex-col md:flex-row justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-9 w-9 rounded-md bg-terracotta-500 grid place-items-center text-white font-display font-bold">C</div>
              <div className="font-display font-bold text-white text-lg">CompliPH</div>
            </div>
            <p className="text-sm text-sand-400 max-w-sm">
              The solo professional's tool that generates your BIR form in 60 seconds.
            </p>
          </div>
          <div className="text-sm">
            © {new Date().getFullYear()} CompliPH. Made in Manila.
          </div>
        </div>
      </footer>
    </div>
  );
}
