import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import api, { formatPHP, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from "@/components/ui/tabs";
import {
  CurrencyCircleDollarIcon, UsersIcon, FileTextIcon, TrendDownIcon, ChartLineUpIcon,
  GearSixIcon, CheckCircleIcon,
} from "@phosphor-icons/react";

export default function Admin() {
  const [metrics, setMetrics] = useState(null);
  const [users, setUsers] = useState([]);
  const [rules, setRules] = useState([]);

  const load = async () => {
    const [m, u, r] = await Promise.all([
      api.get("/admin/metrics"),
      api.get("/admin/users"),
      api.get("/admin/bir-rules"),
    ]);
    setMetrics(m.data);
    setUsers(u.data);
    setRules(r.data);
  };

  useEffect(() => { load(); }, []);

  return (
    <AppLayout>
      <div className="mb-10">
        <div className="text-xs tracking-[0.25em] uppercase font-bold text-terracotta-600 mb-3">Founder console</div>
        <h1 className="font-display font-bold text-olive-900 text-3xl lg:text-5xl tracking-tight">Admin</h1>
        <p className="mt-3 text-sand-700 text-lg max-w-2xl">MRR, churn, users, and editable BIR rules. Operate without founder dependency.</p>
      </div>

      <Tabs defaultValue="metrics" className="space-y-8">
        <TabsList className="bg-sand-100 border border-sand-300">
          <TabsTrigger value="metrics" data-testid="admin-tab-metrics" className="data-[state=active]:bg-olive-600 data-[state=active]:text-white">Metrics</TabsTrigger>
          <TabsTrigger value="users" data-testid="admin-tab-users" className="data-[state=active]:bg-olive-600 data-[state=active]:text-white">Users</TabsTrigger>
          <TabsTrigger value="rules" data-testid="admin-tab-rules" className="data-[state=active]:bg-olive-600 data-[state=active]:text-white">BIR Rules</TabsTrigger>
        </TabsList>

        <TabsContent value="metrics">
          {metrics ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Stat icon={CurrencyCircleDollarIcon} label="MRR" value={formatPHP(metrics.mrr_php)} sub={`${metrics.active_subscribers} active subs`} testid="admin-stat-mrr" />
              <Stat icon={TrendDownIcon} label="Churn rate" value={`${metrics.churn_rate_pct}%`} sub={`${metrics.canceled_subscribers} canceled`} testid="admin-stat-churn" />
              <Stat icon={UsersIcon} label="Total users" value={metrics.total_users} sub={`${metrics.new_users_30d} new in 30d`} testid="admin-stat-users" />
              <Stat icon={FileTextIcon} label="Total filings" value={metrics.total_filings} sub="Lifetime BIR forms generated" testid="admin-stat-filings" />
              <Stat icon={ChartLineUpIcon} label="Active subscribers" value={metrics.active_subscribers} sub="Currently paying" testid="admin-stat-active" />
              <Stat icon={CheckCircleIcon} label="Retention proxy" value={`${(100 - metrics.churn_rate_pct).toFixed(1)}%`} sub="Target: 80%+ monthly" testid="admin-stat-retention" />
            </div>
          ) : <div className="text-sand-700">Loading metrics…</div>}
        </TabsContent>

        <TabsContent value="users">
          <div className="bg-white border border-sand-200 rounded-2xl overflow-hidden">
            <table className="w-full text-sm" data-testid="admin-users-table">
              <thead className="bg-sand-100 text-olive-900">
                <tr>
                  <th className="text-left px-6 py-4 font-display font-semibold">Email</th>
                  <th className="text-left px-6 py-4 font-display font-semibold">Name</th>
                  <th className="text-left px-6 py-4 font-display font-semibold">Provider</th>
                  <th className="text-left px-6 py-4 font-display font-semibold">Plan</th>
                  <th className="text-left px-6 py-4 font-display font-semibold">Status</th>
                  <th className="text-left px-6 py-4 font-display font-semibold">Joined</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-sand-200">
                {users.map(u => (
                  <tr key={u.user_id}>
                    <td className="px-6 py-3 text-olive-900 font-medium">{u.email}</td>
                    <td className="px-6 py-3 text-sand-800">{u.name}</td>
                    <td className="px-6 py-3 text-sand-700">{u.auth_provider}</td>
                    <td className="px-6 py-3 text-sand-700">{u.subscription_plan || "—"}</td>
                    <td className="px-6 py-3"><span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-sage-100 text-olive-900">{u.subscription_status}</span></td>
                    <td className="px-6 py-3 text-sand-700 text-xs">{u.created_at?.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="rules">
          <div className="space-y-3">
            {rules.map(r => <RuleRow key={r.rule_key} rule={r} onSaved={load} />)}
          </div>
        </TabsContent>
      </Tabs>
    </AppLayout>
  );
}

function Stat({ icon: Icon, label, value, sub, testid }) {
  return (
    <div className="bg-white border border-sand-200 rounded-2xl p-6" data-testid={testid}>
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs tracking-[0.2em] uppercase font-bold text-terracotta-600">{label}</div>
        <Icon size={22} weight="duotone" className="text-olive-600" />
      </div>
      <div className="font-display text-4xl font-bold text-olive-900 tabular-nums">{value}</div>
      <div className="text-sm text-sand-600 mt-1">{sub}</div>
    </div>
  );
}

function RuleRow({ rule, onSaved }) {
  const [val, setVal] = useState(rule.rule_value);
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/admin/bir-rules/${rule.rule_key}`, { rule_value: parseFloat(val) });
      toast.success(`Updated ${rule.rule_key}`);
      onSaved();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="bg-white border border-sand-200 rounded-xl p-5 flex flex-col md:flex-row md:items-center gap-4">
      <div className="flex-1">
        <div className="font-display font-semibold text-olive-900">{rule.rule_key}</div>
        <div className="text-xs text-sand-700 mt-1">{rule.description}</div>
      </div>
      <Input
        type="number" step="any" value={val}
        onChange={(e) => setVal(e.target.value)}
        data-testid={`rule-input-${rule.rule_key}`}
        className="w-44 bg-white border-sand-300 tabular-nums"
      />
      <Button onClick={save} disabled={saving} data-testid={`rule-save-${rule.rule_key}`} className="bg-olive-600 hover:bg-olive-700 text-white">
        {saving ? "..." : "Save"}
      </Button>
    </div>
  );
}
