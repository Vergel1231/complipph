import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import api from "@/lib/api";
import { CalendarBlankIcon, CheckCircleIcon, WarningCircleIcon } from "@phosphor-icons/react";

const SEV_STYLES = {
  overdue: "bg-terracotta-700 text-white",
  urgent: "bg-terracotta-500 text-white",
  warning: "bg-amber-500 text-white",
  upcoming: "bg-olive-600 text-white",
};

export default function CalendarView() {
  const [deadlines, setDeadlines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const { data } = await api.get("/deadlines/");
      setDeadlines(data || []);
      setLoading(false);
    })();
  }, []);

  const grouped = deadlines.reduce((acc, d) => {
    const k = d.due_date.slice(0, 7); // YYYY-MM
    (acc[k] ||= []).push(d);
    return acc;
  }, {});

  return (
    <AppLayout>
      <div className="mb-10">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Stay ahead</div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">BIR Deadline Calendar</h1>
        <p className="mt-3 text-sand-700 text-lg max-w-2xl">
          Reminders fire at <strong>30, 7, and 1 day</strong> before each filing deadline. Avoid the 25% surcharge.
        </p>
      </div>

      {loading ? (
        <div className="text-sand-700">Loading…</div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).sort().map(([month, items]) => (
            <div key={month}>
              <div className="flex items-center gap-3 mb-4">
                <CalendarBlankIcon size={22} weight="duotone" className="text-olive-600" />
                <h2 className="font-display font-bold text-olive-900 text-xl">
                  {new Date(month + "-01").toLocaleDateString("en-PH", { month: "long", year: "numeric" })}
                </h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {items.map((d) => (
                  <div
                    key={`${d.form_type}-${d.period}`}
                    data-testid={`calendar-deadline-${d.form_type}-${d.period}`}
                    className={`bg-white border rounded-xl p-5 transition-colors ${
                      d.completed ? "border-sage-300 bg-sage-50" : "border-sand-200 hover:border-olive-400"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-display font-bold text-olive-900 text-lg">
                          BIR {d.form_type} · {d.period}
                        </div>
                        <div className="text-sm text-sand-700 mt-1">Due {d.due_date}</div>
                      </div>
                      {d.completed ? (
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-sage-200 text-olive-900">
                          <CheckCircleIcon size={14} weight="fill" /> Filed
                        </span>
                      ) : (
                        <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide ${SEV_STYLES[d.severity]}`}>
                          {d.days_until < 0 ? `${Math.abs(d.days_until)}d overdue` : `in ${d.days_until}d`}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {Object.keys(grouped).length === 0 && (
            <div className="bg-white border border-sand-200 rounded-2xl p-10 text-center">
              <CalendarBlankIcon size={42} weight="duotone" className="mx-auto text-olive-600 mb-3" />
              <div className="font-display font-semibold text-olive-900">No upcoming deadlines yet.</div>
              <div className="text-sm text-sand-700 mt-1">Complete onboarding to populate your calendar.</div>
            </div>
          )}
        </div>
      )}
    </AppLayout>
  );
}
