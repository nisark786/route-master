import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Sparkles } from "lucide-react";
import { toast } from "react-toastify";

import {
  useApproveAiDispatchCopilotMutation,
  useCreateDriverAssignmentMutation,
  useGetDriversQuery,
  useGetAiDispatchCopilotMutation,
  useGetRoutesQuery,
  useTriggerAiSyncMutation,
  useGetVehiclesQuery,
} from "../../features/companyAdmin/companyAdminApi";
import { extractApiErrorMessage } from "../../utils/adminUi";

export default function CompanyCopilotPage() {
  const [dispatchTopN, setDispatchTopN] = useState(5);
  const [dispatchScheduledAt, setDispatchScheduledAt] = useState(() => {
    const target = new Date(Date.now() + 30 * 60 * 1000);
    const pad = (num) => String(num).padStart(2, "0");
    return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}T${pad(target.getHours())}:${pad(target.getMinutes())}`;
  });
  const [dispatchSuggestions, setDispatchSuggestions] = useState([]);
  const [selectedRouteIds, setSelectedRouteIds] = useState([]);
  const [unmatchedRoutes, setUnmatchedRoutes] = useState([]);
  const { data: routes = [] } = useGetRoutesQuery({ search: "" });
  const { data: drivers = [] } = useGetDriversQuery({ search: "" });
  const { data: vehicles = [] } = useGetVehiclesQuery();
  const [getAiDispatchCopilot, { isLoading: isDispatchLoading, error: dispatchError }] = useGetAiDispatchCopilotMutation();
  const [approveAiDispatchCopilot, { isLoading: isApprovingDispatch, error: approveError }] = useApproveAiDispatchCopilotMutation();
  const [createDriverAssignment] = useCreateDriverAssignmentMutation();
  const [triggerAiSync, { isLoading: isSyncing }] = useTriggerAiSyncMutation();

  const feedback = useMemo(
    () => extractApiErrorMessage(dispatchError) || extractApiErrorMessage(approveError),
    [dispatchError, approveError]
  );

  const dispatchCandidates = useMemo(() => {
    const routeCandidates = Array.isArray(routes)
      ? routes.map((route) => ({
          route_id: route.id,
          route_name: route.route_name,
          start_point: route.start_point || "",
          end_point: route.end_point || "",
          stops_count: Number(route.shops_count || 0),
        }))
      : [];

    const driverCandidates = Array.isArray(drivers)
      ? drivers.map((driver) => ({
          driver_id: driver.id,
          name: driver.name,
          status: driver.status || "AVAILABLE",
          recent_assignments_count: 0,
        }))
      : [];

    const vehicleCandidates = Array.isArray(vehicles)
      ? vehicles.map((vehicle) => ({
          vehicle_id: vehicle.id,
          name: vehicle.name,
          number_plate: vehicle.number_plate,
          status: vehicle.status || "AVAILABLE",
          fuel_percentage: Number(vehicle.fuel_percentage ?? 100),
          recent_assignments_count: 0,
        }))
      : [];

    return {
      routes: routeCandidates,
      drivers: driverCandidates,
      vehicles: vehicleCandidates,
    };
  }, [routes, drivers, vehicles]);

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `company-copilot-${feedback}` });
    }
  }, [feedback]);

  const handleSync = async () => {
    try {
      const result = await triggerAiSync().unwrap();
      if (result?.queued) {
        toast.info("AI knowledge sync started. You can keep using Copilot while it updates.");
      } else {
        toast.info("AI knowledge is already syncing. Please wait a bit.");
      }
    } catch {
      // handled by mutation state
    }
  };

  const handleDispatchCopilot = async () => {
    if (!dispatchCandidates.routes.length) {
      toast.error("Create at least one route before using Copilot.");
      return;
    }
    if (!dispatchCandidates.drivers.length) {
      toast.error("Create at least one driver before using Copilot.");
      return;
    }
    if (!dispatchCandidates.vehicles.length) {
      toast.error("Create at least one vehicle before using Copilot.");
      return;
    }

    try {
      const response = await getAiDispatchCopilot({
        top_n: Number(dispatchTopN) || 5,
        ...dispatchCandidates,
      }).unwrap();
      const suggestions = Array.isArray(response?.suggestions) ? response.suggestions : [];
      setDispatchSuggestions(suggestions);
      setSelectedRouteIds(suggestions.map((item) => item.route_id).filter(Boolean));
      setUnmatchedRoutes(Array.isArray(response?.unmatched_route_ids) ? response.unmatched_route_ids : []);
      toast.success("Dispatch copilot recommendations loaded.");
    } catch {
      // handled by RTK mutation state
    }
  };

  const handleApproveDispatch = async () => {
    if (!dispatchSuggestions.length) {
      toast.error("Generate dispatch recommendations before approval.");
      return;
    }
    if (!dispatchScheduledAt) {
      toast.error("Select scheduled time.");
      return;
    }
    const selectedSuggestions = dispatchSuggestions.filter((item) => selectedRouteIds.includes(item.route_id));
    if (!selectedSuggestions.length) {
      toast.error("Select at least one dispatch recommendation to approve.");
      return;
    }

    try {
      const response = await approveAiDispatchCopilot({
        scheduled_at: new Date(dispatchScheduledAt).toISOString(),
        suggestions: selectedSuggestions,
      }).unwrap();

      const assignments = Array.isArray(response?.assignments) ? response.assignments : [];
      if (!assignments.length) {
        toast.error("No assignments were returned for approval.");
        return;
      }

      const results = await Promise.allSettled(
        assignments.map((assignment) =>
          createDriverAssignment({
            driverId: assignment.driver_id,
            body: {
              route: assignment.route_id,
              vehicle: assignment.vehicle_id,
              scheduled_at: assignment.scheduled_at,
            },
          }).unwrap()
        )
      );

      const successCount = results.filter((result) => result.status === "fulfilled").length;
      const failedCount = results.length - successCount;
      const firstFailure = results.find((result) => result.status === "rejected");
      const failureMessage =
        firstFailure?.status === "rejected" ? extractApiErrorMessage(firstFailure.reason) : "";

      if (successCount > 0) {
        toast.success(`Dispatch approved. ${successCount} assignment${successCount === 1 ? "" : "s"} created.`);
      }
      if (failedCount > 0) {
        toast.error(
          `${failedCount} assignment${failedCount === 1 ? "" : "s"} failed to create.${
            failureMessage ? ` ${failureMessage}` : ""
          }`
        );
      }
    } catch {
      // handled by RTK mutation state
    }
  };

  const toggleRouteSelection = (routeId) => {
    setSelectedRouteIds((prev) =>
      prev.includes(routeId) ? prev.filter((item) => item !== routeId) : [...prev, routeId]
    );
  };

  const selectAllRoutes = () => {
    setSelectedRouteIds(dispatchSuggestions.map((item) => item.route_id).filter(Boolean));
  };

  const clearSelectedRoutes = () => {
    setSelectedRouteIds([]);
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow-sm">
          <Sparkles size={22} />
        </div>
        <div>
          <h1 className="text-3xl font-black tracking-tight text-slate-900">Copilot</h1>
          <p className="mt-1 font-medium text-slate-500">
            Generate and approve AI-powered dispatch recommendations for routes and assignments.
          </p>
        </div>
      </div>

      <section className="space-y-4 rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Dispatch</p>
            <h2 className="text-lg font-black text-slate-900">AI Dispatch Copilot</h2>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-black uppercase tracking-widest text-slate-400">Top N</label>
            <input
              type="number"
              min={1}
              max={20}
              value={dispatchTopN}
              onChange={(event) => setDispatchTopN(event.target.value)}
              className="w-20 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-bold outline-none"
              disabled={isDispatchLoading}
            />
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-black uppercase tracking-widest text-white hover:bg-emerald-700 disabled:opacity-60"
              disabled={isDispatchLoading}
              onClick={handleDispatchCopilot}
            >
              {isDispatchLoading ? "Generating..." : "Generate Plan"}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-black uppercase tracking-widest text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              disabled={isSyncing}
              onClick={handleSync}
            >
              <RefreshCw size={14} className={isSyncing ? "animate-spin" : ""} />
              {isSyncing ? "Syncing" : "Sync Knowledge"}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-black uppercase tracking-widest text-slate-400">Schedule At</label>
          <input
            type="datetime-local"
            value={dispatchScheduledAt}
            onChange={(event) => setDispatchScheduledAt(event.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-bold outline-none"
            disabled={isApprovingDispatch}
          />
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-black uppercase tracking-widest text-white hover:bg-indigo-700 disabled:opacity-60"
            disabled={isApprovingDispatch || isDispatchLoading || !dispatchSuggestions.length || !selectedRouteIds.length}
            onClick={handleApproveDispatch}
          >
            {isApprovingDispatch ? "Approving..." : "Approve Plan"}
          </button>
          <p className="text-xs font-semibold text-slate-500">Selected Routes: {selectedRouteIds.length}</p>
        </div>

        {dispatchSuggestions.length ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded-lg bg-slate-200 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-slate-700 hover:bg-slate-300"
                onClick={selectAllRoutes}
              >
                Select All
              </button>
              <button
                type="button"
                className="rounded-lg bg-slate-200 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-slate-700 hover:bg-slate-300"
                onClick={clearSelectedRoutes}
              >
                Clear
              </button>
            </div>
            {dispatchSuggestions.map((item) => (
              <article
                key={`${item.route_id}-${item.driver_id}-${item.vehicle_id}`}
                className="rounded-xl border border-slate-200 bg-slate-50 p-4"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-black text-slate-700">
                    Rank #{item.rank} - Score {item.score}
                  </p>
                  <label className="inline-flex items-center gap-2 text-xs font-black text-slate-700">
                    <input
                      type="checkbox"
                      checked={selectedRouteIds.includes(item.route_id)}
                      onChange={() => toggleRouteSelection(item.route_id)}
                    />
                    Approve
                  </label>
                </div>
                <p className="mt-1 text-sm font-bold text-slate-900">
                  Route: {item.route_name} | Driver: {item.driver_name} | Vehicle: {item.vehicle_name} ({item.vehicle_number_plate})
                </p>
                {Array.isArray(item.reasoning) && item.reasoning.length ? (
                  <ul className="mt-2 space-y-1">
                    {item.reasoning.map((reason, index) => (
                      <li key={`${item.route_id}-reason-${index}`} className="text-xs font-semibold text-slate-600">
                        - {reason}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="text-xs font-semibold text-slate-500">No dispatch recommendations yet.</p>
        )}

        {unmatchedRoutes.length ? (
          <p className="text-xs font-semibold text-amber-700">
            Unmatched routes: {unmatchedRoutes.length}. Add more available drivers/vehicles or reduce constraints.
          </p>
        ) : null}
      </section>
    </div>
  );
}
