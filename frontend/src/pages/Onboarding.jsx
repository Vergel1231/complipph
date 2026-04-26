import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { formatApiError } from "@/lib/api";
import { CheckCircleIcon, BriefcaseIcon, ScalesIcon, CalendarBlankIcon } from "@phosphor-icons/react";

const BUSINESS_TYPES = [
  { v: "consultant", label: "Consultant" },
  { v: "designer", label: "Designer" },
  { v: "lawyer", label: "Lawyer" },
  { v: "doctor", label: "Doctor" },
  { v: "developer", label: "Developer" },
  { v: "writer", label: "Writer" },
  { v: "coach", label: "Coach / Trainer" },
  { v: "other", label: "Other Solo Professional" },
];

const QUARTERS = ["Q1", "Q2", "Q3", "Q4"];
const currentYear = new Date().getFullYear();

export default function Onboarding() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState({
    legal_name: "",
    trade_name: "",
    tin: "",
    rdo_code: "",
    business_type: "consultant",
    taxpayer_classification: "",
    is_vat_registered: false,
    line_of_business: "",
    first_filing_period: `${currentYear}-Q1`,
  });

  const next = () => setStep((s) => Math.min(3, s + 1));
  const back = () => setStep((s) => Math.max(1, s - 1));

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/business/profile", data);
      await refresh();
      toast.success("You're all set. Welcome to your dashboard!");
      navigate("/dashboard");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-sand-100 px-6 py-16">
      <div className="max-w-2xl mx-auto">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Step {step} of 3</div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-4xl tracking-tight mb-2">
          {step === 1 && "Tell us about your work"}
          {step === 2 && "Pick your taxpayer classification"}
          {step === 3 && "First filing period"}
        </h1>
        <p className="text-sand-700 mb-10">
          {step === 1 && "We use this to map your filings to the right BIR forms."}
          {step === 2 && "This determines whether you file 8% flat or graduated rates — and whether 2551Q applies."}
          {step === 3 && "We'll start tracking deadlines from this quarter forward."}
        </p>

        <Progress value={(step / 3) * 100} className="mb-12" data-testid="onboarding-progress" />

        <div className="bg-white rounded-2xl border border-sand-200 p-8 lg:p-10">
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <Label htmlFor="legal_name" className="text-olive-900 font-semibold">Legal name (as registered with BIR)</Label>
                <Input
                  id="legal_name" required value={data.legal_name}
                  onChange={(e) => setData({ ...data, legal_name: e.target.value })}
                  data-testid="onboarding-legal-name-input"
                  className="mt-2 bg-white border-sand-300 py-6"
                  placeholder="Maria L. Reyes"
                />
              </div>
              <div>
                <Label htmlFor="trade_name" className="text-olive-900 font-semibold">Trade name (optional)</Label>
                <Input
                  id="trade_name" value={data.trade_name}
                  onChange={(e) => setData({ ...data, trade_name: e.target.value })}
                  data-testid="onboarding-trade-name-input"
                  className="mt-2 bg-white border-sand-300 py-6"
                  placeholder="Reyes Design Studio"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <Label htmlFor="tin" className="text-olive-900 font-semibold">TIN</Label>
                  <Input
                    id="tin" required value={data.tin}
                    onChange={(e) => setData({ ...data, tin: e.target.value })}
                    data-testid="onboarding-tin-input"
                    className="mt-2 bg-white border-sand-300 py-6 tabular-nums"
                    placeholder="123-456-789-000"
                  />
                </div>
                <div>
                  <Label htmlFor="rdo" className="text-olive-900 font-semibold">RDO code</Label>
                  <Input
                    id="rdo" value={data.rdo_code}
                    onChange={(e) => setData({ ...data, rdo_code: e.target.value })}
                    data-testid="onboarding-rdo-input"
                    className="mt-2 bg-white border-sand-300 py-6 tabular-nums"
                    placeholder="045"
                  />
                </div>
              </div>
              <div>
                <Label className="text-olive-900 font-semibold">Type of work</Label>
                <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-2">
                  {BUSINESS_TYPES.map((t) => (
                    <button
                      key={t.v}
                      type="button"
                      onClick={() => setData({ ...data, business_type: t.v })}
                      data-testid={`onboarding-business-type-${t.v}`}
                      className={`px-3 py-3 rounded-md border text-sm font-medium text-left transition-colors ${
                        data.business_type === t.v
                          ? "bg-olive-600 text-white border-olive-600"
                          : "bg-white border-sand-300 text-olive-800 hover:bg-sand-200"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <Label htmlFor="lob" className="text-olive-900 font-semibold">Line of business (optional)</Label>
                <Input
                  id="lob" value={data.line_of_business}
                  onChange={(e) => setData({ ...data, line_of_business: e.target.value })}
                  data-testid="onboarding-lob-input"
                  className="mt-2 bg-white border-sand-300 py-6"
                  placeholder="Brand identity & web design"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              {[
                {
                  v: "8_percent_flat",
                  title: "8% Flat Tax",
                  body: "Pay 8% on gross sales/receipts in excess of ₱250,000. No 2551Q. Best for service-based freelancers under ₱3M/year.",
                  icon: ScalesIcon,
                },
                {
                  v: "graduated",
                  title: "Graduated Rates",
                  body: "TRAIN-Law brackets on net taxable income (after allowable expenses). 2551Q (3% percentage tax) applies. Better if you have heavy deductible expenses.",
                  icon: BriefcaseIcon,
                },
              ].map((c) => (
                <button
                  key={c.v}
                  type="button"
                  onClick={() => setData({ ...data, taxpayer_classification: c.v })}
                  data-testid={`onboarding-classification-${c.v}`}
                  className={`w-full text-left p-6 rounded-xl border-2 transition-all duration-200 ${
                    data.taxpayer_classification === c.v
                      ? "border-olive-600 bg-olive-50"
                      : "border-sand-300 bg-white hover:border-olive-400"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`h-12 w-12 rounded-md grid place-items-center shrink-0 ${
                      data.taxpayer_classification === c.v ? "bg-olive-600 text-white" : "bg-sand-200 text-olive-700"
                    }`}>
                      <c.icon size={24} weight="duotone" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div className="font-display font-bold text-olive-900 text-lg">{c.title}</div>
                        {data.taxpayer_classification === c.v && (
                          <CheckCircleIcon size={22} weight="fill" className="text-olive-600" />
                        )}
                      </div>
                      <div className="mt-2 text-sand-700 leading-relaxed text-sm">{c.body}</div>
                    </div>
                  </div>
                </button>
              ))}
              <label className="flex items-center gap-3 mt-6 cursor-pointer">
                <input
                  type="checkbox"
                  checked={data.is_vat_registered}
                  onChange={(e) => setData({ ...data, is_vat_registered: e.target.checked })}
                  data-testid="onboarding-vat-checkbox"
                  className="h-5 w-5 rounded border-sand-400 text-olive-600 focus:ring-terracotta-500"
                />
                <span className="text-sm text-olive-900 font-medium">I am VAT-registered (gross over ₱3M/yr)</span>
              </label>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <div>
                <Label className="text-olive-900 font-semibold">First filing period</Label>
                <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
                  {QUARTERS.map((q) => {
                    const value = `${currentYear}-${q}`;
                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setData({ ...data, first_filing_period: value })}
                        data-testid={`onboarding-period-${q.toLowerCase()}`}
                        className={`px-4 py-4 rounded-md border-2 text-sm font-semibold transition-colors ${
                          data.first_filing_period === value
                            ? "border-olive-600 bg-olive-600 text-white"
                            : "border-sand-300 bg-white text-olive-900 hover:bg-sand-200"
                        }`}
                      >
                        <CalendarBlankIcon size={20} className="mx-auto mb-1" />
                        {q} {currentYear}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="bg-sand-100 border border-sand-300 rounded-md p-5">
                <div className="text-xs tracking-widest uppercase font-bold text-olive-700 mb-1">Summary</div>
                <div className="text-sm text-sand-800 leading-relaxed">
                  <strong>{BUSINESS_TYPES.find(t => t.v === data.business_type)?.label}</strong> filing under
                  <strong> {data.taxpayer_classification === "8_percent_flat" ? "8% Flat Tax" : "Graduated Rates"}</strong>,
                  starting from <strong>{data.first_filing_period}</strong>.
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-between mt-10">
            <Button
              variant="outline"
              onClick={back}
              disabled={step === 1}
              data-testid="onboarding-back-button"
              className="border-sand-300 text-olive-900 hover:bg-sand-200"
            >
              Back
            </Button>
            {step < 3 ? (
              <Button
                onClick={next}
                disabled={
                  (step === 1 && (!data.legal_name || !data.tin)) ||
                  (step === 2 && !data.taxpayer_classification)
                }
                data-testid="onboarding-next-button"
                className="bg-olive-600 hover:bg-olive-700 text-white px-8"
              >
                Continue
              </Button>
            ) : (
              <Button
                onClick={submit}
                disabled={busy}
                data-testid="onboarding-submit-button"
                className="bg-terracotta-500 hover:bg-terracotta-600 text-white px-8"
              >
                {busy ? "Saving..." : "Finish setup"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
