import { useDispatch, useSelector } from "react-redux";
import AdminShell from "../../components/AdminShell";
import {
  useCreatePlanMutation,
  useGetPaymentsQuery,
  useGetPlanChangeLogsQuery,
  useGetPlansQuery,
  useUpdatePlanMutation,
} from "../../features/admin/adminApi";
import { setPaymentFilters } from "../../features/admin/adminSlice";
import { useMemo, useState } from "react";
import {
  Plus,
  Settings2,
  Receipt,
  History,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Filter,
  Pencil,
  Save,
  X,
} from "lucide-react";
import { useEffect } from "react";
import { toast } from "react-toastify";
import { extractApiErrorMessage, extractApiSuccessMessage, formatCurrency } from "../../utils/adminUi";

export default function AdminSubscriptionsPage() {
  const dispatch = useDispatch();
  const paymentFilters = useSelector((state) => state.admin.paymentFilters);

  const {
    data: plans = [],
    isLoading: isPlansLoading,
    error: plansError,
  } = useGetPlansQuery(undefined, {
    selectFromResult: ({ data, isLoading, error }) => ({
      data: data || [],
      isLoading,
      error,
    }),
  });
  const { data: planLogs = [], error: logsError } = useGetPlanChangeLogsQuery(undefined, {
    selectFromResult: ({ data, error }) => ({
      data: data || [],
      error,
    }),
  });
  const {
    data: payments,
    isLoading: isPaymentsLoading,
    error: paymentsError,
  } = useGetPaymentsQuery(paymentFilters, {
    selectFromResult: ({ data, isLoading, error }) => ({ data, isLoading, error }),
  });

  const [createPlan, { isLoading: isCreating, error: createError }] = useCreatePlanMutation();
  const [updatePlan, { isLoading: isUpdating, error: updateError }] = useUpdatePlanMutation();

  const [draft, setDraft] = useState({
    code: "",
    name: "",
    price: "",
    duration_days: 30,
    features: "",
    is_active: true,
  });
  const [editingPlanId, setEditingPlanId] = useState(null);
  const [editDraft, setEditDraft] = useState({
    name: "",
    price: "",
    duration_days: 30,
    features: "",
    is_active: true,
  });

  const feedback = useMemo(() => {
    return (
      extractApiErrorMessage(createError) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(plansError) ||
      extractApiErrorMessage(logsError) ||
      extractApiErrorMessage(paymentsError)
    );
  }, [createError, updateError, plansError, logsError, paymentsError]);

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `subscriptions-error-${feedback}` });
    }
  }, [feedback]);

  const onCreatePlan = async (e) => {
    e.preventDefault();
    try {
      const response = await createPlan({
        code: draft.code,
        name: draft.name,
        price: String(draft.price || "0").trim(),
        duration_days: Number(draft.duration_days || 30),
        features: draft.features.split(",").map((f) => f.trim()).filter(Boolean),
        is_active: draft.is_active,
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);

      setDraft({ code: "", name: "", price: "", duration_days: 30, features: "", is_active: true });
    } catch {
      // Error surfaced from mutation state.
    }
  };

  const onTogglePlan = async (plan) => {
    try {
      const response = await updatePlan({ planId: plan.id, body: { is_active: !plan.is_active } }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
    } catch {
      // Error surfaced from mutation state.
    }
  };

  const onStartEditPlan = (plan) => {
    setEditingPlanId(plan.id);
    setEditDraft({
      name: plan.name || "",
      price: plan.price || "",
      duration_days: plan.duration_days || 30,
      features: Array.isArray(plan.features) ? plan.features.join(", ") : "",
      is_active: !!plan.is_active,
    });
  };

  const onCancelEditPlan = () => {
    setEditingPlanId(null);
    setEditDraft({
      name: "",
      price: "",
      duration_days: 30,
      features: "",
      is_active: true,
    });
  };

  const onSavePlan = async (e) => {
    e.preventDefault();
    if (!editingPlanId) return;

    try {
      const response = await updatePlan({
        planId: editingPlanId,
        body: {
          name: editDraft.name,
          price: String(editDraft.price || "0").trim(),
          duration_days: Number(editDraft.duration_days || 30),
          features: editDraft.features.split(",").map((f) => f.trim()).filter(Boolean),
          is_active: editDraft.is_active,
        },
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      onCancelEditPlan();
    } catch {
      // Error surfaced from mutation state.
    }
  };

  return (
    <AdminShell>
      <div className="space-y-8 animate-in fade-in duration-500">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight">Billing & Plans</h1>
            <p className="text-slate-500 font-medium mt-1">Configure service tiers and monitor global transaction flow.</p>
          </div>
          <div className="bg-blue-50 px-4 py-2 rounded-2xl border border-blue-100 flex items-center gap-2">
            <CheckCircle2 size={16} className="text-blue-600" />
            <span className="text-[10px] font-black text-blue-700 uppercase tracking-widest">Payment Gateway: Active</span>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
          <div className="xl:col-span-4">
            <form className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm sticky top-24" onSubmit={onCreatePlan}>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-600 rounded-xl text-white">
                  <Plus size={20} />
                </div>
                <h2 className="text-lg font-black text-slate-900 tracking-tight">New Plan</h2>
              </div>

              <div className="space-y-4">
                {[
                  { id: "code", label: "Plan Code", placeholder: "e.g. enterprise_monthly", type: "text" },
                  { id: "name", label: "Display Name", placeholder: "e.g. Pro Plus", type: "text" },
                  { id: "price", label: "Price (INR)", placeholder: "0.00", type: "number" },
                  { id: "duration_days", label: "Duration (Days)", placeholder: "30", type: "number" },
                ].map((input) => (
                  <div key={input.id}>
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-1.5 block">
                      {input.label}
                    </label>
                    <input
                      className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all outline-none"
                      placeholder={input.placeholder}
                      type={input.type}
                      value={draft[input.id]}
                      onChange={(e) => setDraft((p) => ({ ...p, [input.id]: e.target.value }))}
                      required
                    />
                  </div>
                ))}

                <div>
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-1.5 block">Features</label>
                  <textarea
                    className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all outline-none h-24 resize-none"
                    placeholder="Fleet Tracking, SMS Alerts, API Access..."
                    value={draft.features}
                    onChange={(e) => setDraft((p) => ({ ...p, features: e.target.value }))}
                  />
                </div>

                <button
                  className="w-full bg-slate-900 text-white font-black text-xs uppercase tracking-[0.2em] rounded-2xl py-4 shadow-lg shadow-slate-200 hover:bg-black transition-all disabled:opacity-60 mt-4"
                  disabled={isCreating}
                  type="submit"
                >
                  {isCreating ? "Processing..." : "Deploy Plan"}
                </button>
              </div>
            </form>
          </div>

          <div className="xl:col-span-8 bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden flex flex-col">
            <div className="p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <h2 className="text-lg font-black text-slate-900 tracking-tight">Plan Catalog</h2>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Manage public service tiers</p>
              </div>
              <Settings2 size={20} className="text-slate-300" />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-white">
                  <tr className="text-left">
                    {["Code", "Price", "Duration", "Status", "Action"].map((h) => (
                      <th key={h} className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {plans.map((plan) => (
                    <tr key={plan.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-8 py-5">
                        <p className="text-sm font-black text-slate-900">{plan.name}</p>
                        <p className="text-[10px] font-bold text-slate-400 font-mono">{plan.code}</p>
                      </td>
                      <td className="px-8 py-5">
                        <span className="text-sm font-black text-slate-900">{formatCurrency(plan.price)}</span>
                      </td>
                      <td className="px-8 py-5">
                        <span className="text-xs font-bold text-slate-500">{plan.duration_days} Days</span>
                      </td>
                      <td className="px-8 py-5">
                        <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter ${plan.is_active ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"}`}>
                          <div className={`h-1 w-1 rounded-full ${plan.is_active ? "bg-emerald-500" : "bg-rose-500"}`} />
                          {plan.is_active ? "Active" : "Disabled"}
                        </div>
                      </td>
                      <td className="px-8 py-5">
                        <div className="flex items-center gap-2">
                          <button
                            className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-blue-100 text-blue-600 hover:bg-blue-50 transition-all inline-flex items-center gap-1"
                            onClick={() => onStartEditPlan(plan)}
                            disabled={isUpdating}
                          >
                            <Pencil size={12} /> Edit
                          </button>
                          <button
                            className={`text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border transition-all ${
                              plan.is_active
                                ? "border-rose-100 text-rose-500 hover:bg-rose-50"
                                : "border-emerald-100 text-emerald-500 hover:bg-emerald-50"
                            }`}
                            onClick={() => onTogglePlan(plan)}
                            disabled={isUpdating}
                          >
                            {plan.is_active ? "Disable" : "Enable"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!isPlansLoading && !plans.length ? (
                    <tr>
                      <td colSpan={5} className="px-8 py-8 text-center text-sm text-slate-500">No plans found.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            {editingPlanId ? (
              <form className="border-t border-slate-100 p-6 bg-slate-50/60" onSubmit={onSavePlan}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-black text-slate-900 uppercase tracking-widest">Edit Existing Plan</h3>
                  <button
                    type="button"
                    className="text-slate-500 hover:text-slate-700 inline-flex items-center gap-1 text-xs font-bold"
                    onClick={onCancelEditPlan}
                  >
                    <X size={14} /> Close
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-1.5 block">Name</label>
                    <input
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-bold focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                      value={editDraft.name}
                      onChange={(e) => setEditDraft((p) => ({ ...p, name: e.target.value }))}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-1.5 block">Price (INR)</label>
                    <input
                      type="number"
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-bold focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                      value={editDraft.price}
                      onChange={(e) => setEditDraft((p) => ({ ...p, price: e.target.value }))}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-1.5 block">Duration (Days)</label>
                    <input
                      type="number"
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-bold focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                      value={editDraft.duration_days}
                      onChange={(e) => setEditDraft((p) => ({ ...p, duration_days: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="inline-flex items-center gap-2 text-xs font-bold text-slate-700">
                      <input
                        type="checkbox"
                        checked={editDraft.is_active}
                        onChange={(e) => setEditDraft((p) => ({ ...p, is_active: e.target.checked }))}
                      />
                      Plan Active
                    </label>
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-1.5 block">Features (comma separated)</label>
                    <textarea
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-bold focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none h-24 resize-none"
                      value={editDraft.features}
                      onChange={(e) => setEditDraft((p) => ({ ...p, features: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="mt-5 flex items-center gap-2">
                  <button
                    type="submit"
                    className="px-4 py-2.5 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest hover:bg-black transition-all inline-flex items-center gap-2 disabled:opacity-60"
                    disabled={isUpdating}
                  >
                    <Save size={14} /> {isUpdating ? "Saving..." : "Save Changes"}
                  </button>
                  <button
                    type="button"
                    className="px-4 py-2.5 rounded-xl border border-slate-200 text-xs font-black uppercase tracking-widest hover:bg-white transition-all"
                    onClick={onCancelEditPlan}
                    disabled={isUpdating}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : null}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-slate-100 rounded-xl text-slate-600">
                <History size={18} />
              </div>
              <h2 className="text-lg font-black text-slate-900 tracking-tight">Lifecycle Events</h2>
            </div>
            <div className="space-y-4 max-h-[400px] overflow-auto pr-2 custom-scrollbar">
              {planLogs.map((log) => (
                <div key={log.id} className="group flex items-center justify-between p-4 rounded-2xl border border-slate-50 hover:border-blue-100 hover:bg-blue-50/30 transition-all">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-full bg-white border border-slate-100 flex items-center justify-center text-[10px] font-black text-slate-400 group-hover:text-blue-600">
                      {log.company_name?.charAt(0)}
                    </div>
                    <div>
                      <p className="text-sm font-black text-slate-900">{log.company_name}</p>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-tighter mt-0.5">
                        <span>{log.old_plan || "Start"}</span>
                        <ArrowRight size={10} className="text-blue-400" />
                        <span className="text-blue-600 font-black">{log.new_plan}</span>
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] font-black text-slate-300 uppercase">{new Date(log.created_at).toLocaleDateString()}</span>
                </div>
              ))}
              {!planLogs.length ? <p className="text-sm text-slate-500">No lifecycle logs found.</p> : null}
            </div>
          </div>

          <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-50 rounded-xl text-emerald-600">
                  <Receipt size={18} />
                </div>
                <h2 className="text-lg font-black text-slate-900 tracking-tight">Transaction Ledger</h2>
              </div>
              <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100">
                <Filter size={14} className="text-slate-400" />
                <select
                  className="bg-transparent text-[10px] font-black uppercase tracking-widest outline-none cursor-pointer"
                  value={paymentFilters.status}
                  onChange={(e) => dispatch(setPaymentFilters({ status: e.target.value, page: 1 }))}
                >
                  <option value="all">Status: All</option>
                  <option value="SUCCESS">Success</option>
                  <option value="FAILED">Failed</option>
                  <option value="REFUNDED">Refunded</option>
                  <option value="DISPUTED">Disputed</option>
                </select>
              </div>
            </div>

            <div className="space-y-4 max-h-[400px] overflow-auto pr-2 custom-scrollbar">
              {(payments?.results || []).map((payment) => (
                <div key={payment.id} className="flex items-center justify-between p-4 rounded-2xl bg-slate-50/50 border border-transparent hover:border-slate-200 transition-all">
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-xl ${payment.status === "SUCCESS" ? "text-emerald-500" : "text-rose-500"}`}>
                      {payment.status === "SUCCESS" ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                    </div>
                    <div>
                      <p className="text-sm font-black text-slate-900">{payment.company_name}</p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                        {formatCurrency(payment.amount)} | {new Date(payment.paid_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className={`text-[10px] font-black px-2 py-1 rounded-lg ${payment.status === "SUCCESS" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                    {payment.status}
                  </div>
                </div>
              ))}
              {isPaymentsLoading ? <p className="text-sm text-slate-500">Loading payments...</p> : null}
              {!isPaymentsLoading && !(payments?.results || []).length ? (
                <p className="text-sm text-slate-500">No payments found.</p>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
