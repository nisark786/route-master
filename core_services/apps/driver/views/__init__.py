from .driver_assignment_inventory_api_view import DriverAssignmentInventoryAPIView
from .driver_assignment_detail_api_view import DriverAssignmentDetailAPIView
from .driver_assignment_list_api_view import DriverAssignmentListAPIView
from .driver_assignment_start_api_view import DriverAssignmentStartAPIView
from .driver_location_update_api_view import DriverLocationUpdateAPIView
from .driver_stop_check_in_api_view import DriverStopCheckInAPIView
from .driver_stop_check_out_api_view import DriverStopCheckOutAPIView
from .driver_stop_complete_order_api_view import DriverStopCompleteOrderAPIView
from .driver_stop_detail_api_view import DriverStopDetailAPIView
from .driver_stop_skip_api_view import DriverStopSkipAPIView

__all__ = [
    "DriverAssignmentInventoryAPIView",
    "DriverAssignmentListAPIView",
    "DriverAssignmentStartAPIView",
    "DriverLocationUpdateAPIView",
    "DriverAssignmentDetailAPIView",
    "DriverStopDetailAPIView",
    "DriverStopCheckInAPIView",
    "DriverStopSkipAPIView",
    "DriverStopCompleteOrderAPIView",
    "DriverStopCheckOutAPIView",
]
