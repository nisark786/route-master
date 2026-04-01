from django.db import IntegrityError, transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Route, RouteShop, Shop
from apps.company_admin.serializers import RouteDetailSerializer, RouteUpdateSerializer

from .base import CompanyAdminAPIView


class RouteDetailAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "route.view",
        "PATCH": "route.update",
        "DELETE": "route.delete",
    }
    def _get_route(self, company_id, route_id):
        route = Route.objects.filter(company_id=company_id, id=route_id).prefetch_related("route_shops__shop").first()
        if not route:
            raise NotFound("Route not found.")
        return route

    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="Route details",
        manual_parameters=[openapi.Parameter("route_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={200: "Route loaded"},
    )
    def get(self, request, route_id):
        route = self._get_route(request.user.company_id, route_id)
        return Response(RouteDetailSerializer(route, context={"request": request}).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="Update route",
        manual_parameters=[openapi.Parameter("route_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=RouteUpdateSerializer,
        responses={200: "Route updated"},
    )
    def patch(self, request, route_id):
        route = self._get_route(request.user.company_id, route_id)
        serializer = RouteUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        requested_shops = validated.get("shops")

        if requested_shops is not None:
            shop_ids = [item["shop_id"] for item in requested_shops]
            if len(shop_ids) != len(set(shop_ids)):
                raise ValidationError({"shops": ["Duplicate shop entries are not allowed."]})

            company_shop_ids = set(
                Shop.objects.filter(company_id=request.user.company_id, id__in=shop_ids).values_list("id", flat=True)
            )
            missing_shop_ids = [str(shop_id) for shop_id in shop_ids if shop_id not in company_shop_ids]
            if missing_shop_ids:
                raise ValidationError({"shops": [f"Invalid shops for company: {', '.join(missing_shop_ids)}"]})

            already_assigned = set(
                RouteShop.objects.filter(shop_id__in=shop_ids).exclude(route_id=route.id).values_list("shop_id", flat=True)
            )
            if already_assigned:
                raise ValidationError({"shops": ["One or more selected shops are already assigned to another route."]})

        update_fields = []
        for field in ("route_name", "start_point", "end_point"):
            if field in validated:
                setattr(route, field, validated[field])
                update_fields.append(field)

        with transaction.atomic():
            if update_fields:
                try:
                    route.save(update_fields=[*update_fields, "updated_at"])
                except IntegrityError:
                    raise ValidationError({"route_name": ["A route with this name already exists."]})

            if requested_shops is not None:
                ordered_shop_ids = []
                for item in requested_shops:
                    position = item.get("position")
                    if position is None or position > len(ordered_shop_ids) + 1:
                        ordered_shop_ids.append(item["shop_id"])
                    else:
                        ordered_shop_ids.insert(position - 1, item["shop_id"])
                existing_assignments = list(
                    RouteShop.objects.select_for_update()
                    .filter(route_id=route.id)
                    .select_related("shop")
                )
                existing_by_shop_id = {
                    assignment.shop_id: assignment for assignment in existing_assignments
                }
                existing_shop_ids = set(existing_by_shop_id.keys())
                requested_shop_ids = set(ordered_shop_ids)

                removed_shop_ids = existing_shop_ids - requested_shop_ids
                protected_shop_names = []
                removable_assignment_ids = []
                for shop_id in removed_shop_ids:
                    assignment = existing_by_shop_id[shop_id]
                    if assignment.run_stops.exists():
                        protected_shop_names.append(assignment.shop.name)
                    else:
                        removable_assignment_ids.append(assignment.id)

                if protected_shop_names:
                    protected_shop_names.sort()
                    raise ValidationError(
                        {
                            "shops": [
                                "Cannot remove shop(s) already used in route runs: "
                                + ", ".join(protected_shop_names)
                            ]
                        }
                    )

                if removable_assignment_ids:
                    RouteShop.objects.filter(id__in=removable_assignment_ids).delete()

                retained_assignments = [
                    assignment
                    for assignment in existing_assignments
                    if assignment.shop_id in requested_shop_ids
                ]

                # Move retained assignments to temporary positions to avoid unique conflicts
                # while we apply the requested final order.
                for index, assignment in enumerate(retained_assignments, start=1):
                    assignment.position = 10000 + index
                if retained_assignments:
                    RouteShop.objects.bulk_update(retained_assignments, ["position", "updated_at"])

                retained_by_shop_id = {
                    assignment.shop_id: assignment for assignment in retained_assignments
                }
                to_create = []
                to_update = []
                for index, shop_id in enumerate(ordered_shop_ids, start=1):
                    assignment = retained_by_shop_id.get(shop_id)
                    if assignment is None:
                        to_create.append(RouteShop(route=route, shop_id=shop_id, position=index))
                    else:
                        assignment.position = index
                        to_update.append(assignment)

                if to_create:
                    RouteShop.objects.bulk_create(to_create)
                if to_update:
                    RouteShop.objects.bulk_update(to_update, ["position", "updated_at"])

                route.save(update_fields=["updated_at"])

        refreshed = self._get_route(request.user.company_id, route_id)
        payload = RouteDetailSerializer(refreshed, context={"request": request}).data
        payload["message"] = "Route updated successfully."
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="Delete route",
        manual_parameters=[openapi.Parameter("route_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={204: "Deleted"},
    )
    def delete(self, request, route_id):
        route = self._get_route(request.user.company_id, route_id)
        route.delete()
        return Response({"message": "Route deleted successfully."}, status=status.HTTP_200_OK)
