from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.schemas.ai import (
    DispatchCopilotApproveRequest,
    DispatchCopilotApproveResponse,
    DispatchCopilotApprovedAssignment,
    DispatchCopilotRequest,
    DispatchCopilotResponse,
    DispatchCopilotSuggestion,
    DispatchDriver,
    DispatchRoute,
    DispatchVehicle,
)
from app.services.plan_registry import plan_registry


def _driver_status_score(status: str) -> tuple[float, str]:
    normalized = (status or "").upper()
    if normalized == "AVAILABLE":
        return 35.0, "Driver is available."
    if normalized == "IN_ROUTE":
        return 10.0, "Driver is currently in route; lower suitability."
    return -100.0, f"Driver status is {status}; not ideal for dispatch."


def _vehicle_status_score(status: str) -> tuple[float, str]:
    normalized = (status or "").upper()
    if normalized == "AVAILABLE":
        return 30.0, "Vehicle is available."
    if normalized == "ON_ROUTE":
        return 5.0, "Vehicle is on route; lower suitability."
    return -100.0, f"Vehicle status is {status}; not ideal for dispatch."


def _fuel_score(fuel_percentage: int) -> tuple[float, str]:
    fuel = max(0, min(100, int(fuel_percentage)))
    if fuel < 20:
        return -20.0, f"Fuel is low at {fuel}%."
    if fuel < 40:
        return 3.0, f"Fuel is moderate at {fuel}%."
    return min(30.0, fuel * 0.3), f"Fuel is healthy at {fuel}%."


def _score_candidate(route: DispatchRoute, driver: DispatchDriver, vehicle: DispatchVehicle) -> tuple[float, list[str]]:
    score = 100.0
    reasons: list[str] = []

    driver_delta, driver_reason = _driver_status_score(driver.status)
    vehicle_delta, vehicle_reason = _vehicle_status_score(vehicle.status)
    fuel_delta, fuel_reason = _fuel_score(vehicle.fuel_percentage)

    score += driver_delta + vehicle_delta + fuel_delta
    reasons.extend([driver_reason, vehicle_reason, fuel_reason])

    if route.stops_count >= 8:
        score -= 5.0
        reasons.append(f"Route has {route.stops_count} stops; slightly more complex.")
    elif route.stops_count > 0:
        score += 2.0
        reasons.append(f"Route stop count is manageable ({route.stops_count}).")

    if driver.recent_assignments_count > 0:
        penalty = min(20.0, float(driver.recent_assignments_count) * 2.5)
        score -= penalty
        reasons.append(
            f"Driver has {driver.recent_assignments_count} recent assignments; load balancing penalty applied."
        )

    if vehicle.recent_assignments_count > 0:
        penalty = min(15.0, float(vehicle.recent_assignments_count) * 2.0)
        score -= penalty
        reasons.append(
            f"Vehicle has {vehicle.recent_assignments_count} recent assignments; wear balancing penalty applied."
        )

    return round(score, 2), reasons


class DispatchGenerationState(TypedDict, total=False):
    tenant_id: str
    payload: DispatchCopilotRequest
    scored: list[dict[str, Any]]
    suggestions: list[DispatchCopilotSuggestion]
    unmatched_route_ids: list[str]
    plan_id: str


class DispatchApprovalState(TypedDict, total=False):
    tenant_id: str
    payload: DispatchCopilotApproveRequest
    plan: dict[str, Any] | None
    assignments: list[DispatchCopilotApprovedAssignment]


