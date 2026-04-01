import { Link } from "react-router-dom";
import { useEffect } from "react";
import {
  ArrowUpRight,
  Users,
  Store,
  Building2,
  Activity,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { toast } from "react-toastify";
import {
  useGetAnalyticsQuery,
  useGetMonitoringQuery,
  useGetOverviewQuery,
} from "../../features/admin/adminApi";
import AdminShell from "../../components/AdminShell";
import { extractApiErrorMessage, formatCurrency } from "../../utils/adminUi";

export default function MainAdminDashboard() {
  const {
    data: overview,
    isLoading: isLoadingOverview,
    isFetching: isFetchingOverview,
    isError: isOverviewError,
    error: overviewError,
    refetch: refetchOverview,
  } = useGetOverviewQuery(undefined, {
    selectFromResult: ({ data, isLoading, isFetching, isError, error, refetch }) => ({
      data,
      isLoading,
      isFetching,
      isError,
      error,
      refetch,
    }),
  });

  const {
    data: analytics,
    isLoading: isLoadingAnalytics,
    isFetching: isFetchingAnalytics,
    isError: isAnalyticsError,
    error: analyticsError,
    refetch: refetchAnalytics,
  } = useGetAnalyticsQuery(undefined, {
    selectFromResult: ({ data, isLoading, isFetching, isError, error, refetch }) => ({
      data,
      isLoading,
      isFetching,
      isError,
      error,
      refetch,
    }),
  });

  const {
    data: monitoring,
    isLoading: isLoadingMonitoring,
    isFetching: isFetchingMonitoring,
    isError: isMonitoringError,
    error: monitoringError,
    refetch: refetchMonitoring,
  } = useGetMonitoringQuery(undefined, {
    selectFromResult: ({ data, isLoading, isFetching, isError, error, refetch }) => ({
      data,
      isLoading,
      isFetching,
      isError,
      error,
      refetch,
    }),
  });

  const isLoading = isLoadingOverview || isLoadingAnalytics || isLoadingMonitoring;
  const isRefreshing = isFetchingOverview || isFetchingAnalytics || isFetchingMonitoring;

  const errorMessage =
    extractApiErrorMessage(overviewError) ||
    extractApiErrorMessage(analyticsError) ||
    extractApiErrorMessage(monitoringError);

  const hasError = isOverviewError || isAnalyticsError || isMonitoringError;

  useEffect(() => {
    if (hasError && errorMessage) {
      toast.error(errorMessage, { toastId: `main-dashboard-error-${errorMessage}` });
    }
  }, [hasError, errorMessage]);

  const kpiCards = [
    { label: "Total Companies", value: overview?.total_companies ?? 0, icon: Building2, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Active Companies", value: overview?.active_companies ?? 0, icon: Activity, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Total Drivers", value: overview?.total_drivers ?? 0, icon: Users, color: "text-indigo-600", bg: "bg-indigo-50" },
    { label: "Total Shops", value: overview?.total_shops ?? 0, icon: Store, color: "text-amber-600", bg: "bg-amber-50" },
  ];

  const revenueLine = analytics?.revenue_line_chart || [];
  const maxRevenuePoint = Math.max(...revenueLine.map((item) => Number(item.revenue || 0)), 1);

  return (
    <AdminShell>
      <div className="space-y-8 animate-in fade-in duration-500">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight">System Overview</h1>
            <p className="text-slate-500 font-medium mt-1">Live admin metrics, subscription growth, and monthly revenue.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                refetchOverview();
                refetchAnalytics();
                refetchMonitoring();
              }}
              className="px-5 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-bold text-slate-700 hover:bg-slate-50 transition-all flex items-center gap-2"
            >
              <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} /> Refresh
            </button>
            <Link to="/admin/companies" className="px-5 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-bold hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all flex items-center gap-2">
              View Companies
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {kpiCards.map((card) => (
            <div key={card.label} className="bg-white rounded-[2rem] border border-slate-100 p-6 shadow-sm hover:shadow-md transition-shadow group">
              <div className="flex items-center justify-between mb-4">
                <div className={`${card.bg} ${card.color} p-3 rounded-2xl group-hover:scale-110 transition-transform`}>
                  <card.icon size={20} />
                </div>
                <ArrowUpRight size={18} className="text-slate-300" />
              </div>
              <p className="text-[11px] font-black text-slate-400 uppercase tracking-widest">{card.label}</p>
              <h3 className="text-2xl font-black text-slate-900 mt-1">
                {isLoading ? <span className="animate-pulse">...</span> : card.value}
              </h3>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 bg-white rounded-[2rem] border border-slate-100 p-8 shadow-sm">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-lg font-black text-slate-900 tracking-tight">Monthly Revenue (Companies)</h2>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-tighter">Successful payments only</p>
              </div>
            </div>

            {revenueLine.length ? (
              <div className="space-y-5">
                {revenueLine.map((point) => {
                  const revenue = Number(point.revenue || 0);
                  return (
                    <div key={point.month} className="group">
                      <div className="flex justify-between items-end mb-2">
                        <span className="text-xs font-bold text-slate-600">{point.month}</span>
                        <span className="text-xs font-black text-slate-900">{formatCurrency(revenue)}</span>
                      </div>
                      <div className="h-3 w-full bg-slate-50 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600 rounded-full transition-all duration-1000 group-hover:bg-blue-500"
                          style={{ width: `${(revenue / maxRevenuePoint) * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No revenue data found.</p>
            )}
          </div>

          <div className="bg-slate-900 rounded-[2rem] p-8 text-white shadow-xl shadow-slate-200 relative overflow-hidden">
            <div className="absolute top-[-20px] right-[-20px] h-40 w-40 bg-blue-500/10 blur-[80px] rounded-full" />
            <h2 className="text-lg font-black tracking-tight mb-6">Revenue KPIs</h2>
            <div className="space-y-6 relative z-10">
              {[
                { label: "Monthly Revenue", val: formatCurrency(overview?.monthly_revenue || 0) },
                { label: "Lifetime Revenue", val: formatCurrency(overview?.lifetime_revenue || 0) },
                { label: "MRR", val: formatCurrency(analytics?.mrr || 0) },
                { label: "ARR", val: formatCurrency(analytics?.arr || 0) },
              ].map((m) => (
                <div key={m.label} className="flex justify-between items-center border-b border-white/5 pb-4">
                  <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{m.label}</span>
                  <span className="text-lg font-black text-white">{m.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <MonitorCard title="Expiring In 7 Days" data={monitoring?.expiring_in_7_days} type="date" isLoading={isLoadingMonitoring} />
          <MonitorCard title="High Value Customers" data={monitoring?.high_value_customers} type="currency" isLoading={isLoadingMonitoring} />
          <MonitorCard title="Long Inactive" data={monitoring?.long_inactive_companies} type="date" isLoading={isLoadingMonitoring} />
        </div>
      </div>
    </AdminShell>
  );
}

function MonitorCard({ title, data, type, isLoading }) {
  return (
    <div className="bg-white rounded-[2rem] border border-slate-100 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-black text-slate-900 uppercase tracking-tighter">{title}</h3>
        <ChevronRight size={16} className="text-slate-300" />
      </div>
      {isLoading ? <p className="text-sm text-slate-500">Loading...</p> : null}
      <div className="space-y-4">
        {(data || []).slice(0, 4).map((item, i) => (
          <div key={`${item.company_id || item.company_name}-${i}`} className="flex items-center justify-between group">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-slate-50 flex items-center justify-center text-[10px] font-black text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                {item.company_name?.charAt(0)}
              </div>
              <span className="text-xs font-bold text-slate-700 truncate max-w-[120px]">{item.company_name}</span>
            </div>
            <span className="text-[10px] font-black text-slate-400">
              {type === "currency"
                ? formatCurrency(item.total_spend)
                : new Date(item.end_date || item.updated_at).toLocaleDateString()}
            </span>
          </div>
        ))}
      </div>
      {!isLoading && !(data || []).length ? <p className="text-xs text-slate-400">No records found.</p> : null}
    </div>
  );
}
