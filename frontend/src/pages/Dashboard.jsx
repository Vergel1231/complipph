import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import { useAuth } from "@/contexts/AuthContext";
import api, { formatPHP } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  CalendarBlankIcon, ClockCountdownIcon, ArrowRightIcon, FileTextIcon,
  SparkleIcon, ChartBarIcon, WarningCircleIcon, CheckCircleIcon,
} from "@phosphor-icons/react";

const SEV_STYLES = {
  overdue: "bg-terracotta-600 text-white",
  urgent: "bg-terracotta-500 text-white",
  warning: "bg-amber-500 text-white",
  upcoming: "bg-olive-600 text-white",
};

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [deadlines, setDeadlines] = useState([]);
  const [filings, setFilings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [p, d, f] = await Promise.all([
          api.get("/business/profile"),
          api.get("/deadlines/"),
          api.get("/forms/history"),
        ]);
        setProfile(p.data);
        setDeadlines(d.data || []);
        setFilings(f.data || []);
        if (!p.data) navigate("/onboarding");
      } finally {
        setLoading(false);
      }
    })();
  }, [navigate]);

  if (loading) {
    return <AppLayout><div className="text-olive-700">Loading dashboard…</div></AppLayout>;
  }

  const upcoming = deadlines.filter(d => !d.completed && d.days_until >= 0).slice(0, 4);
  const nextDeadline = upcoming[0];
  const totalFilings = filings.length;
  const totalTaxFiled = filings.reduce((s, f) => s + (f?.computed?.tax_payable || 0), 0);

  return (
    <AppLayout>
      {/* Hero greeting */}
      <div className="mb-12">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3" data-testid="dashboard-overline">
          {profile?.taxpayer_classification === "8_percent_flat" ? "8% Flat Tax" : "Graduated Rates"} · {profile?.business_type}
        </div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">
          Hi, {user?.name?.split(" ")[0] || "there"}.
        </h1>
        <p className="mt-3 text-sand-700 text-lg max-w-2xl">
          {nextDeadline
            ? <>Your next filing is <strong className="text-olive-900">{nextDeadline.form_type} for {nextDeadline.period}</strong> — due in <strong className="text-terracotta-600">{nextDeadline.days_until} days</strong>.</>
            : "All your upcoming filings are clear. Quiet quarter."}
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Button
            onClick={() => navigate("/generate")}
            data-testid="dashboard-generate-form-button"
            className="bg-olive-600 hover:bg-olive-700 text-white px-6 py-5"
          >
            <SparkleIcon size={18} weight="duotone" /> Generate a BIR form
          </Button>
          <Button
            onClick={() => navigate("/calendar")}
            variant="outline"
            data-testid="dashboard-view-calendar-button"
            className="border-sand-300 text-olive-900 hover:bg-sand-200 px-6 py-5"
          >
            <CalendarBlankIcon size={18} /> View calendar
          </Button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <StatCard
          icon={ClockCountdownIcon}
          label="Next deadline"
          value={nextDeadline ? `${nextDeadline.days_until}d` : "—"}
          sublabel={nextDeadline ? `${nextDeadline.form_type} · ${nextDeadline.period}` : "All clear"}
          accent={nextDeadline?.days_until <= 7 ? "text-terracotta-600" : "text-olive-700"}
          testid="stat-next-deadline"
        />
        <StatCard
          icon={FileTextIcon}
          label="Filings on file"
          value={String(totalFilings)}
          sublabel="Lifetime"
          accent="text-olive-700"
          testid="stat-filings-count"
        />
        <StatCard
          icon={ChartBarIcon}
          label="Tax filed (lifetime)"
          value={formatPHP(totalTaxFiled)}
          sublabel="Total computed payable"
          accent="text-olive-700"
          testid="stat-tax-total"
        />
      </div>

      {/* Two column: upcoming deadlines + recent filings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white border border-sand-200 rounded-2xl p-6 lg:p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-display font-bold text-olive-900 text-xl">Upcoming deadlines</h2>
            <Button variant="ghost" onClick={() => navigate("/calendar")} className="text-olive-700 hover:bg-sand-100" data-testid="view-all-deadlines-button">
              View all <ArrowRightIcon size={16} />
            </Button>
          </div>
          {upcoming.length === 0 ? (
            <div className="text-center py-10 text-sand-700">
              <CheckCircleIcon size={48} weight="duotone" className="mx-auto text-olive-600 mb-3" />
              <div className="font-display font-semibold text-olive-900">No upcoming deadlines.</div>
              <div className="text-sm mt-1">Sit back. We'll let you know when one's coming.</div>
            </div>
          ) : (
            <div className="space-y-3">
              {upcoming.map((d) => (
                <div
                  key={`${d.form_type}-${d.period}`}
                  className="flex items-center gap-4 p-4 rounded-xl bg-sand-100 hover:bg-sand-200 transition-colors"
                  data-testid={`deadline-row-${d.form_type}-${d.period}`}
                >
                  <div className={`px-3 py-2 rounded-md text-xs font-bold tracking-wide ${SEV_STYLES[d.severity]}`}>
                    {d.days_until}d
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-display font-semibold text-olive-900">
                      BIR {d.form_type} · {d.period}
                    </div>
                    <div className="text-sm text-sand-700">Due {d.due_date}</div>
                  </div>
                  <Button
                    onClick={() => navigate(`/generate?form=${d.form_type}&period=${d.period}`)}
                    size="sm"
                    className="bg-olive-600 hover:bg-olive-700 text-white"
                    data-testid={`deadline-generate-${d.form_type}-${d.period}`}
                  >
                    Generate
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-sand-200 rounded-2xl p-6 lg:p-8">
          <h2 className="font-display font-bold text-olive-900 text-xl mb-6">Recent filings</h2>
          {filings.length === 0 ? (
            <div className="text-center py-8 text-sand-700">
              <FileTextIcon size={36} weight="duotone" className="mx-auto text-olive-600 mb-2" />
              <div className="text-sm">No filings yet.</div>
              <Button
                onClick={() => navigate("/generate")}
                className="mt-4 bg-olive-600 hover:bg-olive-700 text-white"
                data-testid="empty-state-generate-button"
              >
                Generate your first
              </Button>
            </div>
          ) : (
            <ul className="divide-y divide-sand-200">
              {filings.slice(0, 5).map((f) => (
                <li key={f.filing_id} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-olive-900">{f.form_type} · {f.period}</div>
                    <div className="text-xs text-sand-600">{new Date(f.generated_at).toLocaleDateString()}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-display font-bold text-olive-900 tabular-nums">{formatPHP(f.computed?.tax_payable)}</div>
                    <div className="text-[11px] uppercase tracking-wider font-semibold text-olive-700">{f.status}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function StatCard({ icon: Icon, label, value, sublabel, accent, testid }) {
  return (
    <div className="bg-white border border-sand-200 rounded-2xl p-6 hover:border-olive-400 transition-colors" data-testid={testid}>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs tracking-[0.2em] uppercase font-bold text-terracotta-600">{label}</div>
        <Icon size={22} weight="duotone" className="text-olive-600" />
      </div>
      <div className={`font-display text-4xl font-bold tracking-tight tabular-nums ${accent}`}>{value}</div>
      <div className="text-sm text-sand-600 mt-2">{sublabel}</div>
    </div>
  );
}
