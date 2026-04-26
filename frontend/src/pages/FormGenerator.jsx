import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import api, { formatPHP, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Tabs, TabsList, TabsTrigger,
} from "@/components/ui/tabs";
import { toast } from "sonner";
import { SparkleIcon, FileTextIcon, ArrowRightIcon, CheckCircleIcon, ArrowLeftIcon, DownloadSimpleIcon } from "@phosphor-icons/react";

const FORMS = ["1701Q", "2551Q"];
const QUARTERS = ["Q1", "Q2", "Q3", "Q4"];
const yr = new Date().getFullYear();

export default function FormGenerator() {
  const [params] = useSearchParams();
  const initForm = params.get("form") || "1701Q";
  const initPeriod = params.get("period") || `${yr}-Q1`;
  const navigate = useNavigate();

  const [formType, setFormType] = useState(initForm);
  const [period, setPeriod] = useState(initPeriod);
  const [profile, setProfile] = useState(null);
  const [step, setStep] = useState(1); // 1 input, 2 preview
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [inputs, setInputs] = useState({
    gross_sales: "",
    other_income: "",
    cost_of_sales: "",
    operating_expenses: "",
    creditable_tax_withheld: "",
    tax_paid_previous_quarters: "",
  });

  useEffect(() => {
    (async () => {
      const { data } = await api.get("/business/profile");
      setProfile(data);
    })();
  }, []);

  const isFlat = profile?.taxpayer_classification === "8_percent_flat";
  const blocks2551 = isFlat || profile?.is_vat_registered;

  const handleGenerate = async () => {
    if (formType === "2551Q" && blocks2551) {
      toast.error("2551Q is not required for your taxpayer classification.");
      return;
    }
    setBusy(true);
    try {
      const num = (k) => Number(inputs[k] || 0);
      const { data } = await api.post("/forms/generate", {
        form_type: formType,
        period,
        gross_sales: num("gross_sales"),
        other_income: num("other_income"),
        cost_of_sales: num("cost_of_sales"),
        operating_expenses: num("operating_expenses"),
        creditable_tax_withheld: num("creditable_tax_withheld"),
        tax_paid_previous_quarters: num("tax_paid_previous_quarters"),
      });
      setResult(data);
      setStep(2);
      toast.success(`Your ${formType} is ready.`);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.form_type}_${result.period}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <AppLayout>
      <div className="mb-10">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">BIR Form Generator</div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">
          {step === 1 ? "Generate your form" : "Your form is ready."}
        </h1>
        <p className="mt-3 text-sand-700 text-lg">
          {step === 1
            ? "Type your numbers — we map every peso to the correct BIR line."
            : "Review the computed values, then mark as submitted once you've filed via eBIRForms."}
        </p>
      </div>

      {step === 1 && (
        <div className="bg-white border border-sand-200 rounded-2xl p-6 lg:p-10 max-w-3xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
            <div>
              <Label className="text-olive-900 font-semibold">Form type</Label>
              <Tabs value={formType} onValueChange={setFormType} className="mt-2">
                <TabsList className="bg-sand-100 border border-sand-300 w-full">
                  {FORMS.map(f => (
                    <TabsTrigger key={f} value={f} data-testid={`form-tab-${f}`}
                      disabled={f === "2551Q" && blocks2551}
                      className="flex-1 data-[state=active]:bg-olive-600 data-[state=active]:text-white">
                      {f}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
              {formType === "2551Q" && blocks2551 && (
                <p className="text-xs text-terracotta-600 mt-2">2551Q is not required for {isFlat ? "8% flat" : "VAT-registered"} taxpayers.</p>
              )}
            </div>
            <div>
              <Label className="text-olive-900 font-semibold">Period</Label>
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                data-testid="form-period-select"
                className="mt-2 w-full rounded-md border border-sand-300 bg-white px-3 py-3 text-olive-900"
              >
                {[yr - 1, yr, yr + 1].flatMap(year =>
                  QUARTERS.map(q => <option key={`${year}-${q}`} value={`${year}-${q}`}>{year} · {q}</option>)
                )}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <NumberInput label="Gross Sales / Receipts (₱)" testid="input-gross-sales" value={inputs.gross_sales} onChange={(v) => setInputs({ ...inputs, gross_sales: v })} required />
            {formType === "1701Q" && (
              <>
                <NumberInput label="Other Income (₱)" testid="input-other-income" value={inputs.other_income} onChange={(v) => setInputs({ ...inputs, other_income: v })} />
                {!isFlat && (
                  <>
                    <NumberInput label="Cost of Sales / Services (₱)" testid="input-cost-of-sales" value={inputs.cost_of_sales} onChange={(v) => setInputs({ ...inputs, cost_of_sales: v })} />
                    <NumberInput label="Operating Expenses (₱)" testid="input-operating-expenses" value={inputs.operating_expenses} onChange={(v) => setInputs({ ...inputs, operating_expenses: v })} />
                  </>
                )}
              </>
            )}
            <NumberInput label="Creditable Tax Withheld (₱)" testid="input-creditable-tax" value={inputs.creditable_tax_withheld} onChange={(v) => setInputs({ ...inputs, creditable_tax_withheld: v })} />
            <NumberInput label="Tax Paid in Previous Quarters (₱)" testid="input-prev-tax" value={inputs.tax_paid_previous_quarters} onChange={(v) => setInputs({ ...inputs, tax_paid_previous_quarters: v })} />
          </div>

          <div className="mt-10 flex justify-end gap-3">
            <Button variant="outline" onClick={() => navigate("/dashboard")} data-testid="generate-back-button" className="border-sand-300 text-olive-900 hover:bg-sand-200">
              <ArrowLeftIcon size={16} /> Back
            </Button>
            <Button onClick={handleGenerate} disabled={busy || !inputs.gross_sales} data-testid="generate-submit-button" className="bg-olive-600 hover:bg-olive-700 text-white px-8">
              {busy ? "Generating…" : (<>Generate {formType} <SparkleIcon size={18} /></>)}
            </Button>
          </div>
        </div>
      )}

      {step === 2 && result && (
        <div className="space-y-6 max-w-4xl">
          <div className="bg-olive-600 rounded-2xl p-8 text-white">
            <div className="flex items-center gap-3 mb-4">
              <CheckCircleIcon size={28} weight="duotone" />
              <div className="text-xs tracking-[0.25em] uppercase font-bold opacity-90">Form generated</div>
            </div>
            <h2 className="font-display font-bold text-3xl lg:text-4xl tracking-tight">
              BIR {result.form_type} · {result.period}
            </h2>
            <div className="mt-6 flex flex-col sm:flex-row sm:items-end gap-6">
              <div>
                <div className="text-xs uppercase tracking-widest opacity-80">Tax Payable</div>
                <div className="font-display text-5xl font-bold tabular-nums">{formatPHP(result.computed.tax_payable)}</div>
              </div>
              <div className="text-sand-100">
                <div className="text-xs uppercase tracking-widest opacity-80">Method</div>
                <div className="font-medium">{result.computed.method}</div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-sand-200 rounded-2xl p-6 lg:p-8">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-display font-bold text-olive-900 text-xl">Pre-filled BIR fields</h3>
              <FileTextIcon size={24} weight="duotone" className="text-olive-600" />
            </div>
            <table className="w-full text-sm" data-testid="form-result-table">
              <tbody className="divide-y divide-sand-200">
                {Object.entries(result.computed.field_map).map(([line, val]) => (
                  <tr key={line}>
                    <td className="py-3 pr-4 text-sand-800">{line}</td>
                    <td className="py-3 text-right font-display font-semibold text-olive-900 tabular-nums">
                      {typeof val === "number" ? formatPHP(val) : val}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={downloadJSON} data-testid="download-form-button" className="bg-terracotta-500 hover:bg-terracotta-600 text-white px-6 py-5">
              <DownloadSimpleIcon size={18} /> Download JSON
            </Button>
            <Button
              onClick={async () => {
                await api.post(`/forms/${result.filing_id}/mark-submitted`);
                toast.success("Marked as submitted. Deadline closed.");
                navigate("/history");
              }}
              variant="outline"
              data-testid="mark-submitted-button"
              className="border-olive-600 text-olive-900 hover:bg-olive-50 px-6 py-5"
            >
              <CheckCircleIcon size={18} /> Mark as submitted
            </Button>
            <Button
              variant="outline"
              onClick={() => { setStep(1); setResult(null); }}
              data-testid="generate-another-button"
              className="border-sand-300 text-olive-900 hover:bg-sand-200 px-6 py-5"
            >
              Generate another
            </Button>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

function NumberInput({ label, value, onChange, testid, required }) {
  return (
    <div>
      <Label className="text-olive-900 font-semibold">{label}{required && <span className="text-terracotta-600"> *</span>}</Label>
      <Input
        type="number" inputMode="decimal" min="0" step="0.01"
        value={value} onChange={(e) => onChange(e.target.value)}
        data-testid={testid}
        className="mt-2 bg-white border-sand-300 py-6 tabular-nums"
        placeholder="0.00"
      />
    </div>
  );
}
