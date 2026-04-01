import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MapPinned, Pencil, Plus, Save, Search, Trash2 } from "lucide-react";
import { toast } from "react-toastify";
import {
  useCreateRouteMutation,
  useDeleteRouteMutation,
  useGetAvailableRouteShopsQuery,
  useLazyGetRouteDetailQuery,
  useGetRoutesQuery,
  useUpdateRouteMutation,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage, extractApiSuccessMessage } from "../../utils/adminUi";
import AdminModal from "../../components/companyAdmin/AdminModal";

const INITIAL_DRAFT = {
  route_name: "",
  start_point: "",
  end_point: "",
};

const insertAtPosition = (items, nextItem, targetPosition) => {
  const sanitized = Number.isFinite(targetPosition) ? Math.max(1, targetPosition) : items.length + 1;
  const clone = [...items];
  const bounded = Math.min(sanitized, clone.length + 1);
  clone.splice(bounded - 1, 0, nextItem);
  return clone.map((entry, index) => ({ ...entry, position: index + 1 }));
};

const normalizeRouteShops = (route) =>
  (route.route_shops || route.shops || []).map((entry, index) => {
    const shop = entry.shop || entry;
    return {
      shop_id: entry.shop_id || shop.id,
      shop_name: entry.shop_name || shop.name,
      owner_name: entry.owner_name || shop.owner_name || "",
      position: Number(entry.position || index + 1),
    };
  });

