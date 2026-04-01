import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { toast } from "react-toastify";

import {
  useGetCompanyProfileQuery,
  useUpdateCompanyProfileMutation,
} from "../../features/billing/billingApi";
import { extractApiErrorMessage } from "../../utils/adminUi";

export default function CompanySettingsProfilePage() {
  const { data: profile, isLoading, error } = useGetCompanyProfileQuery();
  const [updateProfile, { isLoading: isSaving, error: updateError }] = useUpdateCompanyProfileMutation();
  const [form, setForm] = useState({
    name: "",
    official_email: "",
    phone: "",
    address: "",
  });

  useEffect(() => {
    if (!profile) return;
    setForm({
      name: profile.name || "",
      official_email: profile.official_email || "",
      phone: profile.phone || "",
      address: profile.address || "",
    });
  }, [profile]);

  useEffect(() => {
    const feedback = extractApiErrorMessage(error) || extractApiErrorMessage(updateError);
    if (feedback) toast.error(feedback, { toastId: `settings-profile-${feedback}` });
  }, [error, updateError]);

  const onSubmit = async (e) => {
    e.preventDefault();
    try {
      await updateProfile(form).unwrap();
      toast.success("Company profile updated.");
    } catch {
      // handled by hook state
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-3xl space-y-6">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Company Profile</h1>
          <p className="text-slate-500 mt-1">Manage your company identity and contact details.</p>
        </div>

        {isLoading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">Loading profile...</div>
        ) : (
          <form onSubmit={onSubmit} className="rounded-3xl border border-slate-200 bg-white p-6 space-y-4">
            <input
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none"
              placeholder="Company name"
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              required
            />
            <input
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none"
              placeholder="Official email"
              type="email"
              value={form.official_email}
              onChange={(e) => setForm((prev) => ({ ...prev, official_email: e.target.value }))}
              required
            />
            <input
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none"
              placeholder="Phone"
              value={form.phone}
              onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))}
            />
            <textarea
              className="w-full min-h-[110px] rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none"
              placeholder="Address"
              value={form.address}
              onChange={(e) => setForm((prev) => ({ ...prev, address: e.target.value }))}
            />
            <div className="flex justify-end">
              <button
                type="submit"
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700 disabled:opacity-60"
                disabled={isSaving}
              >
                <Save size={14} /> {isSaving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
