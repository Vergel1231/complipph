import { useState } from "react";
import api, { formatPHP, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { LockKeyIcon, CreditCardIcon } from "@phosphor-icons/react";

const PAYMONGO_API = "https://api.paymongo.com/v1";

/**
 * PayMongo card-collection modal.
 * Tokenizes the card directly with PayMongo using the public key (PCI-safe),
 * then asks our backend to attach the payment_method to the payment_intent.
 */
export default function PayMongoCheckout({ open, onClose, session, publicKey, onSuccess }) {
  const [busy, setBusy] = useState(false);
  const [card, setCard] = useState({ number: "", exp_month: "", exp_year: "", cvc: "" });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!publicKey) {
      toast.error("PayMongo public key missing.");
      return;
    }
    setBusy(true);
    try {
      // Step 1 — tokenize card directly with PayMongo using public key
      const auth = "Basic " + btoa(publicKey + ":");
      const pmRes = await fetch(`${PAYMONGO_API}/payment_methods`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": auth },
        body: JSON.stringify({
          data: { attributes: {
            type: "card",
            details: {
              card_number: card.number.replace(/\s+/g, ""),
              exp_month: parseInt(card.exp_month, 10),
              exp_year: parseInt(card.exp_year, 10),
              cvc: card.cvc,
            },
            billing: { email: session.email || undefined, name: session.name || undefined },
          }},
        }),
      });
      const pmJson = await pmRes.json();
      if (!pmRes.ok) {
        const detail = pmJson?.errors?.[0]?.detail || "Card tokenization failed.";
        throw new Error(detail);
      }
      const payment_method_id = pmJson.data.id;

      // Step 2 — backend attaches payment method to the payment intent
      const attachRes = await api.post("/billing/attach-payment", {
        payment_intent_id: session.payment_intent_id,
        payment_method_id,
        client_key: session.client_key,
      });
      const data = attachRes.data;

      if (data.next_action_url) {
        // 3DS authentication required — redirect customer
        window.location.href = data.next_action_url;
        return;
      }
      if (data.status === "succeeded" || data.status === "processing") {
        toast.success("Payment processed. Subscription activating…");
        onSuccess?.();
        return;
      }
      toast.message(`Payment status: ${data.status}`);
      onSuccess?.();
    } catch (err) {
      toast.error(err.message || formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-white max-w-md" data-testid="paymongo-checkout-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-olive-900 text-2xl flex items-center gap-2">
            <CreditCardIcon size={22} weight="duotone" />
            {formatPHP(session?.amount_php)} / month
          </DialogTitle>
          <DialogDescription className="text-sand-700">
            {session?.plan_name} · You'll be charged immediately and on the same day each month.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div>
            <Label className="text-olive-900 font-semibold">Card number</Label>
            <Input
              required value={card.number} onChange={(e) => setCard({ ...card, number: e.target.value })}
              placeholder="4343 4343 4343 4345" inputMode="numeric"
              data-testid="paymongo-card-number"
              className="mt-1 bg-white border-sand-300 py-5 tabular-nums"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label className="text-olive-900 font-semibold">Exp month</Label>
              <Input required value={card.exp_month} onChange={(e) => setCard({ ...card, exp_month: e.target.value })}
                placeholder="MM" maxLength={2} inputMode="numeric"
                data-testid="paymongo-card-exp-month"
                className="mt-1 bg-white border-sand-300 py-5 tabular-nums" />
            </div>
            <div>
              <Label className="text-olive-900 font-semibold">Exp year</Label>
              <Input required value={card.exp_year} onChange={(e) => setCard({ ...card, exp_year: e.target.value })}
                placeholder="YYYY" maxLength={4} inputMode="numeric"
                data-testid="paymongo-card-exp-year"
                className="mt-1 bg-white border-sand-300 py-5 tabular-nums" />
            </div>
            <div>
              <Label className="text-olive-900 font-semibold">CVC</Label>
              <Input required value={card.cvc} onChange={(e) => setCard({ ...card, cvc: e.target.value })}
                placeholder="123" maxLength={4} inputMode="numeric"
                data-testid="paymongo-card-cvc"
                className="mt-1 bg-white border-sand-300 py-5 tabular-nums" />
            </div>
          </div>
          <Button type="submit" disabled={busy}
            data-testid="paymongo-pay-button"
            className="w-full bg-olive-600 hover:bg-olive-700 text-white py-6 mt-2">
            {busy ? "Processing…" : `Subscribe · ${formatPHP(session?.amount_php)}/mo`}
          </Button>
          <p className="text-xs text-sand-600 flex items-center gap-1.5 justify-center">
            <LockKeyIcon size={12} /> Card details are sent directly to PayMongo. We never see them.
          </p>
        </form>
      </DialogContent>
    </Dialog>
  );
}
