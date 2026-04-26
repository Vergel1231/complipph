import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import api, { formatPHP } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { FileTextIcon, EyeIcon } from "@phosphor-icons/react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

export default function FilingHistory() {
  const [filings, setFilings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    (async () => {
      const { data } = await api.get("/forms/history");
      setFilings(data || []);
      setLoading(false);
    })();
  }, []);

  return (
    <AppLayout>
      <div className="mb-10">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Compliance archive</div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">Filing history</h1>
        <p className="mt-3 text-sand-700 text-lg max-w-2xl">
          Every form you've generated lives here — your complete BIR paper trail. This is the part you cannot afford to lose.
        </p>
      </div>

      <div className="bg-white border border-sand-200 rounded-2xl overflow-hidden">
        <table className="w-full text-sm" data-testid="filing-history-table">
          <thead className="bg-sand-100 text-olive-900">
            <tr>
              <th className="text-left px-6 py-4 font-display font-semibold">Form</th>
              <th className="text-left px-6 py-4 font-display font-semibold">Period</th>
              <th className="text-left px-6 py-4 font-display font-semibold">Generated</th>
              <th className="text-right px-6 py-4 font-display font-semibold">Tax Payable</th>
              <th className="text-left px-6 py-4 font-display font-semibold">Status</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-sand-200">
            {loading ? (
              <tr><td colSpan={6} className="px-6 py-10 text-center text-sand-600">Loading…</td></tr>
            ) : filings.length === 0 ? (
              <tr><td colSpan={6} className="px-6 py-14 text-center">
                <FileTextIcon size={36} weight="duotone" className="mx-auto text-olive-600 mb-2" />
                <div className="text-sand-700">No filings yet.</div>
              </td></tr>
            ) : filings.map((f) => (
              <tr key={f.filing_id} className="hover:bg-sand-50" data-testid={`filing-row-${f.filing_id}`}>
                <td className="px-6 py-4 font-semibold text-olive-900">BIR {f.form_type}</td>
                <td className="px-6 py-4 text-sand-800">{f.period}</td>
                <td className="px-6 py-4 text-sand-700">{new Date(f.generated_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 text-right font-display font-bold text-olive-900 tabular-nums">{formatPHP(f.computed?.tax_payable)}</td>
                <td className="px-6 py-4">
                  <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold tracking-wide ${
                    f.status === "submitted" ? "bg-sage-100 text-olive-800" : "bg-amber-100 text-amber-800"
                  }`}>
                    {f.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <Button size="sm" variant="ghost" onClick={() => setOpen(f)} data-testid={`view-filing-${f.filing_id}`} className="text-olive-700 hover:bg-sand-100">
                    <EyeIcon size={16} /> View
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={!!open} onOpenChange={() => setOpen(null)}>
        <DialogContent className="max-w-2xl bg-white">
          <DialogHeader>
            <DialogTitle className="font-display text-olive-900 text-2xl">
              BIR {open?.form_type} · {open?.period}
            </DialogTitle>
          </DialogHeader>
          {open && (
            <div className="space-y-4">
              <div className="text-sm text-sand-700">Generated {new Date(open.generated_at).toLocaleString()}</div>
              <div className="bg-sand-100 rounded-md p-4">
                <div className="text-xs uppercase tracking-widest text-olive-700 font-bold">Method</div>
                <div className="text-olive-900 font-semibold">{open.computed?.method}</div>
              </div>
              <table className="w-full text-sm">
                <tbody className="divide-y divide-sand-200">
                  {open.computed?.field_map && Object.entries(open.computed.field_map).map(([k, v]) => (
                    <tr key={k}>
                      <td className="py-2 pr-4 text-sand-800">{k}</td>
                      <td className="py-2 text-right font-semibold text-olive-900 tabular-nums">
                        {typeof v === "number" ? formatPHP(v) : v}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
