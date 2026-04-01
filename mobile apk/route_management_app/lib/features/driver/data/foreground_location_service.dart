import "dart:async";
import "dart:convert";

import "package:flutter/widgets.dart";
import "package:flutter_foreground_task/flutter_foreground_task.dart";
import "package:geolocator/geolocator.dart";
import "package:http/http.dart" as http;
import "package:shared_preferences/shared_preferences.dart";

import "../../../config/app_config.dart";
import "../../auth/domain/auth_session.dart";

class ForegroundLocationService {
  ForegroundLocationService._();
  static final ForegroundLocationService instance = ForegroundLocationService._();

  static const String _trackingEnabledKey = "driver.tracking.enabled";
  static const String _assignmentIdKey = "driver.tracking.assignment_id";
  static const String _accessTokenKey = "driver.tracking.access_token";
  static const String _refreshTokenKey = "driver.tracking.refresh_token";
  static const String _apiBaseUrlKey = "driver.tracking.api_base_url";

  Future<void> initialize() async {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: "driver_tracking",
        channelName: "Driver Tracking",
        channelDescription: "Live driver tracking while routes are active.",
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
        showWhen: true,
        onlyAlertOnce: true,
      ),
      iosNotificationOptions: const IOSNotificationOptions(),
      foregroundTaskOptions: ForegroundTaskOptions(
        eventAction: ForegroundTaskEventAction.repeat(5000),
        autoRunOnBoot: false,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
  }

  Future<void> startTracking({
    required AuthSession session,
    required String assignmentId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_trackingEnabledKey, true);
    await prefs.setString(_assignmentIdKey, assignmentId);
    await prefs.setString(_accessTokenKey, session.accessToken);
    await prefs.setString(_refreshTokenKey, session.refreshToken ?? "");
    await prefs.setString(_apiBaseUrlKey, AppConfig.apiBaseUrl);

    await FlutterForegroundTask.startService(
      notificationTitle: "Route tracking active",
      notificationText: "Sending driver location in background",
      callback: _startCallback,
    );
  }

  Future<void> stopTracking({String? assignmentId}) async {
    final prefs = await SharedPreferences.getInstance();
    if (assignmentId != null) {
      final currentAssignment = prefs.getString(_assignmentIdKey) ?? "";
      if (currentAssignment.isNotEmpty && currentAssignment != assignmentId) {
        return;
      }
    }
    await prefs.setBool(_trackingEnabledKey, false);
    await prefs.remove(_assignmentIdKey);
    await FlutterForegroundTask.stopService();
  }
}

@pragma("vm:entry-point")
void _startCallback() {
  FlutterForegroundTask.setTaskHandler(DriverTrackingTaskHandler());
}

class DriverTrackingTaskHandler extends TaskHandler {
  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {
    WidgetsFlutterBinding.ensureInitialized();
  }

  @override
  void onRepeatEvent(DateTime timestamp) {
    unawaited(_sendLocationTick());
  }

  @override
  Future<void> onDestroy(DateTime timestamp) async {
    // No-op. Service teardown is handled by the plugin.
  }
}

Future<void> _sendLocationTick() async {
  final prefs = await SharedPreferences.getInstance();
  final enabled = prefs.getBool(ForegroundLocationService._trackingEnabledKey) ?? false;
  if (!enabled) return;

  final assignmentId = prefs.getString(ForegroundLocationService._assignmentIdKey) ?? "";
  String accessToken = prefs.getString(ForegroundLocationService._accessTokenKey) ?? "";
  final refreshToken = prefs.getString(ForegroundLocationService._refreshTokenKey) ?? "";
  final apiBaseUrl = prefs.getString(ForegroundLocationService._apiBaseUrlKey) ?? AppConfig.apiBaseUrl;
  if (assignmentId.isEmpty || accessToken.isEmpty || apiBaseUrl.isEmpty) return;

  final hasPermission = await _hasLocationPermission();
  if (!hasPermission) return;

  try {
    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );
    final payload = <String, dynamic>{
      "latitude": position.latitude,
      "longitude": position.longitude,
      "speed_kph": (position.speed.isFinite ? position.speed : 0) * 3.6,
      "heading": position.heading.isFinite ? position.heading : 0,
      "captured_at": position.timestamp.toUtc().toIso8601String(),
    };

    final locationUri = Uri.parse("$apiBaseUrl/driver/assignments/$assignmentId/location/");
    var response = await http.post(
      locationUri,
      headers: <String, String>{
        "Content-Type": "application/json",
        "Authorization": "Bearer $accessToken",
      },
      body: jsonEncode(payload),
    );

    if (response.statusCode == 401 && refreshToken.isNotEmpty) {
      final refreshedToken = await _refreshAccessToken(
        apiBaseUrl: apiBaseUrl,
        refreshToken: refreshToken,
      );
      if (refreshedToken.isNotEmpty) {
        accessToken = refreshedToken;
        await prefs.setString(ForegroundLocationService._accessTokenKey, accessToken);
        response = await http.post(
          locationUri,
          headers: <String, String>{
            "Content-Type": "application/json",
            "Authorization": "Bearer $accessToken",
          },
          body: jsonEncode(payload),
        );
      }
    }

    if (response.statusCode >= 400 && response.statusCode < 500) {
      await prefs.setBool(ForegroundLocationService._trackingEnabledKey, false);
    }
  } catch (_) {
    // Ignore transient errors; next tick will retry.
  }
}

Future<bool> _hasLocationPermission() async {
  final serviceEnabled = await Geolocator.isLocationServiceEnabled();
  if (!serviceEnabled) return false;
  final permission = await Geolocator.checkPermission();
  return permission == LocationPermission.always || permission == LocationPermission.whileInUse;
}

Future<String> _refreshAccessToken({
  required String apiBaseUrl,
  required String refreshToken,
}) async {
  try {
    final uri = Uri.parse("$apiBaseUrl/auth/refresh/");
    final response = await http.post(
      uri,
      headers: <String, String>{
        "Content-Type": "application/json",
        "X-Client-Type": "mobile",
      },
      body: jsonEncode(<String, dynamic>{"refresh": refreshToken}),
    );
    if (response.statusCode != 200) return "";
    final decoded = jsonDecode(response.body);
    if (decoded is! Map) return "";
    return decoded["access"]?.toString() ?? "";
  } catch (_) {
    return "";
  }
}
