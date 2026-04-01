import { useEffect, useMemo, useState } from "react";
import { CarFront, Pencil, Plus, Save, Trash2 } from "lucide-react";
import { toast } from "react-toastify";
import {
  useCreateVehicleMutation,
  useDeleteVehicleMutation,
  useGetVehiclesQuery,
  useUpdateVehicleMutation,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage, extractApiSuccessMessage } from "../../utils/adminUi";
import AdminModal from "../../components/companyAdmin/AdminModal";

const STATUS_OPTIONS = [
  { value: "AVAILABLE", label: "Available" },
  { value: "ON_ROUTE", label: "On Route" },
  { value: "RENOVATION", label: "Renovation" },
];

export default function CompanyVehiclesPage() {
  const { data: vehicles = [], isLoading, error } = useGetVehiclesQuery();
  const [createVehicle, { isLoading: isCreating, error: createError }] = useCreateVehicleMutation();
  const [updateVehicle, { isLoading: isUpdating, error: updateError }] = useUpdateVehicleMutation();
  const [deleteVehicle, { isLoading: isDeleting, error: deleteError }] = useDeleteVehicleMutation();

  const [draft, setDraft] = useState({
    name: "",
    number_plate: "",
    status: "AVAILABLE",
  });
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState({
    name: "",
    number_plate: "",
    status: "AVAILABLE",
  });
  const [confirmAction, setConfirmAction] = useState(null);

  const feedback = useMemo(() => {
    return (
      extractApiErrorMessage(error) ||
      extractApiErrorMessage(createError) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(deleteError)
    );
  }, [error, createError, updateError, deleteError]);

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `vehicles-error-${feedback}` });
    }
  }, [feedback]);

  const onCreateVehicle = async (e) => {
    e.preventDefault();
    try {
      const response = await createVehicle(draft).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setDraft({ name: "", number_plate: "", status: "AVAILABLE" });
      setIsCreateOpen(false);
    } catch {
      // Error from mutation state.
    }
  };

  const startEdit = (vehicle) => {
    setEditingId(vehicle.id);
    setEditDraft({
      name: vehicle.name,
      number_plate: vehicle.number_plate,
      status: vehicle.status,
    });
  };

  const saveEdit = async (e) => {
    e.preventDefault();
    if (!editingId) return;
    setConfirmAction({
      type: "update",
      vehicleId: editingId,
      body: editDraft,
    });
  };

  const removeVehicle = (vehicleId) => {
    setConfirmAction({ type: "delete", vehicleId });
  };

  const onConfirmAction = async () => {
    if (!confirmAction) return;
    try {
      if (confirmAction.type === "delete") {
        const response = await deleteVehicle(confirmAction.vehicleId).unwrap();
        const successMessage = extractApiSuccessMessage(response);
        if (successMessage) toast.success(successMessage);
        if (editingId === confirmAction.vehicleId) setEditingId(null);
      }
      if (confirmAction.type === "update") {
        const response = await updateVehicle({
          vehicleId: confirmAction.vehicleId,
          body: confirmAction.body,
        }).unwrap();
        const successMessage = extractApiSuccessMessage(response);
        if (successMessage) toast.success(successMessage);
        setEditingId(null);
      }
      setConfirmAction(null);
    } catch {
      // Error from mutation state.
    }
  };

  const statusBadgeClass = (status) => {
    if (status === "AVAILABLE") return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (status === "ON_ROUTE") return "bg-blue-50 text-blue-700 border-blue-200";
    return "bg-amber-50 text-amber-700 border-amber-200";
  };

  return (
    <div className="space-y-8 p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">Vehicle Management</h1>
        <p className="text-slate-500 font-medium mt-1">Manage company vehicles and their availability status.</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
          onClick={() => setIsCreateOpen(true)}
        >
          <Plus size={14} /> Add Vehicle
        </button>
      </div>

      <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-8 border-b border-slate-100 bg-slate-50/50">
            <h2 className="text-lg font-black text-slate-900 tracking-tight">Fleet</h2>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Current company vehicles</p>
          </div>

          {isLoading ? (
            <p className="p-8 text-sm text-slate-500">Loading vehicles...</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {(vehicles || []).map((vehicle) => (
                <div key={vehicle.id} className="p-6 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                        <CarFront size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-black text-slate-900">{vehicle.name}</p>
                        <p className="text-[10px] font-bold text-slate-500 uppercase">{vehicle.number_plate}</p>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${statusBadgeClass(vehicle.status)}`}>
                      {vehicle.status.replace("_", " ")}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-blue-100 text-blue-600 hover:bg-blue-50 transition-all inline-flex items-center gap-1"
                      onClick={() => startEdit(vehicle)}
                      disabled={isUpdating}
                    >
                      <Pencil size={12} /> Edit
                    </button>
                    <button
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-rose-100 text-rose-600 hover:bg-rose-50 transition-all inline-flex items-center gap-1"
                      onClick={() => removeVehicle(vehicle.id)}
                      disabled={isDeleting}
                    >
                      <Trash2 size={12} /> Delete
                    </button>
                  </div>
                </div>
              ))}
              {!vehicles?.length ? <p className="p-8 text-sm text-slate-500">No vehicles added yet.</p> : null}
            </div>
          )}
      </div>

      <AdminModal
        isOpen={isCreateOpen}
        title="Add Vehicle"
        description="Create a new vehicle record for your fleet."
        onClose={() => setIsCreateOpen(false)}
      >
        <form className="space-y-4" onSubmit={onCreateVehicle}>
          <div>
            <label className="mb-1.5 ml-1 block text-[10px] font-black uppercase tracking-widest text-slate-400">Vehicle Name</label>
            <input
              className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={draft.name}
              onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
              placeholder="Truck 01"
              required
            />
          </div>
          <div>
            <label className="mb-1.5 ml-1 block text-[10px] font-black uppercase tracking-widest text-slate-400">Number Plate</label>
            <input
              className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold uppercase outline-none"
              value={draft.number_plate}
              onChange={(e) => setDraft((p) => ({ ...p, number_plate: e.target.value }))}
              placeholder="KL 64 B 1234"
              required
            />
          </div>
          <div>
            <label className="mb-1.5 ml-1 block text-[10px] font-black uppercase tracking-widest text-slate-400">Status</label>
            <select
              className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={draft.status}
              onChange={(e) => setDraft((p) => ({ ...p, status: e.target.value }))}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
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
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white transition-all hover:bg-black disabled:opacity-60"
              disabled={isCreating}
            >
              <Save size={14} /> {isCreating ? "Saving..." : "Create Vehicle"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={!!editingId}
        title="Edit Vehicle"
        description="Update vehicle details."
        onClose={() => setEditingId(null)}
      >
        <form className="space-y-4" onSubmit={saveEdit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.name}
              onChange={(e) => setEditDraft((p) => ({ ...p, name: e.target.value }))}
              placeholder="Vehicle Name"
              required
            />
            <input
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold uppercase outline-none"
              value={editDraft.number_plate}
              onChange={(e) => setEditDraft((p) => ({ ...p, number_plate: e.target.value }))}
              placeholder="Number Plate"
              required
            />
            <select
              className="rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.status}
              onChange={(e) => setEditDraft((p) => ({ ...p, status: e.target.value }))}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
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
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-black uppercase tracking-widest text-white transition-all hover:bg-black disabled:opacity-60"
              disabled={isUpdating}
            >
              <Save size={14} /> {isUpdating ? "Saving..." : "Save Changes"}
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
                ? "Are you sure you want to delete this vehicle? This action cannot be undone."
                : "Are you sure you want to update this vehicle details?"}
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
    </div>
  );
}
