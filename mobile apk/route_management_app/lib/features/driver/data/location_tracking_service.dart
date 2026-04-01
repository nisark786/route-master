import "package:geolocator/geolocator.dart";
import "package:permission_handler/permission_handler.dart";

import "../../auth/domain/auth_session.dart";
import "foreground_location_service.dart";

class LocationTrackingService {
  LocationTrackingService._();
  static final LocationTrackingService instance = LocationTrackingService._();

  Future<bool> _ensurePermission() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return false;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    return permission == LocationPermission.always || permission == LocationPermission.whileInUse;
  }

  Future<bool> _ensureNotificationPermission() async {
    if (!await Permission.notification.isGranted) {
      final result = await Permission.notification.request();
      return result.isGranted;
    }
    return true;
  }

  Future<void> start({
    required AuthSession session,
    required String assignmentId,
  }) async {
    final allowed = await _ensurePermission();
    if (!allowed) return;
    final notificationAllowed = await _ensureNotificationPermission();
    if (!notificationAllowed) return;
    await ForegroundLocationService.instance.startTracking(
      session: session,
      assignmentId: assignmentId,
    );
  }

  void stop({String? assignmentId}) {
    ForegroundLocationService.instance.stopTracking(assignmentId: assignmentId);
  }
}
