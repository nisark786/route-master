import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { toast } from "react-toastify";

import { useChangePasswordMutation } from "../../features/billing/billingApi";

function extractError(err) {
  const payload = err?.data;
  if (!payload) return "Unable to update password.";
  if (typeof payload.message === "string" && payload.message) return payload.message;
  const firstKey = Object.keys(payload)[0];
  const firstValue = payload[firstKey];
  if (Array.isArray(firstValue) && firstValue[0]) return String(firstValue[0]);
  if (typeof firstValue === "string") return firstValue;
  return "Unable to update password.";
}

export default function CompanySettingsSecurityPage() {
  const [changePassword, { isLoading }] = useChangePasswordMutation();
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const onSubmit = async (e) => {
    e.preventDefault();
    try {
      await changePassword(form).unwrap();
      toast.success("Password updated successfully.");
      setForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      toast.error(extractError(err));
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-2xl space-y-6">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Security</h1>
          <p className="text-slate-500 mt-1">Manage account password and access hygiene.</p>
        </div>

        <form onSubmit={onSubmit} className="rounded-3xl border border-slate-200 bg-white p-6 space-y-4">
          <input
            type="password"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none"
            placeholder="Current password"
            value={form.current_password}
            onChange={(e) => setForm((prev) => ({ ...prev, current_password: e.target.value }))}
            required
          />
          <input
            type="password"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none"
            placeholder="New password"
            value={form.new_password}
            onChange={(e) => setForm((prev) => ({ ...prev, new_password: e.target.value }))}
            required
          />
          <input
            type="password"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none"
            placeholder="Confirm new password"
            value={form.confirm_password}
            onChange={(e) => setForm((prev) => ({ ...prev, confirm_password: e.target.value }))}
            required
          />
          <div className="flex justify-end">
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700 disabled:opacity-60"
              disabled={isLoading}
            >
              <ShieldCheck size={14} /> {isLoading ? "Updating..." : "Update Password"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
