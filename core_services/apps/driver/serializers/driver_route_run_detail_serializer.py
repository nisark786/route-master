from rest_framework import serializers

from apps.driver.models import DriverRouteRun


class DriverRouteRunStopSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    route_shop_id = serializers.UUIDField(read_only=True)
    shop_id = serializers.UUIDField(read_only=True)
    shop_name = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(read_only=True)
    owner_mobile_number = serializers.CharField(read_only=True)
    location = serializers.CharField(read_only=True)
    location_display_name = serializers.CharField(read_only=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, read_only=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, read_only=True)
    address = serializers.CharField(read_only=True)
    landmark = serializers.CharField(read_only=True)
    shop_image = serializers.CharField(read_only=True)
    position = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    check_in_at = serializers.DateTimeField(read_only=True)
    check_out_at = serializers.DateTimeField(read_only=True)
    skipped_at = serializers.DateTimeField(read_only=True)
    skip_reason = serializers.CharField(read_only=True)
    invoice_number = serializers.CharField(read_only=True)
    invoice_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    invoice_url = serializers.CharField(read_only=True)
    preordered_items = serializers.ListField(read_only=True)
    ordered_items = serializers.ListField(read_only=True)


class DriverRouteRunDetailSerializer(serializers.ModelSerializer):
    assignment_id = serializers.UUIDField(read_only=True)
    assignment_status = serializers.CharField(source="assignment.status", read_only=True)
    route_id = serializers.UUIDField(read_only=True)
    route_name = serializers.CharField(source="route.route_name", read_only=True)
    start_point = serializers.CharField(source="route.start_point", read_only=True)
    end_point = serializers.CharField(source="route.end_point", read_only=True)
    vehicle_id = serializers.UUIDField(read_only=True)
    vehicle_name = serializers.CharField(source="vehicle.name", read_only=True)
    vehicle_number_plate = serializers.CharField(source="vehicle.number_plate", read_only=True)
    vehicle_status = serializers.CharField(source="vehicle.status", read_only=True)
    fuel_percentage = serializers.IntegerField(source="vehicle.fuel_percentage", read_only=True)
    progress = serializers.SerializerMethodField()
    stops = serializers.SerializerMethodField()
    next_pending_stop_id = serializers.SerializerMethodField()

    class Meta:
        model = DriverRouteRun
        fields = [
            "id",
            "assignment_id",
            "assignment_status",
            "status",
            "started_at",
            "completed_at",
            "route_id",
            "route_name",
            "start_point",
            "end_point",
            "vehicle_id",
            "vehicle_name",
            "vehicle_number_plate",
            "vehicle_status",
            "fuel_percentage",
            "progress",
            "next_pending_stop_id",
            "stops",
        ]

    def _build_invoice_url(self, stop):
        request = self.context.get("request")
        if not stop.invoice_file:
            return ""
        if request is None:
            return stop.invoice_file.url
        return request.build_absolute_uri(stop.invoice_file.url)

    def _build_shop_image_url(self, shop):
        request = self.context.get("request")
        if not shop.image:
            return ""
        if request is None:
            return shop.image.url
        return request.build_absolute_uri(shop.image.url)

    def _serialize_stop(self, stop):
        shop = stop.shop
        return {
            "id": stop.id,
            "route_shop_id": stop.route_shop_id,
            "shop_id": shop.id,
            "shop_name": shop.name,
            "owner_name": shop.owner_name,
            "owner_mobile_number": shop.owner_mobile_number,
            "location": shop.location,
            "location_display_name": shop.location_display_name,
            "latitude": shop.latitude,
            "longitude": shop.longitude,
            "address": shop.address,
            "landmark": shop.landmark,
            "shop_image": self._build_shop_image_url(shop),
            "position": stop.position,
            "status": stop.status,
            "check_in_at": stop.check_in_at,
            "check_out_at": stop.check_out_at,
            "skipped_at": stop.skipped_at,
            "skip_reason": stop.skip_reason,
            "invoice_number": stop.invoice_number,
            "invoice_total": stop.invoice_total,
            "invoice_url": self._build_invoice_url(stop),
            "preordered_items": stop.preordered_items or [],
            "ordered_items": stop.ordered_items or [],
        }

    def get_stops(self, obj):
        stops = obj.stops.select_related("shop").all().order_by("position")
        return [self._serialize_stop(stop) for stop in stops]

    def get_progress(self, obj):
        stops = list(obj.stops.all())
        total = len(stops)
        completed = sum(1 for stop in stops if stop.status == "COMPLETED")
        skipped = sum(1 for stop in stops if stop.status == "SKIPPED")
        checked_in = sum(1 for stop in stops if stop.status == "CHECKED_IN")
        return {
            "total_stops": total,
            "completed_stops": completed,
            "skipped_stops": skipped,
            "checked_in_stops": checked_in,
            "pending_stops": max(total - completed - skipped - checked_in, 0),
        }

    def get_next_pending_stop_id(self, obj):
        pending = obj.stops.filter(status="PENDING").order_by("position").first()
        return pending.id if pending else None
