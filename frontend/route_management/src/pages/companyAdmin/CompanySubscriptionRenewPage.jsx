import { useMemo, useState } from "react";
import { ShieldAlert, CreditCard, CheckCircle2 } from "lucide-react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

import {
  useCompleteRenewalMutation,
  useCreateRenewalOrderMutation,
  useGetPlansQuery,
} from "../../features/billing/billingApi";
import { clearSubscriptionGate } from "../../features/auth/authSlice";

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

function extractError(err, fallback) {
  const payload = err?.data;
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
  const firstValue = Object.values(payload)[0];
  if (Array.isArray(firstValue) && firstValue[0]) return String(firstValue[0]);
  if (typeof firstValue === "string") return firstValue;
  return fallback;
}

export default function CompanySubscriptionRenewPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const subscriptionGate = useSelector((state) => state.auth.subscriptionGate);
  const { data: plans = [] } = useGetPlansQuery();
  const [createRenewalOrder, { isLoading: isCreatingOrder }] = useCreateRenewalOrderMutation();
  const [completeRenewal, { isLoading: isCompleting }] = useCompleteRenewalMutation();

  const [planCode, setPlanCode] = useState("");
  const [error, setError] = useState("");

  const selectedPlan = useMemo(() => {
    if (!plans.length) return null;
    if (!planCode) return plans[0];
    return plans.find((p) => p.code === planCode) || plans[0];
  }, [plans, planCode]);

  const selectedPlanCode = selectedPlan?.code || "";

  const finalizeRenewal = async (paymentData = {}) => {
    const payload = { plan_code: selectedPlanCode, ...paymentData };
    const response = await completeRenewal(payload).unwrap();
    dispatch(clearSubscriptionGate());
    toast.success(response?.message || "Subscription renewed successfully.");
    navigate("/company/dashboard", { replace: true });
  };

  const onRenew = async () => {
    setError("");
    if (!selectedPlanCode) {
      setError("No active plan available for renewal.");
      return;
    }

    try {
      const order = await createRenewalOrder({ plan_code: selectedPlanCode }).unwrap();
      if (!order.requires_payment) {
        await finalizeRenewal();
        return;
      }

      const loaded = await loadRazorpayScript();
      if (!loaded) {
        setError("Payment gateway failed to load.");
        return;
      }

      const rzp = new window.Razorpay({
        key: order.key,
        amount: order.amount,
        currency: order.currency,
        name: "RouteMaster",
        description: `${selectedPlan?.name || "Selected"} Renewal`,
        order_id: order.order_id,
        handler: async (paymentResponse) => {
          try {
            await finalizeRenewal(paymentResponse);
          } catch (err) {
            setError(extractError(err, "Renewal completion failed."));
          }
        },
        theme: { color: "#2563eb" },
      });
      rzp.open();
    } catch (err) {
      setError(extractError(err, "Unable to start renewal."));
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="rounded-3xl border border-amber-200 bg-amber-50 p-6">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
              <ShieldAlert size={20} />
            </div>
            <div>
              <h1 className="text-2xl font-black text-slate-900">Subscription Renewal Required</h1>
              <p className="text-sm text-slate-600 mt-1">
                {subscriptionGate?.message || "Your company access is currently restricted due to subscription status."}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 space-y-5">
          <div>
            <p className="text-[11px] font-black uppercase tracking-widest text-slate-500">Select Plan</p>
            <select
              className="mt-2 w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
              value={selectedPlanCode}
              onChange={(e) => setPlanCode(e.target.value)}
            >
              {plans.map((plan) => (
                <option key={plan.id} value={plan.code}>
                  {plan.name} - INR {plan.price}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-2xl bg-slate-900 p-5 text-white">
            <p className="text-xs font-black uppercase tracking-widest text-slate-300">Summary</p>
            <p className="text-lg font-black mt-2">{selectedPlan?.name || "Plan"}</p>
            <p className="text-3xl font-black mt-1">INR {selectedPlan?.price || "0.00"}</p>
          </div>

          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
              {error}
            </div>
          ) : null}

          <button
            type="button"
            className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-5 py-3.5 text-sm font-black uppercase tracking-widest text-white hover:bg-blue-700 disabled:opacity-60"
            onClick={onRenew}
            disabled={isCreatingOrder || isCompleting || !selectedPlanCode}
          >
            {isCreatingOrder || isCompleting ? <CreditCard size={16} /> : <CheckCircle2 size={16} />}
            {isCreatingOrder || isCompleting ? "Processing..." : "Renew Subscription"}
          </button>
        </div>
      </div>
    </div>
  );
}
