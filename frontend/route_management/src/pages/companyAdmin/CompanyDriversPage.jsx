import { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, Search, Trash2, UserRound } from "lucide-react";
import { toast } from "react-toastify";
import {
  useCreateDriverMutation,
  useDeleteDriverMutation,
  useGetDriversQuery,
  useResetDriverPasswordMutation,
  useUpdateDriverMutation,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage, extractApiSuccessMessage } from "../../utils/adminUi";
import AdminModal from "../../components/companyAdmin/AdminModal";

const DRIVER_STATUS_OPTIONS = [
  { value: "AVAILABLE", label: "Available" },
  { value: "IN_ROUTE", label: "In Route" },
  { value: "ON_LEAVE", label: "On Leave" },
];

const INITIAL_DRIVER_DRAFT = {
  name: "",
  mobile_number: "",
  age: "",
  status: "AVAILABLE",
  temporary_password: "",
};

export default function CompanyDriversPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [draft, setDraft] = useState(INITIAL_DRIVER_DRAFT);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState(INITIAL_DRIVER_DRAFT);
  const [confirmAction, setConfirmAction] = useState(null);
  const [resetTargetDriverId, setResetTargetDriverId] = useState(null);
  const [resetTempPassword, setResetTempPassword] = useState("");

  const { data: drivers = [], isLoading, error } = useGetDriversQuery({ search });
  const [createDriver, { isLoading: isCreating, error: createError }] = useCreateDriverMutation();
  const [updateDriver, { isLoading: isUpdating, error: updateError }] = useUpdateDriverMutation();
  const [deleteDriver, { isLoading: isDeleting, error: deleteError }] = useDeleteDriverMutation();
  const [resetDriverPassword, { isLoading: isResettingPassword, error: resetPasswordError }] = useResetDriverPasswordMutation();

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(error) ||
      extractApiErrorMessage(createError) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(deleteError) ||
      extractApiErrorMessage(resetPasswordError),
    [error, createError, updateError, deleteError, resetPasswordError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `drivers-error-${feedback}` });
    }
  }, [feedback]);

  const onSearch = (e) => {
    e.preventDefault();
    setSearch(searchInput.trim());
  };

  const onCreateDriver = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...draft,
        age: Number(draft.age || 0),
      };

      const created = await createDriver(payload).unwrap();
      const successMessage = extractApiSuccessMessage(created);
      if (successMessage) toast.success(successMessage);
      setDraft(INITIAL_DRIVER_DRAFT);
      setIsCreateOpen(false);
    } catch {
      // handled from mutation state
    }
  };

  const startEdit = (driver) => {
    setEditingId(driver.id);
    setEditDraft({
      name: driver.name,
      mobile_number: driver.mobile_number,
      age: driver.age,
      status: driver.status,
    });
  };

  const saveEdit = (e) => {
    e.preventDefault();
    if (!editingId) return;
    setConfirmAction({
      type: "update",
      driverId: editingId,
      body: { ...editDraft, age: Number(editDraft.age || 0) },
    });
  };

  const removeDriver = (driverId) => setConfirmAction({ type: "delete", driverId });

  const onConfirmAction = async () => {
    if (!confirmAction) return;
    try {
      if (confirmAction.type === "delete") {
        const response = await deleteDriver(confirmAction.driverId).unwrap();
        const successMessage = extractApiSuccessMessage(response);
        if (successMessage) toast.success(successMessage);
        if (editingId === confirmAction.driverId) setEditingId(null);
      }
      if (confirmAction.type === "update") {
        const response = await updateDriver({ driverId: confirmAction.driverId, body: confirmAction.body }).unwrap();
        const successMessage = extractApiSuccessMessage(response);
        if (successMessage) toast.success(successMessage);
        setEditingId(null);
      }
      setConfirmAction(null);
    } catch {
      // handled from mutation state
    }
  };

  const onResetPassword = async () => {
    if (!resetTargetDriverId) return;
    try {
      const payload = { temporary_password: resetTempPassword.trim() };
      const response = await resetDriverPassword({
        driverId: resetTargetDriverId,
        body: payload,
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setResetTempPassword("");
      setResetTargetDriverId(null);
    } catch {
      // handled by mutation state
    }
  };

  return (
    <div className="space-y-8 p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">Driver Management</h1>
        <p className="text-slate-500 font-medium mt-1">Create and manage drivers, then assign routes and vehicles.</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
          onClick={() => setIsCreateOpen(true)}
        >
          <Plus size={14} /> Add Driver
        </button>
      </div>

      <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-8 border-b border-slate-100 bg-slate-50/50 space-y-4">
            <h2 className="text-lg font-black text-slate-900 tracking-tight">Drivers</h2>
            <form className="flex gap-2" onSubmit={onSearch}>
              <div className="relative flex-1">
                <Search size={14} className="absolute top-1/2 -translate-y-1/2 left-3 text-slate-400" />
                <input
                  className="w-full bg-white border border-slate-200 rounded-xl px-9 py-2.5 text-sm font-semibold outline-none"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search name or mobile..."
                />
              </div>
              <button type="submit" className="px-4 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest">
                Search
              </button>
            </form>
          </div>

          {isLoading ? (
            <p className="p-8 text-sm text-slate-500">Loading drivers...</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {drivers.map((driver) => (
                <div key={driver.id} className="p-6 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                      <UserRound size={18} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-black text-slate-900 truncate">{driver.name}</p>
                      <p className="text-xs text-slate-600 font-semibold truncate">
                        {driver.mobile_number} | Age {driver.age}
                      </p>
                      <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
                        {driver.status.replace("_", " ")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-blue-100 text-blue-600 hover:bg-blue-50 transition-all inline-flex items-center gap-1"
                      onClick={() => startEdit(driver)}
                      disabled={isUpdating}
                    >
                      <Pencil size={12} /> Edit
                    </button>
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-rose-100 text-rose-600 hover:bg-rose-50 transition-all inline-flex items-center gap-1"
                      onClick={() => removeDriver(driver.id)}
                      disabled={isDeleting}
                    >
                      <Trash2 size={12} /> Delete
                    </button>
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-amber-200 text-amber-700 hover:bg-amber-50 transition-all inline-flex items-center gap-1"
                      onClick={() => {
                        setResetTargetDriverId(driver.id);
                        setResetTempPassword("");
                      }}
                      disabled={isResettingPassword}
                    >
                      Reset Password
                    </button>
                  </div>
                </div>
              ))}
              {!drivers.length ? <p className="p-8 text-sm text-slate-500">No drivers found.</p> : null}
            </div>
          )}
      </div>

      <AdminModal
        isOpen={isCreateOpen}
        title="Add Driver"
        description="Create a driver account for your company."
        onClose={() => setIsCreateOpen(false)}
      >
        <form className="space-y-4" onSubmit={onCreateDriver}>
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.name}
            onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
            placeholder="Driver Name"
            required
          />
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.mobile_number}
            onChange={(e) => setDraft((p) => ({ ...p, mobile_number: e.target.value }))}
            placeholder="Mobile Number"
            required
          />
          <input
            type="number"
            min={18}
            max={80}
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.age}
            onChange={(e) => setDraft((p) => ({ ...p, age: e.target.value }))}
            placeholder="Age"
            required
          />
          <input
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.temporary_password}
            onChange={(e) => setDraft((p) => ({ ...p, temporary_password: e.target.value }))}
            placeholder="Temporary Password"
            required
          />
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Password will not be returned in response. Share it securely with the driver.
          </p>
          <select
            className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
            value={draft.status}
            onChange={(e) => setDraft((p) => ({ ...p, status: e.target.value }))}
          >
            {DRIVER_STATUS_OPTIONS.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => setIsCreateOpen(false)}
              disabled={isCreating}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white disabled:opacity-60"
              disabled={isCreating}
            >
              {isCreating ? "Saving..." : "Create Driver"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={!!editingId}
        title="Edit Driver"
        description="Update driver details."
        onClose={() => setEditingId(null)}
      >
        <form className="space-y-4" onSubmit={saveEdit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.name}
              onChange={(e) => setEditDraft((p) => ({ ...p, name: e.target.value }))}
              placeholder="Driver Name"
              required
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.mobile_number}
              onChange={(e) => setEditDraft((p) => ({ ...p, mobile_number: e.target.value }))}
              placeholder="Mobile Number"
              required
            />
            <input
              type="number"
              min={18}
              max={80}
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.age}
              onChange={(e) => setEditDraft((p) => ({ ...p, age: e.target.value }))}
              placeholder="Age"
              required
            />
            <select
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.status}
              onChange={(e) => setEditDraft((p) => ({ ...p, status: e.target.value }))}
            >
              {DRIVER_STATUS_OPTIONS.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => setEditingId(null)}
              disabled={isUpdating}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white transition-all hover:bg-black disabled:opacity-60"
              disabled={isUpdating}
            >
              {isUpdating ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </AdminModal>

      {confirmAction ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">
              {confirmAction.type === "delete" ? "Confirm Delete" : "Confirm Update"}
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              {confirmAction.type === "delete"
                ? "Are you sure you want to delete this driver?"
                : "Are you sure you want to update this driver details?"}
            </p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmAction(null)}
                disabled={isDeleting || isUpdating}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`px-4 py-2 rounded-xl text-white text-xs font-black uppercase tracking-widest disabled:opacity-60 ${
                  confirmAction.type === "delete" ? "bg-rose-600 hover:bg-rose-700" : "bg-slate-900 hover:bg-black"
                }`}
                onClick={onConfirmAction}
                disabled={isDeleting || isUpdating}
              >
                {confirmAction.type === "delete" ? (isDeleting ? "Deleting..." : "OK, Delete") : isUpdating ? "Saving..." : "OK, Update"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {resetTargetDriverId ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">Reset Driver Password</h3>
            <p className="mt-2 text-sm text-slate-600">
              Set a temporary password. Driver will be forced to change password at next login.
            </p>
            <input
              className="mt-4 w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
              value={resetTempPassword}
              onChange={(e) => setResetTempPassword(e.target.value)}
              placeholder="Temporary Password"
            />
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => {
                  setResetTargetDriverId(null);
                  setResetTempPassword("");
                }}
                disabled={isResettingPassword}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                onClick={onResetPassword}
                disabled={isResettingPassword}
              >
                {isResettingPassword ? "Resetting..." : "Reset"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
