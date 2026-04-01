import { useEffect, useMemo, useState } from "react";
import { CalendarClock, Eye, Pencil, Plus, Save, Search, Trash2 } from "lucide-react";
import { toast } from "react-toastify";
import {
  useCreateDriverAssignmentMutation,
  useDeleteDriverAssignmentMutation,
  useGetDriversQuery,
  useGetOperationsExecutionsQuery,
  useGetRoutesQuery,
  useGetVehiclesQuery,
  useLazyGetOperationExecutionDetailQuery,
  useUpdateDriverAssignmentMutation,
} from "../../features/companyAdmin/companyAdminApi";
import {
  extractApiErrorMessage,
  extractApiSuccessMessage,
  isoToLocalDateTimeInput,
  localDateTimeInputToIso,
} from "../../utils/adminUi";
import AdminModal from "../../components/companyAdmin/AdminModal";

const STATUS_OPTIONS = [
  { value: "all", label: "All Status" },
  { value: "ASSIGNED", label: "Assigned" },
  { value: "IN_ROUTE", label: "In Route" },
  { value: "COMPLETED", label: "Completed" },
];

const INITIAL_DRAFT = {
  driverId: "",
  route: "",
  vehicle: "",
  scheduled_at: "",
  notes: "",
};

const badgeClass = (status) => {
  if (status === "ASSIGNED") return "bg-blue-50 text-blue-700 border-blue-200";
  if (status === "IN_ROUTE") return "bg-amber-50 text-amber-700 border-amber-200";
  if (status === "COMPLETED") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  return "bg-rose-50 text-rose-700 border-rose-200";
};

const formatMoney = (value) => {
  const parsed = Number(value || 0);
  if (Number.isNaN(parsed)) return "0.00";
  return parsed.toFixed(2);
};

const formatDateTime = (value) => {
  if (!value) return "-";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "-";
  return dt.toLocaleString();
};

