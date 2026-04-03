from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import jwt
from langgraph.graph import END, StateGraph

from app.core.config import settings
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


class DispatchApprovalState(TypedDict, total=False):
    tenant_id: str
    payload: DispatchCopilotApproveRequest
    assignments: list[DispatchCopilotApprovedAssignment]


class DispatchCopilotService:
    def __init__(self) -> None:
        self._generate_graph = self._build_generate_graph()
        self._approve_graph = self._build_approve_graph()

    def suggest(self, tenant_id: str, payload: DispatchCopilotRequest) -> DispatchCopilotResponse:
        state: DispatchGenerationState = {"tenant_id": tenant_id, "payload": payload}
        result = self._generate_graph.invoke(state)
        suggestions = result.get("suggestions", []) or []
        return DispatchCopilotResponse(
            tenant_id=tenant_id,
            plan_id=self._encode_plan_token(tenant_id=tenant_id, suggestions=suggestions),
            suggestions=suggestions,
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
    def _plan_signing_secret() -> str:
        secret = (settings.auth_internal_token_secret or settings.auth_jwt_secret or "").strip()
        if not secret:
            raise ValueError("Dispatch plan signing secret is not configured.")
        return secret

    @classmethod
    def _encode_plan_token(cls, tenant_id: str, suggestions: list[DispatchCopilotSuggestion]) -> str:
        if not suggestions:
            return ""
        payload = {
            "sub": "dispatch_copilot_plan",
            "tenant_id": tenant_id,
            "suggestions": [item.model_dump() for item in suggestions],
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
        return jwt.encode(payload, cls._plan_signing_secret(), algorithm=settings.auth_internal_token_algorithm)

    @classmethod
    def _decode_plan_token(cls, tenant_id: str, token: str) -> list[DispatchCopilotSuggestion]:
        if not token:
            raise ValueError("Dispatch plan token is required when suggestions are not provided.")
        try:
            payload = jwt.decode(
                token,
                cls._plan_signing_secret(),
                algorithms=[settings.auth_internal_token_algorithm],
                options={"verify_aud": False, "verify_iss": False},
            )
        except jwt.PyJWTError as exc:
            raise ValueError("Dispatch plan token is invalid or expired.") from exc
        if str(payload.get("tenant_id") or "") != str(tenant_id):
            raise ValueError("Dispatch plan does not belong to this tenant.")
        raw_suggestions = payload.get("suggestions", []) or []
        return [DispatchCopilotSuggestion.model_validate(item) for item in raw_suggestions]

    @staticmethod
    def _build_generate_graph():
        graph = StateGraph(DispatchGenerationState)
        graph.add_node("score", DispatchCopilotService._node_score_candidates)
        graph.add_node("select", DispatchCopilotService._node_select_recommendations)
        graph.set_entry_point("score")
        graph.add_edge("score", "select")
        graph.add_edge("select", END)
        return graph.compile()

    @staticmethod
    def _build_approve_graph():
        graph = StateGraph(DispatchApprovalState)
        graph.add_node("build_assignments", DispatchCopilotService._node_build_assignments)
        graph.set_entry_point("build_assignments")
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
    def _node_build_assignments(state: DispatchApprovalState) -> DispatchApprovalState:
        tenant_id = state["tenant_id"]
        payload = state["payload"]
        selected_suggestions = payload.suggestions
        if not selected_suggestions:
            decoded_suggestions = DispatchCopilotService._decode_plan_token(tenant_id=tenant_id, token=payload.plan_id)
            route_set = set(payload.route_ids or [])
            selected_suggestions = [
                item for item in decoded_suggestions if not route_set or item.route_id in route_set
            ]
        if not selected_suggestions:
            raise ValueError("Select at least one dispatch suggestion before approval.")

        assignments = [
            DispatchCopilotApprovedAssignment(
                route_id=item.route_id,
                route_name=item.route_name,
                driver_id=item.driver_id,
                driver_name=item.driver_name,
                vehicle_id=item.vehicle_id,
                vehicle_name=item.vehicle_name,
                vehicle_number_plate=item.vehicle_number_plate,
                scheduled_at=payload.scheduled_at,
            )
            for item in selected_suggestions
        ]
        return {"assignments": assignments}


dispatch_copilot_service = DispatchCopilotService()
