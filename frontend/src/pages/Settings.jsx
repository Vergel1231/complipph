import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import api, { formatPHP, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { CreditCardIcon, BuildingsIcon, UserIcon } from "@phosphor-icons/react";

export default function Settings() {
  const { user, refresh } = useAuth();
  const [profile, setProfile] = useState(null);
  const [sub, setSub] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const [p, s] = await Promise.all([
        api.get("/business/profile"),
        api.get("/billing/subscription"),
      ]);
      setProfile(p.data);
      setSub(s.data);
    })();
  }, []);

  const save = async () => {
    setBusy(true);
    try {
      await api.post("/business/profile", profile);
      await refresh();
      toast.success("Profile saved.");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const cancelSub = async () => {
    if (!window.confirm("Cancel subscription? You will lose access to filing history.")) return;
    await api.post("/billing/cancel");
    await refresh();
    setSub(null);
    toast.success("Subscription canceled.");
  };

  return (
    <AppLayout>
      <div className="mb-10">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Settings</div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">Account & Business</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl">
        <div className="bg-white border border-sand-200 rounded-2xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <UserIcon size={24} weight="duotone" className="text-olive-600" />
            <h2 className="font-display font-bold text-olive-900 text-xl">Account</h2>
          </div>
          <div className="space-y-3 text-sm">
            <div><span className="text-sand-600">Name:</span> <strong className="text-olive-900">{user?.name}</strong></div>
            <div><span className="text-sand-600">Email:</span> <strong className="text-olive-900">{user?.email}</strong></div>
            <div><span className="text-sand-600">Auth:</span> <strong className="text-olive-900">{user?.auth_provider}</strong></div>
            <div><span className="text-sand-600">Role:</span> <strong className="text-olive-900">{user?.role}</strong></div>
          </div>
        </div>

        <div className="bg-white border border-sand-200 rounded-2xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <CreditCardIcon size={24} weight="duotone" className="text-olive-600" />
            <h2 className="font-display font-bold text-olive-900 text-xl">Subscription</h2>
          </div>
          {sub ? (
            <div className="space-y-3">
              <div className="text-sm">
                <div><span className="text-sand-600">Plan:</span> <strong className="text-olive-900">{sub.plan}</strong></div>
                <div><span className="text-sand-600">Amount:</span> <strong className="text-olive-900">{formatPHP(sub.amount_php)} / month</strong></div>
                <div><span className="text-sand-600">Status:</span> <strong className="text-olive-900">{sub.status}</strong></div>
                <div><span className="text-sand-600">Provider:</span> <strong className="text-olive-900">{sub.provider} (PayMongo swap-ready)</strong></div>
              </div>
              <Button variant="outline" onClick={cancelSub} data-testid="cancel-subscription-button" className="border-terracotta-500 text-terracotta-700 hover:bg-terracotta-50">
                Cancel subscription
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sand-700 text-sm">No active subscription. Subscribe to keep your filing history & deadline reminders.</p>
              <Button onClick={() => window.location.href = "/pricing"} data-testid="go-to-pricing-button" className="bg-olive-600 hover:bg-olive-700 text-white">
                See plans
              </Button>
            </div>
          )}
        </div>

        {profile && (
          <div className="bg-white border border-sand-200 rounded-2xl p-8 lg:col-span-2">
            <div className="flex items-center gap-3 mb-6">
              <BuildingsIcon size={24} weight="duotone" className="text-olive-600" />
              <h2 className="font-display font-bold text-olive-900 text-xl">Business profile</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <Label className="text-olive-900 font-semibold">Legal name</Label>
                <Input value={profile.legal_name || ""} onChange={(e) => setProfile({ ...profile, legal_name: e.target.value })} data-testid="settings-legal-name-input" className="mt-2 bg-white border-sand-300 py-6" />
              </div>
              <div>
                <Label className="text-olive-900 font-semibold">Trade name</Label>
                <Input value={profile.trade_name || ""} onChange={(e) => setProfile({ ...profile, trade_name: e.target.value })} data-testid="settings-trade-name-input" className="mt-2 bg-white border-sand-300 py-6" />
              </div>
              <div>
                <Label className="text-olive-900 font-semibold">TIN</Label>
                <Input value={profile.tin || ""} onChange={(e) => setProfile({ ...profile, tin: e.target.value })} data-testid="settings-tin-input" className="mt-2 bg-white border-sand-300 py-6 tabular-nums" />
              </div>
              <div>
                <Label className="text-olive-900 font-semibold">RDO Code</Label>
                <Input value={profile.rdo_code || ""} onChange={(e) => setProfile({ ...profile, rdo_code: e.target.value })} data-testid="settings-rdo-input" className="mt-2 bg-white border-sand-300 py-6 tabular-nums" />
              </div>
              <div>
                <Label className="text-olive-900 font-semibold">Taxpayer Classification</Label>
                <select
                  value={profile.taxpayer_classification}
                  onChange={(e) => setProfile({ ...profile, taxpayer_classification: e.target.value })}
                  data-testid="settings-classification-select"
                  className="mt-2 w-full rounded-md border border-sand-300 bg-white px-3 py-3 text-olive-900"
                >
                  <option value="8_percent_flat">8% Flat Tax</option>
                  <option value="graduated">Graduated Rates</option>
                </select>
              </div>
              <label className="flex items-center gap-3 mt-7">
                <input type="checkbox" checked={profile.is_vat_registered} onChange={(e) => setProfile({ ...profile, is_vat_registered: e.target.checked })} data-testid="settings-vat-checkbox" className="h-5 w-5 rounded border-sand-400 text-olive-600" />
                <span className="text-olive-900 text-sm font-medium">VAT-registered</span>
              </label>
            </div>
            <div className="mt-8">
              <Button onClick={save} disabled={busy} data-testid="settings-save-button" className="bg-olive-600 hover:bg-olive-700 text-white px-6 py-5">
                {busy ? "Saving…" : "Save changes"}
              </Button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