export default function CompanySchedulePage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [opsDate, setOpsDate] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [draft, setDraft] = useState(INITIAL_DRAFT);
  const [editingAssignment, setEditingAssignment] = useState(null);
  const [editDraft, setEditDraft] = useState(INITIAL_DRAFT);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [isExecutionOpen, setIsExecutionOpen] = useState(false);
  const [executionDetail, setExecutionDetail] = useState(null);

  const { data: drivers = [] } = useGetDriversQuery({ search: "" });
  const { data: routes = [] } = useGetRoutesQuery({});
  const { data: vehicles = [] } = useGetVehiclesQuery();
  const {
    data: operationsData = { kpis: {}, results: [] },
    isLoading: isOperationsLoading,
    error: operationsError,
  } = useGetOperationsExecutionsQuery(
    { date: opsDate, search, status },
    { pollingInterval: 15000 }
  );
  const [loadExecutionDetail, { isFetching: isExecutionLoading, error: executionError }] =
    useLazyGetOperationExecutionDetailQuery();

  const [createAssignment, { isLoading: isCreating, error: createError }] = useCreateDriverAssignmentMutation();
  const [updateAssignment, { isLoading: isUpdating, error: updateError }] = useUpdateDriverAssignmentMutation();
  const [deleteAssignment, { isLoading: isDeleting, error: deleteError }] = useDeleteDriverAssignmentMutation();

  const executionByAssignmentId = useMemo(
    () =>
      (operationsData?.results || []).reduce((acc, item) => {
        acc[item.assignment_id] = item;
        return acc;
      }, {}),
    [operationsData]
  );

  const displayedAssignments = useMemo(
    () =>
      (operationsData?.results || []).map((item) => ({
        id: item.assignment_id,
        driver: item.driver?.id,
        driver_name: item.driver?.name || "-",
        driver_mobile_number: item.driver?.mobile_number || "-",
        route: item.route?.id,
        route_name: item.route?.name || "-",
        vehicle: item.vehicle?.id,
        vehicle_name: item.vehicle?.name || "-",
        vehicle_number_plate: item.vehicle?.number_plate || "-",
        scheduled_at: item.scheduled_at,
        status: item.status,
        notes: "",
      })),
    [operationsData]
  );

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(operationsError) ||
      extractApiErrorMessage(createError) ||
      extractApiErrorMessage(updateError) ||
      extractApiErrorMessage(deleteError) ||
      extractApiErrorMessage(executionError),
    [operationsError, createError, updateError, deleteError, executionError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `schedule-error-${feedback}` });
    }
  }, [feedback]);

  const onSearch = (e) => {
    e.preventDefault();
    setSearch(searchInput.trim());
  };

  const onCreateAssignment = async (e) => {
    e.preventDefault();
    if (!draft.driverId) return;
    try {
      const response = await createAssignment({
        driverId: draft.driverId,
        body: {
          route: draft.route,
          vehicle: draft.vehicle,
          scheduled_at: localDateTimeInputToIso(draft.scheduled_at),
          notes: draft.notes,
        },
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setDraft(INITIAL_DRAFT);
      setIsCreateOpen(false);
    } catch {
      // handled by mutation state
    }
  };

  const startEdit = (assignment) => {
    if (assignment.status !== "ASSIGNED") return;
    setEditingAssignment(assignment);
    setEditDraft({
      driverId: assignment.driver,
      route: assignment.route,
      vehicle: assignment.vehicle,
      scheduled_at: isoToLocalDateTimeInput(assignment.scheduled_at),
      notes: assignment.notes || "",
    });
  };

  const onSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingAssignment) return;
    try {
      const response = await updateAssignment({
        driverId: editDraft.driverId,
        assignmentId: editingAssignment.id,
        body: {
          route: editDraft.route,
          vehicle: editDraft.vehicle,
          scheduled_at: localDateTimeInputToIso(editDraft.scheduled_at),
          notes: editDraft.notes,
        },
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setEditingAssignment(null);
    } catch {
      // handled by mutation state
    }
  };

  const onDeleteAssignment = async () => {
    if (!confirmDelete) return;
    try {
      const response = await deleteAssignment({
        driverId: confirmDelete.driverId,
        assignmentId: confirmDelete.assignmentId,
      }).unwrap();
      const successMessage = extractApiSuccessMessage(response);
      if (successMessage) toast.success(successMessage);
      setConfirmDelete(null);
    } catch {
      // handled by mutation state
    }
  };

  const onOpenExecution = async (assignmentId) => {
    try {
      const payload = await loadExecutionDetail(assignmentId).unwrap();
      setExecutionDetail(payload);
      setIsExecutionOpen(true);
    } catch {
      // handled by hook error + toast
    }
  };

  const kpis = operationsData?.kpis || {};

  return (
    <div className="space-y-8 p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Assignment Management</h1>
          <p className="text-slate-500 font-medium mt-1">
            Assign drivers to routes and vehicles, then monitor route execution, invoices, and stop-level activity.
          </p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-blue-700"
          onClick={() => setIsCreateOpen(true)}
        >
          <Plus size={14} /> Add Assignment
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-[11px] font-black uppercase tracking-wider text-slate-500">Total</p>
          <p className="text-2xl font-black text-slate-900 mt-1">{kpis.total_assignments ?? 0}</p>
        </div>
        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
          <p className="text-[11px] font-black uppercase tracking-wider text-blue-700">Assigned</p>
          <p className="text-2xl font-black text-blue-900 mt-1">{kpis.assigned_count ?? 0}</p>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-[11px] font-black uppercase tracking-wider text-amber-700">In Route</p>
          <p className="text-2xl font-black text-amber-900 mt-1">{kpis.in_route_count ?? 0}</p>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-[11px] font-black uppercase tracking-wider text-emerald-700">Completed</p>
          <p className="text-2xl font-black text-emerald-900 mt-1">{kpis.completed_count ?? 0}</p>
        </div>
        <div className="rounded-2xl border border-slate-300 bg-slate-900 p-4">
          <p className="text-[11px] font-black uppercase tracking-wider text-slate-300">Invoice Total</p>
          <p className="text-2xl font-black text-white mt-1">Rs {formatMoney(kpis.total_invoice_amount)}</p>
        </div>
      </div>

      <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-8 border-b border-slate-100 bg-slate-50/50 flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
          <form className="flex gap-2 w-full lg:max-w-xl" onSubmit={onSearch}>
            <div className="relative flex-1">
              <Search size={14} className="absolute top-1/2 -translate-y-1/2 left-3 text-slate-400" />
              <input
                className="w-full bg-white border border-slate-200 rounded-xl px-9 py-2.5 text-sm font-semibold outline-none"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search driver, route, vehicle, number plate..."
              />
            </div>
            <button type="submit" className="px-4 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest">
              Search
            </button>
          </form>

          <div className="flex flex-wrap items-center gap-2">
            <input
              type="date"
              className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-black uppercase tracking-widest outline-none"
              value={opsDate}
              onChange={(e) => setOpsDate(e.target.value)}
            />
            <select
              className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-black uppercase tracking-widest outline-none"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {isOperationsLoading ? (
          <p className="p-8 text-sm text-slate-500">Loading assignments and operations...</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {displayedAssignments.map((assignment) => {
              const execution = executionByAssignmentId[assignment.id];
              const isAssigned = assignment.status === "ASSIGNED";
              return (
                <div key={assignment.id} className="p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="space-y-1">
                    <p className="text-sm font-black text-slate-900">{assignment.driver_name}</p>
                    <p className="text-xs text-slate-600 font-semibold">{assignment.driver_mobile_number}</p>
                    <p className="text-xs text-slate-600 font-semibold">
                      {assignment.route_name} | {assignment.vehicle_name} ({assignment.vehicle_number_plate})
                    </p>
                    <p className="text-xs text-slate-500 font-semibold inline-flex items-center gap-1">
                      <CalendarClock size={13} /> {new Date(assignment.scheduled_at).toLocaleString()}
                    </p>
                    {assignment.notes ? <p className="text-xs text-slate-500">Notes: {assignment.notes}</p> : null}
                    {execution ? (
                      <div className="flex flex-wrap gap-2 pt-1">
                        <span className="px-2 py-1 rounded-lg bg-slate-100 text-[10px] font-black text-slate-700">
                          Stops {execution.progress?.completed ?? 0}/{execution.progress?.total ?? 0}
                        </span>
                        <span className="px-2 py-1 rounded-lg bg-slate-100 text-[10px] font-black text-slate-700">
                          Invoice Rs {formatMoney(execution.invoice_total)}
                        </span>
                        <span className="px-2 py-1 rounded-lg bg-slate-100 text-[10px] font-black text-slate-700">
                          Loaded Qty {execution.inventory_loaded_quantity ?? 0}
                        </span>
                        {execution.current_stop?.shop_name ? (
                          <span className="px-2 py-1 rounded-lg bg-blue-50 border border-blue-100 text-[10px] font-black text-blue-700">
                            Current: {execution.current_stop.shop_name}
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${badgeClass(assignment.status)}`}>
                      {assignment.status}
                    </span>
                    <button
                      type="button"
                      className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-violet-100 text-violet-600 hover:bg-violet-50 transition-all inline-flex items-center gap-1"
                      onClick={() => onOpenExecution(assignment.id)}
                      disabled={isExecutionLoading}
                    >
                      <Eye size={12} /> Execution
                    </button>
                    {isAssigned ? (
                      <button
                        type="button"
                        className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-blue-100 text-blue-600 hover:bg-blue-50 transition-all inline-flex items-center gap-1"
                        onClick={() => startEdit(assignment)}
                        disabled={isUpdating}
                      >
                        <Pencil size={12} /> Edit
                      </button>
                    ) : null}
                    {isAssigned ? (
                      <button
                        type="button"
                        className="text-[10px] font-black uppercase tracking-widest px-3 py-2 rounded-xl border border-rose-100 text-rose-600 hover:bg-rose-50 transition-all inline-flex items-center gap-1"
                        onClick={() => setConfirmDelete({ driverId: assignment.driver, assignmentId: assignment.id })}
                        disabled={isDeleting}
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
            {!displayedAssignments.length ? <p className="p-8 text-sm text-slate-500">No assignments found.</p> : null}
          </div>
        )}
      </div>

      <AdminModal
        isOpen={isCreateOpen}
        title="Add Assignment"
        description="Select driver, route, vehicle, and schedule time."
        onClose={() => setIsCreateOpen(false)}
      >
        <form className="space-y-4" onSubmit={onCreateAssignment}>
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={draft.driverId}
            onChange={(e) => setDraft((prev) => ({ ...prev, driverId: e.target.value }))}
            required
          >
            <option value="">Select Driver</option>
            {drivers.map((driver) => (
              <option key={driver.id} value={driver.id}>
                {driver.name} ({driver.mobile_number})
              </option>
            ))}
          </select>
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={draft.route}
            onChange={(e) => setDraft((prev) => ({ ...prev, route: e.target.value }))}
            required
          >
            <option value="">Select Route</option>
            {routes.map((route) => (
              <option key={route.id} value={route.id}>
                {route.route_name}
              </option>
            ))}
          </select>
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={draft.vehicle}
            onChange={(e) => setDraft((prev) => ({ ...prev, vehicle: e.target.value }))}
            required
          >
            <option value="">Select Vehicle</option>
            {vehicles.map((vehicle) => (
              <option key={vehicle.id} value={vehicle.id}>
                {vehicle.name} ({vehicle.number_plate})
              </option>
            ))}
          </select>
          <input
            type="datetime-local"
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={draft.scheduled_at}
            onChange={(e) => setDraft((prev) => ({ ...prev, scheduled_at: e.target.value }))}
            required
          />
          <textarea
            className="w-full min-h-[90px] bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={draft.notes}
            onChange={(e) => setDraft((prev) => ({ ...prev, notes: e.target.value }))}
            placeholder="Notes (optional)"
          />
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
              <Save size={14} /> {isCreating ? "Creating..." : "Create Assignment"}
            </button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        isOpen={!!editingAssignment}
        title="Edit Assignment"
        description="Update the driver assignment details."
        onClose={() => setEditingAssignment(null)}
      >
        <form className="space-y-4" onSubmit={onSaveEdit}>
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.driverId}
            onChange={(e) => setEditDraft((prev) => ({ ...prev, driverId: e.target.value }))}
            required
          >
            <option value="">Select Driver</option>
            {drivers.map((driver) => (
              <option key={driver.id} value={driver.id}>
                {driver.name} ({driver.mobile_number})
              </option>
            ))}
          </select>
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.route}
            onChange={(e) => setEditDraft((prev) => ({ ...prev, route: e.target.value }))}
            required
          >
            <option value="">Select Route</option>
            {routes.map((route) => (
              <option key={route.id} value={route.id}>
                {route.route_name}
              </option>
            ))}
          </select>
          <select
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.vehicle}
            onChange={(e) => setEditDraft((prev) => ({ ...prev, vehicle: e.target.value }))}
            required
          >
            <option value="">Select Vehicle</option>
            {vehicles.map((vehicle) => (
              <option key={vehicle.id} value={vehicle.id}>
                {vehicle.name} ({vehicle.number_plate})
              </option>
            ))}
          </select>
          <input
            type="datetime-local"
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.scheduled_at}
            onChange={(e) => setEditDraft((prev) => ({ ...prev, scheduled_at: e.target.value }))}
            required
          />
          <textarea
            className="w-full min-h-[90px] bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold outline-none"
            value={editDraft.notes}
            onChange={(e) => setEditDraft((prev) => ({ ...prev, notes: e.target.value }))}
            placeholder="Notes (optional)"
          />
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700"
              onClick={() => setEditingAssignment(null)}
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

      <AdminModal
        isOpen={isExecutionOpen}
        title="Execution Timeline"
        description="Driver run, stop-by-stop status, loaded inventory, ordered items, invoices, and event timeline."
        onClose={() => {
          setIsExecutionOpen(false);
          setExecutionDetail(null);
        }}
      >
        {isExecutionLoading ? (
          <p className="text-sm text-slate-500">Loading execution detail...</p>
        ) : executionDetail ? (
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-[11px] font-black uppercase tracking-wider text-slate-500">Assignment</p>
                <p className="text-sm font-black text-slate-900 mt-1">{executionDetail.assignment?.route?.name}</p>
                <p className="text-xs text-slate-600">{executionDetail.assignment?.driver?.name}</p>
                <p className="text-xs text-slate-600">{executionDetail.assignment?.vehicle?.name} ({executionDetail.assignment?.vehicle?.number_plate})</p>
                <p className="text-xs text-slate-500 mt-1">Scheduled: {formatDateTime(executionDetail.assignment?.scheduled_at)}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-[11px] font-black uppercase tracking-wider text-slate-500">Run Summary</p>
                <p className="text-xs text-slate-700 mt-1">Status: <span className="font-bold">{executionDetail.run?.status || executionDetail.assignment?.status}</span></p>
                <p className="text-xs text-slate-700">Started: {formatDateTime(executionDetail.run?.started_at)}</p>
                <p className="text-xs text-slate-700">Completed: {formatDateTime(executionDetail.run?.completed_at)}</p>
                <p className="text-xs text-slate-700 mt-1">Invoice Total: <span className="font-bold">Rs {formatMoney(executionDetail.summary?.invoice_total)}</span></p>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 text-xs font-black uppercase tracking-wider text-slate-600">
                Stops
              </div>
              <div className="max-h-56 overflow-auto divide-y divide-slate-100">
                {(executionDetail.stops || []).map((stop) => (
                  <div key={stop.stop_id} className="px-4 py-3">
                    <p className="text-sm font-black text-slate-900">#{stop.position} {stop.shop?.name}</p>
                    <p className="text-xs text-slate-600">Status: {stop.status} | Invoice: {stop.invoice_number || "-"}</p>
                    <p className="text-xs text-slate-600">Check-in: {formatDateTime(stop.check_in_at)} | Check-out: {formatDateTime(stop.check_out_at)}</p>
                    {stop.skip_reason ? <p className="text-xs text-rose-600">Skip reason: {stop.skip_reason}</p> : null}
                    {(stop.ordered_items || []).length ? (
                      <p className="text-xs text-slate-700 mt-1">
                        Ordered: {(stop.ordered_items || []).map((item) => `${item.name} x ${item.quantity}`).join(", ")}
                      </p>
                    ) : null}
                  </div>
                ))}
                {!(executionDetail.stops || []).length ? (
                  <p className="px-4 py-3 text-sm text-slate-500">No stop activity yet.</p>
                ) : null}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 text-xs font-black uppercase tracking-wider text-slate-600">
                Loaded Inventory
              </div>
              <div className="max-h-40 overflow-auto divide-y divide-slate-100">
                {(executionDetail.inventory?.loaded_items || []).map((item) => (
                  <div key={item.product_id} className="px-4 py-2 text-xs text-slate-700 flex items-center justify-between">
                    <span>{item.product_name}</span>
                    <span className="font-bold">{item.quantity}</span>
                  </div>
                ))}
                {!(executionDetail.inventory?.loaded_items || []).length ? (
                  <p className="px-4 py-3 text-sm text-slate-500">No inventory loaded.</p>
                ) : null}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 text-xs font-black uppercase tracking-wider text-slate-600">
                Event Timeline
              </div>
              <div className="max-h-44 overflow-auto divide-y divide-slate-100">
                {(executionDetail.events || []).map((event, index) => (
                  <div key={`${event.type}-${index}`} className="px-4 py-2 text-xs text-slate-700">
                    <p className="font-bold">{event.label}</p>
                    <p className="text-slate-500">{formatDateTime(event.timestamp)}</p>
                  </div>
                ))}
                {!(executionDetail.events || []).length ? (
                  <p className="px-4 py-3 text-sm text-slate-500">No events available.</p>
                ) : null}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Select an assignment to view execution details.</p>
        )}
      </AdminModal>

      {confirmDelete ? (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-6">
            <h3 className="text-base font-black text-slate-900">Delete Assignment</h3>
            <p className="mt-2 text-sm text-slate-600">Are you sure you want to delete this assignment?</p>
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-black uppercase tracking-widest"
                onClick={() => setConfirmDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                onClick={onDeleteAssignment}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