export default function CompanyRoutesPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [draft, setDraft] = useState(INITIAL_DRAFT);
  const [selectedShopId, setSelectedShopId] = useState("");
  const [selectedShopPosition, setSelectedShopPosition] = useState(1);
  const [selectedShops, setSelectedShops] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState(INITIAL_DRAFT);
  const [editSelectedShopId, setEditSelectedShopId] = useState("");
  const [editSelectedShopPosition, setEditSelectedShopPosition] = useState(1);
  const [editSelectedShops, setEditSelectedShops] = useState([]);
  const [confirmAction, setConfirmAction] = useState(null);

  const { data: routes = [], isLoading, error } = useGetRoutesQuery({ search });
  const [fetchRouteDetail] = useLazyGetRouteDetailQuery();
  const { data: availableShops = [], isLoading: isShopsLoading } = useGetAvailableRouteShopsQuery();
  const [createRoute, { isLoading: isCreating, error: createError }] = useCreateRouteMutation();
  const [updateRoute, { isLoading: isUpdating, error: updateError }] = useUpdateRouteMutation();
  const [deleteRoute, { isLoading: isDeleting, error: deleteError }] = useDeleteRouteMutation();

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(error) ||
      extractApiErrorMessage(createError) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(deleteError),
    [error, createError, updateError, deleteError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `routes-error-${feedback}` });
    }
  }, [feedback]);

  const onSearch = (e) => {
    e.preventDefault();
    setSearch(searchInput.trim());
  };

  const addShopToList = ({ shopId, position, list, setList, setShopId, setPosition }) => {
    if (!shopId) return;
    const alreadyAdded = list.some((item) => item.shop_id === shopId);
    if (alreadyAdded) return;
    const shop = availableShops.find((item) => item.id === shopId);
    if (!shop) return;
    const next = insertAtPosition(
      list,
      { shop_id: shop.id, shop_name: shop.name, owner_name: shop.owner_name, position: list.length + 1 },
      Number(position)
    );
    setList(next);
    setShopId("");
    setPosition(next.length + 1);
  };

  const removeShopFromList = (shopId, list, setList, setPosition) => {
    const next = list
      .filter((item) => item.shop_id !== shopId)
      .map((item, index) => ({ ...item, position: index + 1 }));
    setList(next);
    setPosition(next.length + 1);
  };

  const changeShopPosition = (shopId, targetPosition, list, setList) => {
    const moving = list.find((item) => item.shop_id === shopId);
    if (!moving) return;
    const rest = list.filter((item) => item.shop_id !== shopId);
    const next = insertAtPosition(rest, moving, Number(targetPosition));
    setList(next);
  };

  const onCreateRoute = async (e) => {
    e.preventDefault();
    try {
      const response = await createRoute({
        ...draft,
        shops: selectedShops.map((item) => ({ shop_id: item.shop_id, position: item.position })),
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setDraft(INITIAL_DRAFT);
      setSelectedShops([]);
      setSelectedShopPosition(1);
      setIsCreateOpen(false);
    } catch {
      // handled by mutation state
    }
  };

  const startEdit = async (route) => {
    try {
      const detail = await fetchRouteDetail(route.id).unwrap();
      const routeShops = normalizeRouteShops(detail);
      setEditingId(detail.id || route.id);
      setEditDraft({
        route_name: detail.route_name || route.route_name || "",
        start_point: detail.start_point || route.start_point || "",
        end_point: detail.end_point || route.end_point || "",
      });
      setEditSelectedShops(routeShops);
      setEditSelectedShopId("");
      setEditSelectedShopPosition(routeShops.length + 1 || 1);
    } catch (err) {
      toast.error(extractApiErrorMessage(err) || "Unable to load route details.");
    }
  };

  const onSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingId) return;
    try {
      const response = await updateRoute({
        routeId: editingId,
        body: {
          ...editDraft,
          shops: editSelectedShops.map((item) => ({ shop_id: item.shop_id, position: item.position })),
        },
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setEditingId(null);
    } catch {
      // handled by mutation state
    }
  };

  const onDeleteRoute = async () => {
    if (!confirmAction?.routeId) return;
    try {
      const response = await deleteRoute(confirmAction.routeId).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setConfirmAction(null);
    } catch {
      // handled by mutation state
    }
  };

  return (
    <div className="space-y-8 p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Route Management</h1>
          <p className="text-slate-500 font-medium mt-1">Create routes, assign shops, and control delivery sequence.</p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
          onClick={() => setIsCreateOpen(true)}
        >
          <Plus size={14} /> Add Route
        </button>
      </div>

      <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-8 border-b border-slate-100 bg-slate-50/50 space-y-4">
          <h2 className="text-lg font-black text-slate-900 tracking-tight">Routes</h2>
          <form className="flex gap-2" onSubmit={onSearch}>
            <div className="relative flex-1">
              <Search size={14} className="absolute top-1/2 -translate-y-1/2 left-3 text-slate-400" />
              <input
                className="w-full bg-white border border-slate-200 rounded-xl px-9 py-2.5 text-sm font-semibold outline-none"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search route name, start, or end..."
              />
            </div>
            <button type="submit" className="px-4 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest">
              Search
            </button>
          </form>
        </div>

        {isLoading ? (
          <p className="p-8 text-sm text-slate-500">Loading routes...</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {routes.map((route) => (
              <div key={route.id} className="p-6 flex items-center justify-between gap-4">
                <Link to={`/company/routes/${route.id}`} className="flex items-start gap-3 min-w-0">
                  <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <MapPinned size={18} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-black text-slate-900 truncate">{route.route_name}</p>
                    <p className="text-xs text-slate-600 font-semibold truncate">
                      {route.start_point} {"->"} {route.end_point}
                    </p>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
                      Shops: {route.shops_count}
                    </p>
                  </div>
                </Link>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-blue-100 text-blue-600 hover:bg-blue-50 transition-all inline-flex items-center gap-1"
                    onClick={() => startEdit(route)}
                    disabled={isUpdating}
                  >
                    <Pencil size={12} /> Edit
                  </button>
                  <button
                    type="button"
                    className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-rose-100 text-rose-600 hover:bg-rose-50 transition-all inline-flex items-center gap-1"
                    onClick={() => setConfirmAction({ type: "delete", routeId: route.id })}
                    disabled={isDeleting}
                  >
                    <Trash2 size={12} /> Delete
                  </button>
                </div>
              </div>
            ))}
            {!routes.length ? <p className="p-8 text-sm text-slate-500">No routes found.</p> : null}
          </div>
        )}
      </div>

      <AdminModal
        isOpen={isCreateOpen}
        title="Add Route"
        description="Create a route and arrange its shop order."
        onClose={() => setIsCreateOpen(false)}
      >
        <form className="space-y-4" onSubmit={onCreateRoute}>
          <input
            className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={draft.route_name}
            onChange={(e) => setDraft((prev) => ({ ...prev, route_name: e.target.value }))}
            placeholder="Route Name"
            required
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
              value={draft.start_point}
              onChange={(e) => setDraft((prev) => ({ ...prev, start_point: e.target.value }))}
              placeholder="Start Point"
              required
            />
            <input
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
              value={draft.end_point}
              onChange={(e) => setDraft((prev) => ({ ...prev, end_point: e.target.value }))}
              placeholder="End Point"
              required
            />
          </div>

          <div className="rounded-xl border border-slate-200 p-3 space-y-3">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Add Unassigned Shops</p>
            <select
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
              value={selectedShopId}
              onChange={(e) => setSelectedShopId(e.target.value)}
              disabled={isShopsLoading}
            >
              <option value="">Select shop</option>
              {availableShops.map((shop) => (
                <option key={shop.id} value={shop.id}>
                  {shop.name} ({shop.owner_name})
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <input
                type="number"
                min={1}
                className="flex-1 bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
                value={selectedShopPosition}
                onChange={(e) => setSelectedShopPosition(Number(e.target.value || 1))}
                placeholder="Position"
              />
              <button
                type="button"
                className="px-4 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest disabled:opacity-50"
                onClick={() =>
                  addShopToList({
                    shopId: selectedShopId,
                    position: selectedShopPosition,
                    list: selectedShops,
                    setList: setSelectedShops,
                    setShopId: setSelectedShopId,
                    setPosition: setSelectedShopPosition,
                  })
                }
                disabled={!selectedShopId}
              >
                Add
              </button>
            </div>
          </div>

          {selectedShops.length ? (
            <div className="rounded-xl border border-slate-200 divide-y divide-slate-100">
              {selectedShops.map((item) => (
                <div key={item.shop_id} className="px-3 py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-black text-slate-800 truncate">{item.shop_name}</p>
                    <p className="text-[10px] text-slate-500 font-semibold truncate">{item.owner_name}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={1}
                      max={selectedShops.length}
                      className="w-16 bg-slate-50 border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold outline-none"
                      value={item.position}
                      onChange={(e) => changeShopPosition(item.shop_id, Number(e.target.value || 1), selectedShops, setSelectedShops)}
                    />
                    <button
                      type="button"
                      className="text-rose-600 hover:text-rose-700"
                      onClick={() => removeShopFromList(item.shop_id, selectedShops, setSelectedShops, setSelectedShopPosition)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

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
              <Save size={14} /> {isCreating ? "Creating..." : "Create Route"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={!!editingId}
        title="Edit Route"
        description="Update route details and reorder shops."
        onClose={() => setEditingId(null)}
      >
        <form className="space-y-4" onSubmit={onSaveEdit}>
          <input
            className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.route_name}
            onChange={(e) => setEditDraft((prev) => ({ ...prev, route_name: e.target.value }))}
            placeholder="Route Name"
            required
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.start_point}
              onChange={(e) => setEditDraft((prev) => ({ ...prev, start_point: e.target.value }))}
              placeholder="Start Point"
              required
            />
            <input
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
              value={editDraft.end_point}
              onChange={(e) => setEditDraft((prev) => ({ ...prev, end_point: e.target.value }))}
              placeholder="End Point"
              required
            />
          </div>

          <div className="rounded-xl border border-slate-200 p-3 space-y-3">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Add More Unassigned Shops</p>
            <select
              className="w-full bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
              value={editSelectedShopId}
              onChange={(e) => setEditSelectedShopId(e.target.value)}
              disabled={isShopsLoading}
            >
              <option value="">Select shop</option>
              {availableShops.map((shop) => (
                <option key={shop.id} value={shop.id}>
                  {shop.name} ({shop.owner_name})
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <input
                type="number"
                min={1}
                className="flex-1 bg-slate-50 border-slate-200 rounded-xl px-3 py-2.5 text-sm font-bold outline-none"
                value={editSelectedShopPosition}
                onChange={(e) => setEditSelectedShopPosition(Number(e.target.value || 1))}
                placeholder="Position"
              />
              <button
                type="button"
                className="px-4 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest disabled:opacity-50"
                onClick={() =>
                  addShopToList({
                    shopId: editSelectedShopId,
                    position: editSelectedShopPosition,
                    list: editSelectedShops,
                    setList: setEditSelectedShops,
                    setShopId: setEditSelectedShopId,
                    setPosition: setEditSelectedShopPosition,
                  })
                }
                disabled={!editSelectedShopId}
              >
                Add
              </button>
            </div>
          </div>

          {editSelectedShops.length ? (
            <div className="rounded-xl border border-slate-200 divide-y divide-slate-100">
              {editSelectedShops.map((item) => (
                <div key={item.shop_id} className="px-3 py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-black text-slate-800 truncate">{item.shop_name}</p>
                    <p className="text-[10px] text-slate-500 font-semibold truncate">{item.owner_name}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={1}
                      max={editSelectedShops.length}
                      className="w-16 bg-slate-50 border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold outline-none"
                      value={item.position}
                      onChange={(e) =>
                        changeShopPosition(item.shop_id, Number(e.target.value || 1), editSelectedShops, setEditSelectedShops)
                      }
                    />
                    <button
                      type="button"
                      className="text-rose-600 hover:text-rose-700"
                      onClick={() =>
                        removeShopFromList(item.shop_id, editSelectedShops, setEditSelectedShops, setEditSelectedShopPosition)
                      }
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

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
            <h3 className="text-base font-black text-slate-900">Confirm Delete</h3>
            <p className="mt-2 text-sm text-slate-600">Delete this route and its shop assignments?</p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmAction(null)}
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
    </div>
  );
}
