import { useMemo, useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, CreditCard, Mail, Building2, ShieldCheck, ChevronRight, ArrowLeft } from "lucide-react";

import {
  useCompleteRegistrationMutation,
  useCreateOrderMutation,
  useGetPlansQuery,
  useResendOtpMutation,
  useStartRegistrationMutation,
  useVerifyOtpMutation,
} from "../features/billing/billingApi";
import { setCredentials } from "../features/auth/authSlice";

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) { resolve(true); return; }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function Payment() {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const { data: plans = [] } = useGetPlansQuery();
  const [startRegistration, { isLoading: isStarting }] = useStartRegistrationMutation();
  const [verifyOtp, { isLoading: isVerifying }] = useVerifyOtpMutation();
  const [resendOtp, { isLoading: isResending }] = useResendOtpMutation();
  const [createOrder, { isLoading: isCreatingOrder }] = useCreateOrderMutation();
  const [completeRegistration, { isLoading: isCompleting }] = useCompleteRegistrationMutation();

  const [step, setStep] = useState("DETAILS");
  const [registrationId, setRegistrationId] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState({
    company_name: "", official_email: "", phone: "",
    address: "", admin_email: "", admin_password: "",
    plan_code: "trial",
  });

  const selectedPlan = useMemo(
    () => plans.find((plan) => plan.code === form.plan_code) || plans[0] || null,
    [plans, form.plan_code]
  );
  const resolvedPlanCode = selectedPlan?.code || "";

  const onChange = (e) => setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const extractError = (err, fallback) => {
    const payload = err?.data;
    if (!payload) return fallback;
    if (typeof payload === "string") return payload;
    if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
    if (typeof payload.error === "string") return payload.error;
    if (payload.error?.details && typeof payload.error.details === "object") {
      const firstDetail = Object.values(payload.error.details)[0];
      if (Array.isArray(firstDetail) && firstDetail[0]) return String(firstDetail[0]);
      if (typeof firstDetail === "string") return firstDetail;
    }
    const firstValue = Object.values(payload)[0];
    if (Array.isArray(firstValue) && firstValue[0]) return String(firstValue[0]);
    if (typeof firstValue === "string") return firstValue;
    return fallback;
  };

  // Logic handlers remain identical to ensure functional parity
  const onStart = async (e) => {
    e.preventDefault(); setError(""); setSuccess("");
    try {
      const data = await startRegistration({ ...form, plan_code: resolvedPlanCode }).unwrap();
      setRegistrationId(data.registration_id);
      setStep("OTP");
      setSuccess("Verification code sent to your official email.");
    } catch (err) { setError(extractError(err, "Registration failed")); }
  };

  const onVerifyOtp = async (e) => {
    e.preventDefault(); setError(""); setSuccess("");
    try {
      await verifyOtp({ registration_id: registrationId, otp }).unwrap();
      setStep("PAYMENT");
    } catch (err) { setError(extractError(err, "Invalid OTP. Please try again.")); }
  };

  const onResendOtp = async () => {
    setError(""); setSuccess("");
    try {
      await resendOtp({ registration_id: registrationId }).unwrap();
      setSuccess("New OTP sent.");
    } catch (err) { setError(extractError(err, "Failed to resend.")); }
  };

  const finalizeRegistration = async (paymentData = {}) => {
    const payload = { registration_id: registrationId, ...paymentData };
    const data = await completeRegistration(payload).unwrap();
    dispatch(setCredentials(data));
    navigate("/company/dashboard");
  };

  const onProceedPayment = async () => {
    setError(""); setSuccess("");
    try {
      const orderData = await createOrder({ registration_id: registrationId }).unwrap();
      if (!orderData.requires_payment) { await finalizeRegistration(); return; }
      const loaded = await loadRazorpayScript();
      if (!loaded) { setError("Payment gateway failed to load."); return; }

      const rzp = new window.Razorpay({
        key: orderData.key, amount: orderData.amount, currency: orderData.currency,
        name: "RouteMaster", description: `${selectedPlan?.name} Subscription`,
        order_id: orderData.order_id,
        handler: async (response) => { finalizeRegistration(response); },
        prefill: { email: form.official_email },
        theme: { color: "#2563eb" },
      });
      rzp.open();
    } catch (err) { setError(extractError(err, "Order creation failed.")); }
  };

  const STEPS = [
    { id: "DETAILS", label: "Company", icon: Building2 },
    { id: "OTP", label: "Verify", icon: Mail },
    { id: "PAYMENT", label: "Payment", icon: CreditCard },
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans py-12 px-6">
      <div className="max-w-2xl mx-auto">
        
        {/* Step Progress Bar - SaaS Style */}
        <div className="flex items-center justify-between mb-10 px-4">
          {STEPS.map((s, idx) => (
            <div key={s.id} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-2">
                <div className={`h-10 w-10 rounded-xl flex items-center justify-center transition-all ${
                  step === s.id ? "bg-blue-600 text-white shadow-lg shadow-blue-200" : 
                  STEPS.findIndex(x => x.id === step) > idx ? "bg-emerald-500 text-white" : "bg-white border border-slate-200 text-slate-400"
                }`}>
                  {STEPS.findIndex(x => x.id === step) > idx ? <CheckCircle2 size={20} /> : <s.icon size={20} />}
                </div>
                <span className={`text-[10px] font-bold uppercase tracking-widest ${step === s.id ? "text-blue-600" : "text-slate-400"}`}>
                  {s.label}
                </span>
              </div>
              {idx < STEPS.length - 1 && (
                <div className="h-[2px] flex-1 mx-4 bg-slate-200 relative top-[-10px]">
                  <div className={`h-full bg-blue-600 transition-all duration-500 ${STEPS.findIndex(x => x.id === step) > idx ? "w-full" : "w-0"}`} />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Main Form Card */}
        <div className="bg-white border border-slate-200 rounded-[2rem] shadow-sm overflow-hidden">
          <div className="p-8 border-b border-slate-50 bg-slate-50/50">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Setup Platform</h1>
            <p className="text-slate-500 text-sm mt-1">Initialize your enterprise logistics workspace</p>
          </div>

          <div className="p-8">
            {error && <div className="mb-6 p-4 bg-rose-50 border border-rose-100 text-rose-600 text-sm font-bold rounded-2xl flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" /> {error}
            </div>}
            
            {success && <div className="mb-6 p-4 bg-emerald-50 border border-emerald-100 text-emerald-600 text-sm font-bold rounded-2xl flex items-center gap-3">
               <CheckCircle2 size={18} /> {success}
            </div>}

            {step === "DETAILS" && (
              <form onSubmit={onStart} className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1">Company Identity</label>
                    <input className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all" name="company_name" value={form.company_name} onChange={onChange} placeholder="Legal Entity Name" required />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1">Work Email</label>
                    <input className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all" name="official_email" value={form.official_email} onChange={onChange} placeholder="corp@domain.com" type="email" required />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1">Admin Account</label>
                    <input className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all" name="admin_email" value={form.admin_email} onChange={onChange} placeholder="admin@domain.com" type="email" required />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1">Secure Password</label>
                    <input className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all" name="admin_password" value={form.admin_password} onChange={onChange} placeholder="********" type="password" required />
                  </div>
                  <div className="md:col-span-2 space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 uppercase ml-1">Subscription Tier</label>
                    <select className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all appearance-none" name="plan_code" value={resolvedPlanCode} onChange={onChange}>
                      {plans.map((plan) => (
                        <option key={plan.id} value={plan.code}>{plan.name} - INR {plan.price}/mo</option>
                      ))}
                    </select>
                  </div>
                </div>

                <button className="w-full bg-blue-600 text-white py-4 rounded-2xl font-black text-sm hover:bg-blue-700 shadow-xl shadow-blue-500/20 transition-all flex justify-center items-center gap-2 group" disabled={isStarting} type="submit">
                  {isStarting ? "Processing..." : "Continue to Verification"}
                  <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                </button>
              </form>
            )}

            {step === "OTP" && (
              <form onSubmit={onVerifyOtp} className="space-y-6 text-center">
                <div className="bg-blue-50 h-16 w-16 rounded-2xl flex items-center justify-center mx-auto mb-4 text-blue-600">
                  <Mail size={32} />
                </div>
                <h3 className="font-bold text-slate-900">Verify your Email</h3>
                <p className="text-sm text-slate-500 px-10">We've sent a 6-digit code to <span className="text-slate-900 font-bold">{form.official_email}</span></p>
                <input className="w-full max-w-[280px] mx-auto block text-center tracking-[1em] text-2xl font-black border-2 border-slate-200 rounded-2xl py-4 focus:border-blue-500 outline-none transition-all" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value)} placeholder="000000" required />
                <div className="flex flex-col gap-3">
                  <button className="w-full bg-blue-600 text-white py-4 rounded-2xl font-bold shadow-lg shadow-blue-500/20" disabled={isVerifying} type="submit">
                    {isVerifying ? "Verifying..." : "Confirm Verification"}
                  </button>
                  <button className="text-xs font-bold text-slate-400 hover:text-blue-600 transition-colors" disabled={isResending} type="button" onClick={onResendOtp}>
                    Didn't get the code? <span className="underline">Resend OTP</span>
                  </button>
                </div>
              </form>
            )}

            {step === "PAYMENT" && (
              <div className="space-y-6">
                <div className="p-6 rounded-[1.5rem] bg-slate-900 text-white relative overflow-hidden">
                  <div className="absolute top-[-20px] right-[-20px] h-32 w-32 bg-blue-600/20 blur-3xl rounded-full" />
                  <p className="text-[10px] font-bold text-blue-400 uppercase tracking-widest mb-4">Summary</p>
                  <h3 className="text-xl font-bold">{selectedPlan?.name} Plan</h3>
                  <div className="mt-6 flex justify-between items-end">
                    <span className="text-sm text-slate-400 italic">Monthly Subscription</span>
                    <span className="text-3xl font-black">INR {selectedPlan?.price}</span>
                  </div>
                </div>
                <button className="w-full bg-blue-600 text-white py-4 rounded-2xl font-black text-sm hover:bg-blue-700 shadow-xl shadow-blue-500/20 transition-all flex justify-center items-center gap-2 group" disabled={isCreatingOrder || isCompleting} onClick={onProceedPayment}>
                  <ShieldCheck size={18} />
                  {isCreatingOrder || isCompleting ? "Processing..." : "Pay & Activate Dashboard"}
                </button>
                <button onClick={() => setStep("DETAILS")} className="w-full flex justify-center items-center gap-2 text-xs font-bold text-slate-400 hover:text-slate-600 transition-colors">
                  <ArrowLeft size={14} /> Back to Details
                </button>
              </div>
            )}
          </div>
          
          <div className="bg-slate-50 p-6 flex justify-center gap-8 border-t border-slate-100 opacity-50">
             {/* Mock visual trust badges common in your templates */}
             <div className="flex items-center gap-2 grayscale"><ShieldCheck size={16}/> <span className="text-[10px] font-black uppercase">PCI DSS</span></div>
             <div className="flex items-center gap-2 grayscale"><CreditCard size={16}/> <span className="text-[10px] font-black uppercase">Razorpay</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
