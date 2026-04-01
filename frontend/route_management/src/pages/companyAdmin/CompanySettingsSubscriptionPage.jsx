import { useMemo } from "react";
import { Link } from "react-router-dom";
import { CalendarClock, ShieldCheck } from "lucide-react";

import { useGetCompanyProfileQuery } from "../../features/billing/billingApi";

export default function CompanySettingsSubscriptionPage() {
  const { data: profile, isLoading } = useGetCompanyProfileQuery();

  const subscription = profile?.subscription;
  const queuedPlanName = subscription?.queued_plan_name || null;
  const queuedPlanCode = subscription?.queued_plan_code || null;
  const queuedPlanEffectiveAt = subscription?.queued_plan_effective_at || null;
  const statusLabel = useMemo(() => {
    if (!subscription) return "Not Available";
    return subscription.is_active ? "Active" : "Expired";
  }, [subscription]);

  return (
    <div className="p-8">
      <div className="max-w-3xl space-y-6">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Subscription</h1>
          <p className="text-slate-500 mt-1">Review current plan and renew access.</p>
        </div>

        {isLoading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">Loading subscription...</div>
        ) : (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 space-y-5">
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-[11px] font-black uppercase tracking-wider text-slate-500">Plan</p>
                <p className="text-lg font-black text-slate-900 mt-1">{subscription?.plan_name || "-"}</p>
                <p className="text-xs text-slate-500">{subscription?.plan_code || "-"}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-[11px] font-black uppercase tracking-wider text-slate-500">Status</p>
                <p className="text-lg font-black text-slate-900 mt-1">{statusLabel}</p>
                <p className="text-xs text-slate-500">Amount Paid: INR {subscription?.amount_paid || "0.00"}</p>
              </div>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <div className="inline-flex items-center gap-2 font-black uppercase tracking-wider text-xs">
                <CalendarClock size={14} /> End Date
              </div>
              <p className="mt-1 font-semibold">
                {subscription?.end_date ? new Date(subscription.end_date).toLocaleString() : "-"}
              </p>
            </div>

            {queuedPlanName ? (
              <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
                <p className="text-[11px] font-black uppercase tracking-wider text-blue-700">Next Plan Scheduled</p>
                <p className="mt-1 text-base font-black text-blue-900">{queuedPlanName}</p>
                <p className="text-xs text-blue-700">{queuedPlanCode || "-"}</p>
                <p className="mt-1 text-xs text-blue-700">
                  Starts: {queuedPlanEffectiveAt ? new Date(queuedPlanEffectiveAt).toLocaleString() : "-"}
                </p>
              </div>
            ) : null}

            <div className="flex justify-end">
              <Link
                to="/company/renew-subscription"
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
              >
                <ShieldCheck size={14} /> Renew / Upgrade
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
