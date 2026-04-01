import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Boxes,
  CarFront,
  Map,
  Navigation,
  RefreshCw,
  Route,
  ShieldAlert,
  Store,
  Truck,
  Users,
} from "lucide-react";
import { toast } from "react-toastify";

import { useGetDashboardOverviewQuery } from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage } from "../../utils/adminUi";

const toneClasses = {
  blue: "bg-blue-600",
  emerald: "bg-emerald-600",
  rose: "bg-rose-600",
  amber: "bg-amber-500",
};

function DashboardCard({ label, value, helper, icon: Icon, tone = "blue" }) {
  return (
    <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">{label}</p>
          <h3 className="mt-2 text-3xl font-black tracking-tight text-slate-900">{value}</h3>
          {helper ? <p className="mt-2 text-sm font-semibold text-slate-500">{helper}</p> : null}
        </div>
        <div className={`rounded-2xl p-3 text-white ${toneClasses[tone] || toneClasses.blue}`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
}

function StatusPill({ text, tone = "slate" }) {
  const styles = {
    slate: "bg-slate-100 text-slate-600",
    blue: "bg-blue-50 text-blue-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    rose: "bg-rose-50 text-rose-700",
  };
  return (
    <span className={`rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${styles[tone] || styles.slate}`}>
      {text}
    </span>
  );
}

function SectionCard({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={`rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm ${className}`}>
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-black tracking-tight text-slate-900">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm font-medium text-slate-500">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function AssignmentList({ items = [], emptyText, showStartedAt = false }) {
  if (!items.length) {
    return <p className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm font-medium text-slate-500">{emptyText}</p>;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="truncate text-sm font-black text-slate-900">{item.route_name}</p>
              <p className="mt-1 text-sm font-semibold text-slate-600">
                {item.driver_name} • {item.vehicle_name}
              </p>
              <p className="mt-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
                {showStartedAt ? "Started" : "Scheduled"}{" "}
                {new Date(showStartedAt ? item.started_at : item.scheduled_at).toLocaleString()}
              </p>
            </div>
            <StatusPill
              text={item.status.replaceAll("_", " ")}
              tone={
                item.status === "COMPLETED"
                  ? "emerald"
                  : item.status === "CANCELLED"
                    ? "rose"
                    : item.status === "IN_PROGRESS"
                      ? "blue"
                      : "amber"
              }
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function MetricBar({ label, value, total, tone = "blue" }) {
  const percentage = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-slate-600">{label}</span>
        <span className="text-sm font-black text-slate-900">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div
          className={`h-2 rounded-full ${toneClasses[tone] || toneClasses.blue}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function TrendBars({ items = [] }) {
  const maxAssigned = Math.max(1, ...items.map((item) => item.assigned || 0));
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.date} className="grid grid-cols-[72px_1fr_auto] items-center gap-4">
          <span className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">{item.label}</span>
          <div className="space-y-2">
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-blue-600" style={{ width: `${Math.max(8, (item.assigned / maxAssigned) * 100)}%` }} />
            </div>
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-emerald-500" style={{ width: `${Math.max(8, (item.completed / maxAssigned) * 100)}%` }} />
            </div>
          </div>
          <div className="text-right text-xs font-bold text-slate-500">
            <div>{item.assigned} assigned</div>
            <div>{item.completed} completed</div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CompanyAdminDashboardPage() {
  const {
    data,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useGetDashboardOverviewQuery();

  const errorMessage = extractApiErrorMessage(error);

  useEffect(() => {
    if (errorMessage) {
      toast.error(errorMessage, { toastId: `company-dashboard-error-${errorMessage}` });
    }
  }, [errorMessage]);

  const cards = useMemo(
    () => [
      {
        label: "Drivers",
        value: data?.kpis?.drivers ?? 0,
        helper: `${data?.kpis?.available_drivers ?? 0} available now`,
        icon: Users,
        tone: "blue",
      },
      {
        label: "Vehicles",
        value: data?.kpis?.vehicles ?? 0,
        helper: `${data?.kpis?.available_vehicles ?? 0} ready to dispatch`,
        icon: CarFront,
        tone: "emerald",
      },
      {
        label: "Assignments Today",
        value: data?.kpis?.assignments_today ?? 0,
        helper: `${data?.kpis?.completed_today ?? 0} completed today`,
        icon: Navigation,
        tone: "amber",
      },
      {
        label: "Active Runs",
        value: data?.kpis?.active_runs ?? 0,
        helper: "Trips currently in progress",
        icon: Truck,
        tone: "blue",
      },
      {
        label: "Network",
        value: data?.kpis?.shops ?? 0,
        helper: `${data?.kpis?.routes ?? 0} routes configured`,
        icon: Store,
        tone: "emerald",
      },
      {
        label: "Inventory",
        value: data?.kpis?.products ?? 0,
        helper: `${data?.resources?.inventory?.zero_stock ?? 0} out of stock`,
        icon: Boxes,
        tone: "rose",
      },
    ],
    [data]
  );

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <section className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-950 px-6 py-7 text-white shadow-xl">
        <div className="absolute right-0 top-0 h-56 w-56 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute bottom-0 left-0 h-44 w-44 rounded-full bg-emerald-500/10 blur-3xl" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.22em] text-blue-200">Operations Command Center</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight lg:text-4xl">
              {data?.header?.company_name || "Company"} dashboard
            </h1>
            <p className="mt-3 max-w-2xl text-sm font-medium text-slate-300">
              Track route execution, assignment load, resource readiness, and operational attention points from one place.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-black text-white backdrop-blur-sm transition hover:bg-white/15"
            >
              <RefreshCw size={16} className={isFetching ? "animate-spin" : ""} />
              Refresh
            </button>
            <Link
              to="/company/schedule"
              className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-black text-slate-900 transition hover:bg-slate-100"
            >
              Assign routes
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/company/live-tracking"
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-black text-white backdrop-blur-sm transition hover:bg-white/15"
            >
              <Map size={16} />
              Live tracking
            </Link>
            <Link
              to="/company/assistant"
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-black text-white backdrop-blur-sm transition hover:bg-white/15"
            >
              <Bot size={16} />
              AI assistant
            </Link>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <DashboardCard key={card.label} {...card} value={isLoading ? "..." : card.value} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.55fr_1fr]">
        <SectionCard
          title="Operational Snapshot"
          subtitle="The most important work happening right now and what’s coming next."
          action={<StatusPill text={`${data?.kpis?.alerts ?? 0} alerts`} tone={(data?.kpis?.alerts ?? 0) > 0 ? "amber" : "emerald"} />}
        >
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black uppercase tracking-[0.18em] text-slate-400">Active Runs</h3>
                <Link to="/company/live-tracking" className="text-xs font-black uppercase tracking-[0.14em] text-blue-600">
                  View live
                </Link>
              </div>
              <AssignmentList
                items={data?.operations?.active_assignments}
                emptyText="No routes are actively running right now."
                showStartedAt
              />
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black uppercase tracking-[0.18em] text-slate-400">Upcoming Assignments</h3>
                <Link to="/company/schedule" className="text-xs font-black uppercase tracking-[0.14em] text-blue-600">
                  Manage
                </Link>
              </div>
              <AssignmentList
                items={data?.operations?.upcoming_assignments}
                emptyText="No upcoming assignments are scheduled yet."
              />
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="Attention Needed"
          subtitle="Immediate issues that can block route execution or fulfillment."
          action={<ShieldAlert size={18} className="text-slate-400" />}
        >
          <div className="space-y-3">
            {!data?.alerts?.length ? (
              <div className="rounded-2xl border border-dashed border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">
                No operational alerts right now. Your resources and schedules look healthy.
              </div>
            ) : null}
            {(data?.alerts || []).map((alert) => (
              <div key={alert.id} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 rounded-xl p-2 ${alert.severity === "critical" ? "bg-rose-100 text-rose-600" : "bg-amber-100 text-amber-600"}`}>
                    <AlertTriangle size={16} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-black text-slate-900">{alert.title}</p>
                    <p className="mt-1 text-sm font-medium text-slate-500">{alert.description}</p>
                    <Link
                      to={alert.action_to}
                      className="mt-3 inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-blue-600"
                    >
                      {alert.action_label}
                      <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_1fr]">
        <SectionCard
          title="Resource Readiness"
          subtitle="How your people, fleet, and inventory are currently distributed."
        >
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <h3 className="text-sm font-black uppercase tracking-[0.18em] text-slate-400">Drivers</h3>
              <MetricBar label="Available" value={data?.resources?.drivers?.available ?? 0} total={data?.kpis?.drivers ?? 0} tone="blue" />
              <MetricBar label="In Route" value={data?.resources?.drivers?.in_route ?? 0} total={data?.kpis?.drivers ?? 0} tone="emerald" />
              <MetricBar label="On Leave" value={data?.resources?.drivers?.on_leave ?? 0} total={data?.kpis?.drivers ?? 0} tone="amber" />
              <MetricBar label="Unassigned" value={data?.resources?.drivers?.unassigned ?? 0} total={data?.kpis?.drivers ?? 0} tone="rose" />
            </div>
            <div className="space-y-4">
              <h3 className="text-sm font-black uppercase tracking-[0.18em] text-slate-400">Fleet & Network</h3>
              <MetricBar label="Vehicles Available" value={data?.resources?.vehicles?.available ?? 0} total={data?.kpis?.vehicles ?? 0} tone="blue" />
              <MetricBar label="Vehicles On Route" value={data?.resources?.vehicles?.on_route ?? 0} total={data?.kpis?.vehicles ?? 0} tone="emerald" />
              <MetricBar label="Low Stock Products" value={data?.resources?.inventory?.low_stock ?? 0} total={data?.kpis?.products ?? 0} tone="amber" />
              <MetricBar label="Zero Stock Products" value={data?.resources?.inventory?.zero_stock ?? 0} total={data?.kpis?.products ?? 0} tone="rose" />
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="7-Day Assignment Trend"
          subtitle="Quick pulse on schedule load and delivery completion."
        >
          <TrendBars items={data?.trend || []} />
          <div className="mt-5 flex flex-wrap gap-3 text-xs font-bold text-slate-500">
            <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-blue-600" />Assigned</span>
            <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />Completed</span>
          </div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_0.9fr]">
        <SectionCard
          title="Assignment Status"
          subtitle="Current balance of scheduled work across the company."
        >
          <div className="space-y-4">
            {(data?.assignment_status || []).map((item) => {
              const total = Math.max(
                1,
                ...(data?.assignment_status || []).map((entry) => entry.count || 0)
              );
              return (
                <div key={item.key} className="grid grid-cols-[120px_1fr_auto] items-center gap-4">
                  <span className="text-sm font-semibold text-slate-600">{item.label}</span>
                  <div className="h-3 rounded-full bg-slate-100">
                    <div
                      className={`h-3 rounded-full ${toneClasses[item.tone] || toneClasses.blue}`}
                      style={{ width: `${Math.max(item.count ? 12 : 0, ((item.count || 0) / total) * 100)}%` }}
                    />
                  </div>
                  <span className="text-sm font-black text-slate-900">{item.count}</span>
                </div>
              );
            })}
          </div>
        </SectionCard>

        <SectionCard
          title="Recent Activity"
          subtitle="Latest assignment changes and scheduling updates."
        >
          <div className="space-y-3">
            {(data?.operations?.recent_activity || []).length ? (
              data.operations.recent_activity.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-black text-slate-900">
                        {item.driver_name} assigned to {item.route_name}
                      </p>
                      <p className="mt-1 text-sm font-medium text-slate-500">Vehicle: {item.vehicle_name}</p>
                      <p className="mt-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
                        Updated {new Date(item.updated_at).toLocaleString()}
                      </p>
                    </div>
                    <StatusPill
                      text={item.status.replaceAll("_", " ")}
                      tone={
                        item.status === "COMPLETED"
                          ? "emerald"
                          : item.status === "CANCELLED"
                            ? "rose"
                            : item.status === "IN_ROUTE"
                              ? "amber"
                              : "blue"
                      }
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="rounded-2xl border border-dashed border-slate-200 p-4 text-sm font-medium text-slate-500">
                No recent assignment activity recorded yet.
              </p>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