class DispatchCopilotService:
    def __init__(self) -> None:
        self._generate_graph = self._build_generate_graph()
        self._approve_graph = self._build_approve_graph()

    def suggest(self, tenant_id: str, payload: DispatchCopilotRequest) -> DispatchCopilotResponse:
        state: DispatchGenerationState = {"tenant_id": tenant_id, "payload": payload}
        result = self._generate_graph.invoke(state)
        return DispatchCopilotResponse(
            tenant_id=tenant_id,
            plan_id=str(result.get("plan_id") or ""),
            suggestions=result.get("suggestions", []) or [],
            unmatched_route_ids=result.get("unmatched_route_ids", []) or [],
        )

    def approve(self, tenant_id: str, payload: DispatchCopilotApproveRequest) -> DispatchCopilotApproveResponse:
        state: DispatchApprovalState = {"tenant_id": tenant_id, "payload": payload}
        result = self._approve_graph.invoke(state)
        assignments = result.get("assignments", []) or []
        return DispatchCopilotApproveResponse(
            tenant_id=tenant_id,
            plan_id=payload.plan_id,
            approved=len(assignments),
            assignments=assignments,
        )

    @staticmethod
    def _build_generate_graph():
        graph = StateGraph(DispatchGenerationState)
        graph.add_node("score", DispatchCopilotService._node_score_candidates)
        graph.add_node("select", DispatchCopilotService._node_select_recommendations)
        graph.add_node("persist", DispatchCopilotService._node_persist_plan)
        graph.set_entry_point("score")
        graph.add_edge("score", "select")
        graph.add_edge("select", "persist")
        graph.add_edge("persist", END)
        return graph.compile()

    @staticmethod
    def _build_approve_graph():
        graph = StateGraph(DispatchApprovalState)
        graph.add_node("load_plan", DispatchCopilotService._node_load_plan)
        graph.add_node("build_assignments", DispatchCopilotService._node_build_assignments)
        graph.set_entry_point("load_plan")
        graph.add_edge("load_plan", "build_assignments")
        graph.add_edge("build_assignments", END)
        return graph.compile()

    @staticmethod
    def _node_score_candidates(state: DispatchGenerationState) -> DispatchGenerationState:
        payload = state["payload"]
        scored: list[dict[str, Any]] = []
        for route in payload.routes:
            for driver in payload.drivers:
                for vehicle in payload.vehicles:
                    score, reasons = _score_candidate(route, driver, vehicle)
                    scored.append(
                        {
                            "score": score,
                            "route": route,
                            "driver": driver,
                            "vehicle": vehicle,
                            "reasoning": reasons,
                        }
                    )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return {"scored": scored}

    @staticmethod
    def _node_select_recommendations(state: DispatchGenerationState) -> DispatchGenerationState:
        payload = state["payload"]
        scored = state.get("scored", []) or []
        used_routes: set[str] = set()
        used_drivers: set[str] = set()
        used_vehicles: set[str] = set()
        suggestions: list[DispatchCopilotSuggestion] = []

        for item in scored:
            route: DispatchRoute = item["route"]
            driver: DispatchDriver = item["driver"]
            vehicle: DispatchVehicle = item["vehicle"]

            if route.route_id in used_routes or driver.driver_id in used_drivers or vehicle.vehicle_id in used_vehicles:
                continue

            suggestions.append(
                DispatchCopilotSuggestion(
                    rank=len(suggestions) + 1,
                    score=float(item["score"]),
                    route_id=route.route_id,
                    route_name=route.route_name,
                    driver_id=driver.driver_id,
                    driver_name=driver.name,
                    vehicle_id=vehicle.vehicle_id,
                    vehicle_name=vehicle.name,
                    vehicle_number_plate=vehicle.number_plate,
                    reasoning=item["reasoning"],
                )
            )
            used_routes.add(route.route_id)
            used_drivers.add(driver.driver_id)
            used_vehicles.add(vehicle.vehicle_id)

            if len(suggestions) >= payload.top_n:
                break

        all_route_ids = [route.route_id for route in payload.routes]
        unmatched = [route_id for route_id in all_route_ids if route_id not in used_routes]
        return {"suggestions": suggestions, "unmatched_route_ids": unmatched}

    @staticmethod
    def _node_persist_plan(state: DispatchGenerationState) -> DispatchGenerationState:
        tenant_id = state["tenant_id"]
        suggestions = state.get("suggestions", []) or []
        unmatched = state.get("unmatched_route_ids", []) or []
        plan_id = plan_registry.create(
            tenant_id=tenant_id,
            suggestions=[item.model_dump() for item in suggestions],
            unmatched_route_ids=unmatched,
        )
        return {"plan_id": plan_id}

    @staticmethod
    def _node_load_plan(state: DispatchApprovalState) -> DispatchApprovalState:
        payload = state["payload"]
        plan = plan_registry.get(payload.plan_id)
        if not plan:
            raise ValueError("Dispatch plan not found or expired.")
        if str(plan.get("tenant_id")) != str(state["tenant_id"]):
            raise ValueError("Dispatch plan does not belong to this tenant.")
        return {"plan": plan}

    @staticmethod
    def _node_build_assignments(state: DispatchApprovalState) -> DispatchApprovalState:
        payload = state["payload"]
        plan = state.get("plan") or {}
        suggestions = plan.get("suggestions", []) or []
        route_set = set(payload.route_ids or [])
        selected = [item for item in suggestions if not route_set or item.get("route_id") in route_set]

        assignments = [
            DispatchCopilotApprovedAssignment(
                route_id=str(item.get("route_id") or ""),
                route_name=str(item.get("route_name") or ""),
                driver_id=str(item.get("driver_id") or ""),
                driver_name=str(item.get("driver_name") or ""),
                vehicle_id=str(item.get("vehicle_id") or ""),
                vehicle_name=str(item.get("vehicle_name") or ""),
                vehicle_number_plate=str(item.get("vehicle_number_plate") or ""),
                scheduled_at=payload.scheduled_at,
            )
            for item in selected
        ]
        return {"assignments": assignments}


dispatch_copilot_service = DispatchCopilotService()
