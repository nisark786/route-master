import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  Search,
  Filter,
  Plus,
  Building2,
  Users,
  Store,
  CreditCard,
  History,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
  MoreVertical,
} from "lucide-react";
import { useEffect, useMemo } from "react";
import { toast } from "react-toastify";
import AdminShell from "../../components/AdminShell";
import {
  useGetCompaniesQuery,
  useGetCompanyDetailQuery,
  useUpdateCompanyStatusMutation,
} from "../../features/admin/adminApi";
import {
  setCompanyFilters,
  setSelectedCompanyId,
} from "../../features/admin/adminSlice";
import { extractApiErrorMessage, extractApiSuccessMessage, formatCurrency } from "../../utils/adminUi";

export default function AdminCompaniesPage() {
  const dispatch = useDispatch();
  const { companyFilters, selectedCompanyId } = useSelector((state) => state.admin);
  const {
    data,
    isFetching,
    error: companiesError,
  } = useGetCompaniesQuery(companyFilters, {
    selectFromResult: ({ data, isFetching, error }) => ({ data, isFetching, error }),
  });

  const {
    data: detailData,
    isFetching: isFetchingDetail,
    error: detailError,
  } = useGetCompanyDetailQuery(selectedCompanyId, {
    skip: !selectedCompanyId,
    selectFromResult: ({ data, isFetching, error }) => ({ data, isFetching, error }),
  });

  const [updateCompanyStatus, { isLoading: isUpdatingStatus, error: updateStatusError }] =
    useUpdateCompanyStatusMutation();

  const results = data?.results || [];

  const listError = extractApiErrorMessage(companiesError);
  const detailsError = extractApiErrorMessage(detailError);
  const mutationError = extractApiErrorMessage(updateStatusError);

  const summaryMessage = useMemo(() => mutationError || detailsError || listError || "", [mutationError, detailsError, listError]);

  useEffect(() => {
    if (summaryMessage) {
      toast.error(summaryMessage, { toastId: `companies-error-${summaryMessage}` });
    }
  }, [summaryMessage]);

  const onFilterChange = (next) => {
    dispatch(setCompanyFilters({ ...next, page: 1 }));
  };

  const onStatusAction = async (action) => {
    if (!selectedCompanyId) return;
    const body = {
      action,
      reason: action === "suspend" ? "Suspended by super admin" : "Reactivated by super admin",
    };

    try {
      const response = await updateCompanyStatus({ companyId: selectedCompanyId, body }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
    } catch {
      // Error comes from RTK query state and is shown in UI.
    }
  };

  const getStatusStyle = (status) => {
    const map = {
      active: "bg-emerald-50 text-emerald-600 border-emerald-100",
      trial: "bg-blue-50 text-blue-600 border-blue-100",
      suspended: "bg-rose-50 text-rose-600 border-rose-100",
      expired: "bg-slate-50 text-slate-500 border-slate-200",
    };
    return map[status?.toLowerCase()] || "bg-slate-50 text-slate-600 border-slate-100";
  };

  return (
    <AdminShell>
      <div className="space-y-6 animate-in fade-in duration-500">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight">Organization Registry</h1>
            <p className="text-slate-500 font-medium mt-1">Manage partner accounts and operational access.</p>
          </div>
          <Link
            to="/subscribe"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-black hover:bg-blue-700 shadow-lg shadow-blue-100 transition-all"
          >
            <Plus size={18} /> Add Organization
          </Link>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          <div className="xl:col-span-8 bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex flex-wrap gap-4 items-center justify-between">
              <div className="relative flex-1 min-w-[280px]">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                <input
                  className="w-full bg-white border border-slate-200 rounded-xl pl-11 pr-4 py-2.5 text-sm font-bold placeholder:text-slate-400 outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
                  placeholder="Filter by name or domain..."
                  value={companyFilters.search}
                  onChange={(e) => onFilterChange({ search: e.target.value })}
                />
              </div>
              <div className="flex items-center gap-2">
                <Filter size={16} className="text-slate-400" />
                <select
                  className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-[10px] font-black uppercase tracking-widest outline-none cursor-pointer"
                  value={companyFilters.status}
                  onChange={(e) => onFilterChange({ status: e.target.value })}
                >
                  <option value="all">All Statuses</option>
                  <option value="active">Active</option>
                  <option value="trial">Trial</option>
                  <option value="suspended">Suspended</option>
                  <option value="expired">Expired</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left border-b border-slate-100">
                    <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Organization</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Resources</th>
                    <th className="px-6 py-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {results.map((company) => (
                    <tr
                      key={company.id}
                      className={`group cursor-pointer transition-all ${
                        selectedCompanyId === company.id ? "bg-blue-50/50" : "hover:bg-slate-50/50"
                      }`}
                      onClick={() => dispatch(setSelectedCompanyId(company.id))}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-4">
                          <div
                            className={`h-10 w-10 rounded-xl flex items-center justify-center font-black text-xs ${
                              selectedCompanyId === company.id
                                ? "bg-blue-600 text-white"
                                : "bg-slate-100 text-slate-400 group-hover:bg-slate-200"
                            }`}
                          >
                            {company.name?.charAt(0)}
                          </div>
                          <div>
                            <div className="text-sm font-black text-slate-900 leading-none">{company.name}</div>
                            <div className="text-[10px] font-bold text-slate-400 mt-1">{company.official_email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${getStatusStyle(company.operational_status)}`}
                        >
                          {company.operational_status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-center gap-4 text-slate-400">
                          <div className="flex items-center gap-1.5" title="Drivers">
                            <Users size={14} />
                            <span className="text-xs font-black text-slate-600">{company.drivers_count}</span>
                          </div>
                          <div className="flex items-center gap-1.5" title="Shops">
                            <Store size={14} />
                            <span className="text-xs font-black text-slate-600">{company.shops_count}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <ChevronRight
                          size={18}
                          className={`transition-transform ${
                            selectedCompanyId === company.id
                              ? "translate-x-1 text-blue-600"
                              : "text-slate-300 group-hover:text-slate-400"
                          }`}
                        />
                      </td>
                    </tr>
                  ))}
                  {!isFetching && !results.length ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-6 text-center text-sm text-slate-500">
                        No companies found.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            <div className="p-6 border-t border-slate-100 flex items-center justify-between">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                {isFetching ? "Loading..." : `Showing ${results.length} of ${data?.count || 0} Entities`}
              </p>
              <div className="flex gap-2">
                <button
                  className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-black hover:bg-slate-50 disabled:opacity-30"
                  disabled={(companyFilters.page || 1) <= 1}
                  onClick={() => dispatch(setCompanyFilters({ page: (companyFilters.page || 1) - 1 }))}
                >
                  Previous
                </button>
                <button
                  className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-black hover:bg-slate-50 disabled:opacity-30"
                  disabled={(companyFilters.page || 1) * (companyFilters.page_size || 10) >= (data?.count || 0)}
                  onClick={() => dispatch(setCompanyFilters({ page: (companyFilters.page || 1) + 1 }))}
                >
                  Next
                </button>
              </div>
            </div>
          </div>

          <div className="xl:col-span-4 space-y-6 sticky top-24">
            {!selectedCompanyId ? (
              <div className="bg-slate-50 border border-dashed border-slate-200 rounded-[2rem] p-12 text-center">
                <Building2 className="mx-auto text-slate-300 mb-4" size={48} />
                <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest">No Profile Selected</h3>
              </div>
            ) : (
              <div className="bg-white rounded-[2rem] border border-slate-200 shadow-xl overflow-hidden animate-in slide-in-from-right-4 duration-500">
                <div className="p-8 bg-slate-900 text-white relative">
                  <div className="absolute top-4 right-4 text-white/20">
                    <MoreVertical size={20} />
                  </div>
                  <div className="flex flex-col items-center text-center">
                    <div className="h-16 w-16 bg-blue-600 rounded-2xl flex items-center justify-center text-2xl font-black mb-4">
                      {detailData?.profile?.name?.charAt(0)}
                    </div>
                    <h2 className="text-xl font-black tracking-tight">{detailData?.profile?.name}</h2>
                    <p className="text-xs text-slate-400 font-bold mt-1">{detailData?.profile?.official_email}</p>
                  </div>
                </div>

                <div className="p-8 space-y-8">
                  {isFetchingDetail ? <p className="text-sm text-slate-500">Loading company details...</p> : null}

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 rounded-2xl">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Plan</p>
                      <p className="text-sm font-black text-slate-900">{detailData?.subscription?.plan_name || "Free Tier"}</p>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-2xl">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Status</p>
                      <p className="text-sm font-black text-blue-600 uppercase tracking-tighter">{detailData?.subscription?.status || "Idle"}</p>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center gap-2 mb-4">
                      <CreditCard size={16} className="text-slate-400" />
                      <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Billing History</h3>
                    </div>
                    <div className="space-y-3">
                      {(detailData?.payment_history || []).slice(0, 3).map((payment) => (
                        <div key={payment.id} className="flex justify-between items-center text-xs p-3 rounded-xl border border-slate-50">
                          <span className="font-bold text-slate-700">{formatCurrency(payment.amount)}</span>
                          <span className="px-2 py-0.5 rounded bg-slate-100 font-black text-[9px] uppercase">{payment.status}</span>
                        </div>
                      ))}
                      {!detailData?.payment_history?.length ? (
                        <p className="text-xs text-slate-400 italic">No transactions.</p>
                      ) : null}
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center gap-2 mb-4">
                      <History size={16} className="text-slate-400" />
                      <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Activity Audit</h3>
                    </div>
                    <div className="space-y-4">
                      {(detailData?.activity_log || []).slice(0, 3).map((log) => (
                        <div key={log.id} className="flex gap-3">
                          <div className="h-2 w-2 rounded-full bg-blue-500 mt-1" />
                          <div>
                            <p className="text-[11px] font-bold text-slate-700 leading-tight">{log.action}</p>
                            <p className="text-[9px] text-slate-400 font-bold uppercase mt-1">{log.actor || "System"}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-6 border-t border-slate-100 grid grid-cols-2 gap-3">
                    <button
                      className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-rose-50 text-rose-600 text-[10px] font-black uppercase tracking-widest hover:bg-rose-100 transition-all"
                      onClick={() => onStatusAction("suspend")}
                      disabled={isUpdatingStatus}
                    >
                      <ShieldAlert size={14} /> Suspend
                    </button>
                    <button
                      className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-emerald-50 text-emerald-600 text-[10px] font-black uppercase tracking-widest hover:bg-emerald-100 transition-all"
                      onClick={() => onStatusAction("reactivate")}
                      disabled={isUpdatingStatus}
                    >
                      <ShieldCheck size={14} /> Activate
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
