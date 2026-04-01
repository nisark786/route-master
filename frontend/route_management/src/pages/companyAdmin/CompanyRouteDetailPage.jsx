import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Save, Trash2 } from "lucide-react";
import { toast } from "react-toastify";
import {
  useAddShopToRouteMutation,
  useDeleteRouteMutation,
  useGetAvailableRouteShopsQuery,
  useGetRouteDetailQuery,
  useRemoveShopFromRouteMutation,
  useUpdateRouteMutation,
  useUpdateRouteShopPositionMutation,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage, extractApiSuccessMessage } from "../../utils/adminUi";

export default function CompanyRouteDetailPage() {
  const { routeId } = useParams();
  const navigate = useNavigate();

  const { data: route, isLoading, error } = useGetRouteDetailQuery(routeId, { skip: !routeId });
  const { data: availableShops = [] } = useGetAvailableRouteShopsQuery();
  const [updateRoute, { isLoading: isUpdating, error: updateError }] = useUpdateRouteMutation();
  const [deleteRoute, { isLoading: isDeleting, error: deleteError }] = useDeleteRouteMutation();
  const [addShopToRoute, { isLoading: isAddingShop, error: addShopError }] = useAddShopToRouteMutation();
  const [removeShopFromRoute, { isLoading: isRemovingShop, error: removeShopError }] = useRemoveShopFromRouteMutation();
  const [updateRouteShopPosition, { isLoading: isMovingShop, error: moveShopError }] = useUpdateRouteShopPositionMutation();

  const [editDraft, setEditDraft] = useState({ route_name: "", start_point: "", end_point: "" });
  const [selectedShopId, setSelectedShopId] = useState("");
  const [selectedPosition, setSelectedPosition] = useState(1);
  const [confirmDeleteRoute, setConfirmDeleteRoute] = useState(false);
  const [confirmRemoveShopId, setConfirmRemoveShopId] = useState("");
  const [confirmUpdateRoute, setConfirmUpdateRoute] = useState(false);

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(error) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(deleteError) ||
      extractApiErrorMessage(addShopError) ||
      extractApiErrorMessage(removeShopError) ||
      extractApiErrorMessage(moveShopError),
    [error, updateError, deleteError, addShopError, removeShopError, moveShopError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `route-detail-error-${feedback}` });
    }
  }, [feedback]);

  const currentShops = route?.route_shops || [];

  const onSyncDraft = () => {
    if (!route) return;
    setEditDraft({
      route_name: route.route_name || "",
      start_point: route.start_point || "",
      end_point: route.end_point || "",
    });
  };

  const onConfirmUpdateRoute = async () => {
    const body = Object.fromEntries(
      Object.entries(editDraft).filter(([, value]) => String(value || "").trim() !== "")
    );
    if (!Object.keys(body).length) {
      setConfirmUpdateRoute(false);
      return;
    }
    try {
      const response = await updateRoute({ routeId, body }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setConfirmUpdateRoute(false);
    } catch {
      // handled by mutation state
    }
  };

  const onDeleteRoute = async () => {
    try {
      const response = await deleteRoute(routeId).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      navigate("/company/routes", { replace: true });
    } catch {
      // handled by mutation state
    }
  };

  const onAddShop = async () => {
    if (!selectedShopId) return;
    try {
      const response = await addShopToRoute({
        routeId,
        body: {
          shop_id: selectedShopId,
          position: Number(selectedPosition || currentShops.length + 1),
        },
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setSelectedShopId("");
      setSelectedPosition((currentShops.length || 0) + 2);
    } catch {
      // handled by mutation state
    }
  };

  const onRemoveShop = async () => {
    if (!confirmRemoveShopId) return;
    try {
      const response = await removeShopFromRoute({ routeId, shopId: confirmRemoveShopId }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setConfirmRemoveShopId("");
    } catch {
      // handled by mutation state
    }
  };

  const onChangePosition = async (shopId, position) => {
    try {
      const response = await updateRouteShopPosition({ routeId, shopId, position: Number(position || 1) }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
    } catch {
      // handled by mutation state
    }
  };

  return (
    <div className="space-y-8 p-8">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/company/routes" className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-500 hover:text-slate-700 mb-3">
            <ArrowLeft size={14} /> Back to Routes
          </Link>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Route Details</h1>
          <p className="text-slate-500 font-medium mt-1">Edit route info and manage ordered shop sequence.</p>
        </div>
        <button
          type="button"
          className="px-4 py-2 rounded-xl border border-rose-100 text-rose-600 text-xs font-black uppercase tracking-widest hover:bg-rose-50"
          onClick={() => setConfirmDeleteRoute(true)}
          disabled={isDeleting || isLoading}
        >
          <Trash2 size={12} className="inline mr-1" />
          Delete Route
        </button>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm text-sm text-slate-500">Loading route details...</div>
      ) : route ? (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
          <div className="xl:col-span-4 space-y-6">
            <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-black text-slate-900">Route Info</h2>
                <button type="button" onClick={onSyncDraft} className="text-xs font-black uppercase tracking-widest text-slate-500">
                  Load Current
                </button>
              </div>
              <input
                className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
                placeholder={route.route_name}
                value={editDraft.route_name}
                onChange={(e) => setEditDraft((prev) => ({ ...prev, route_name: e.target.value }))}
              />
              <input
                className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
                placeholder={route.start_point}
                value={editDraft.start_point}
                onChange={(e) => setEditDraft((prev) => ({ ...prev, start_point: e.target.value }))}
              />
              <input
                className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
                placeholder={route.end_point}
                value={editDraft.end_point}
                onChange={(e) => setEditDraft((prev) => ({ ...prev, end_point: e.target.value }))}
              />
              <button
                type="button"
                className="w-full bg-slate-900 text-white font-black text-xs uppercase tracking-[0.2em] rounded-2xl py-3 hover:bg-black disabled:opacity-60"
                onClick={() => setConfirmUpdateRoute(true)}
                disabled={isUpdating}
              >
                <Save size={14} className="inline mr-2" />
                {isUpdating ? "Saving..." : "Update Route"}
              </button>
            </div>

            <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm space-y-3">
              <h2 className="text-lg font-black text-slate-900">Add Shop to Route</h2>
              <select
                className="w-full bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
                value={selectedShopId}
                onChange={(e) => setSelectedShopId(e.target.value)}
              >
                <option value="">Select unassigned shop</option>
                {availableShops.map((shop) => (
                  <option key={shop.id} value={shop.id}>
                    {shop.name} ({shop.owner_name})
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                className="w-full bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
                value={selectedPosition}
                onChange={(e) => setSelectedPosition(Number(e.target.value || 1))}
                placeholder="Position"
              />
              <p className="text-[11px] text-slate-500 font-semibold">
                If position already exists, next shops shift by +1 automatically.
              </p>
              <button
                type="button"
                className="w-full bg-blue-600 text-white font-black text-xs uppercase tracking-[0.2em] rounded-2xl py-3 hover:bg-blue-700 disabled:opacity-60"
                onClick={onAddShop}
                disabled={!selectedShopId || isAddingShop}
              >
                <Plus size={14} className="inline mr-2" />
                {isAddingShop ? "Adding..." : "Add Shop"}
              </button>
            </div>
          </div>

          <div className="xl:col-span-8 bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-8 border-b border-slate-100 bg-slate-50/50">
              <h2 className="text-lg font-black text-slate-900 tracking-tight">{route.route_name}</h2>
              <p className="text-xs text-slate-600 font-semibold">
                {route.start_point} {"->"} {route.end_point}
              </p>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">
                Total Shops: {currentShops.length}
              </p>
            </div>

            <div className="divide-y divide-slate-100">
              {currentShops.map((assignment) => (
                <div key={assignment.id} className="p-6 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-black text-slate-900">
                      #{assignment.position} - {assignment.shop.name}
                    </p>
                    <p className="text-xs text-slate-600 font-semibold">
                      Owner: {assignment.shop.owner_name} | {assignment.shop.location || "No location"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={1}
                      max={currentShops.length}
                      className="w-20 bg-slate-50 border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold outline-none"
                      defaultValue={assignment.position}
                      onBlur={(e) => onChangePosition(assignment.shop.id, Number(e.target.value || assignment.position))}
                      disabled={isMovingShop}
                    />
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-rose-100 text-rose-600 hover:bg-rose-50 transition-all inline-flex items-center gap-1"
                      onClick={() => setConfirmRemoveShopId(assignment.shop.id)}
                      disabled={isRemovingShop}
                    >
                      <Trash2 size={12} /> Remove
                    </button>
                  </div>
                </div>
              ))}
              {!currentShops.length ? <p className="p-8 text-sm text-slate-500">No shops assigned to this route yet.</p> : null}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm text-sm text-slate-500">Route not found.</div>
      )}

      {confirmDeleteRoute ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">Confirm Delete</h3>
            <p className="mt-2 text-sm text-slate-600">Delete this route and all assignments?</p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmDeleteRoute(false)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                onClick={onDeleteRoute}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "OK, Delete"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {confirmRemoveShopId ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">Confirm Remove Shop</h3>
            <p className="mt-2 text-sm text-slate-600">Remove this shop from the route?</p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmRemoveShopId("")}
                disabled={isRemovingShop}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                onClick={onRemoveShop}
                disabled={isRemovingShop}
              >
                {isRemovingShop ? "Removing..." : "OK, Remove"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {confirmUpdateRoute ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">Confirm Update</h3>
            <p className="mt-2 text-sm text-slate-600">Save route details changes?</p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmUpdateRoute(false)}
                disabled={isUpdating}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-black text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                onClick={onConfirmUpdateRoute}
                disabled={isUpdating}
              >
                {isUpdating ? "Saving..." : "OK, Update"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
