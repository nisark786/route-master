import "dart:async";
import "dart:convert";
import "dart:io";

import "package:http/http.dart" as http;

import "../../../config/app_config.dart";
import "../../../core/storage/auth_storage.dart";
import "../../auth/data/auth_api.dart";
import "../../auth/domain/auth_session.dart";
import "driver_offline_store.dart";

class DriverApi {
  DriverApi({http.Client? client, AuthApi? authApi})
    : _client = client ?? http.Client(),
      _authApi = authApi ?? AuthApi(client: client);

  final http.Client _client;
  final AuthApi _authApi;
  final DriverOfflineStore _offlineStore = DriverOfflineStore();
  static const Duration _requestTimeout = Duration(seconds: 12);

  Future<List<Map<String, dynamic>>> listAssignments(
    AuthSession session,
  ) async {
    try {
      final payload = await _get("/driver/assignments/", session);
      final data = payload["data"];
      if (data is! List) return [];
      final assignments = data
          .whereType<Map>()
          .map((item) => item.cast<String, dynamic>())
          .toList();
      await _offlineStore.saveAssignments(assignments);
      return assignments;
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      final cached = await _offlineStore.getAssignments();
      if (cached.isNotEmpty) return cached;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> startAssignment({
    required AuthSession session,
    required String assignmentId,
  }) async {
    final path = "/driver/assignments/$assignmentId/start/";
    try {
      final payload = await _post(path, session, body: const {});
      await _offlineStore.applyStartAssignmentOffline(assignmentId);
      return _toMap(payload["data"]);
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      await _queueOperation(
        type: "start_assignment",
        assignmentId: assignmentId,
        path: path,
        body: const {},
      );
      await _offlineStore.applyStartAssignmentOffline(assignmentId);
      return {
        "queued_offline": true,
        "message":
            "No internet. Route start saved and will sync automatically.",
      };
    }
  }

  Future<Map<String, dynamic>> getAssignmentDetail({
    required AuthSession session,
    required String assignmentId,
  }) async {
    try {
      final payload = await _get("/driver/assignments/$assignmentId/", session);
      final data = _toMap(payload["data"]);
      if (data.isNotEmpty) {
        await _offlineStore.saveAssignmentDetail(assignmentId, data);
      }
      return data;
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      final cached = await _offlineStore.getAssignmentDetail(assignmentId);
      if (cached.isNotEmpty) return cached;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getAssignmentInventory({
    required AuthSession session,
    required String assignmentId,
  }) async {
    try {
      final payload = await _get(
        "/driver/assignments/$assignmentId/inventory/",
        session,
      );
      final data = _toMap(payload["data"]);
      if (data.isNotEmpty) {
        await _offlineStore.saveAssignmentInventory(assignmentId, data);
      }
      return data;
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      final cached = await _offlineStore.getAssignmentInventory(assignmentId);
      if (cached.isNotEmpty) return {...cached, "from_cache": true};
      rethrow;
    }
  }

  Future<Map<String, dynamic>> saveAssignmentInventory({
    required AuthSession session,
    required String assignmentId,
    required List<Map<String, dynamic>> items,
  }) async {
    final path = "/driver/assignments/$assignmentId/inventory/";
    final payloadBody = {"items": items};
    try {
      final payload = await _post(path, session, body: payloadBody);
      final data = _toMap(payload["data"]);
      if (data.isNotEmpty) {
        await _offlineStore.saveAssignmentInventory(assignmentId, data);
      } else {
        await _offlineStore.applyAssignmentInventoryOffline(
          assignmentId,
          items,
        );
      }
      return data;
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      await _queueOperation(
        type: "assignment_inventory_update",
        assignmentId: assignmentId,
        path: path,
        body: payloadBody,
      );
      await _offlineStore.applyAssignmentInventoryOffline(assignmentId, items);
      return {
        "queued_offline": true,
        "message":
            "No internet. Inventory saved offline and will sync automatically.",
      };
    }
  }

  Future<Map<String, dynamic>> getStopDetail({
    required AuthSession session,
    required String assignmentId,
    required String shopId,
  }) async {
    try {
      final payload = await _get(
        "/driver/assignments/$assignmentId/shops/$shopId/",
        session,
      );
      final data = _toMap(payload["data"]);
      if (data.isNotEmpty) {
        await _offlineStore.saveStopDetail(assignmentId, shopId, data);
      }
      return data;
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      final cached = await _offlineStore.getStopDetail(assignmentId, shopId);
      if (cached.isNotEmpty) return cached;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> checkInStop({
    required AuthSession session,
    required String assignmentId,
    required String shopId,
  }) async {
    final path = "/driver/assignments/$assignmentId/shops/$shopId/check-in/";
    try {
      final payload = await _post(path, session, body: const {});
      await _offlineStore.applyCheckInOffline(assignmentId, shopId);
      return _toMap(payload["data"]);
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      await _queueOperation(
        type: "check_in_stop",
        assignmentId: assignmentId,
        shopId: shopId,
        path: path,
        body: const {},
      );
      await _offlineStore.applyCheckInOffline(assignmentId, shopId);
      return {
        "queued_offline": true,
        "message": "Check-in saved offline and will sync automatically.",
      };
    }
  }

  Future<Map<String, dynamic>> skipStop({
    required AuthSession session,
    required String assignmentId,
    required String shopId,
    required String reason,
  }) async {
    final path = "/driver/assignments/$assignmentId/shops/$shopId/skip/";
    final payloadBody = {"reason": reason.trim()};
    try {
      final payload = await _post(path, session, body: payloadBody);
      await _offlineStore.applySkipStopOffline(
        assignmentId,
        shopId,
        reason.trim(),
      );
      return _toMap(payload["data"]);
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      await _queueOperation(
        type: "skip_stop",
        assignmentId: assignmentId,
        shopId: shopId,
        path: path,
        body: payloadBody,
      );
      await _offlineStore.applySkipStopOffline(
        assignmentId,
        shopId,
        reason.trim(),
      );
      return {
        "queued_offline": true,
        "message": "Skip reason saved offline and will sync automatically.",
      };
    }
  }

  Future<Map<String, dynamic>> completeStopOrder({
    required AuthSession session,
    required String assignmentId,
    required String shopId,
    required List<Map<String, dynamic>> items,
  }) async {
    final path =
        "/driver/assignments/$assignmentId/shops/$shopId/complete-order/";
    final payloadBody = {"items": items};
    try {
      final payload = await _post(path, session, body: payloadBody);
      await _offlineStore.applyCompleteOrderOffline(
        assignmentId,
        shopId,
        items,
      );
      return _toMap(payload["data"]);
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      await _queueOperation(
        type: "complete_stop_order",
        assignmentId: assignmentId,
        shopId: shopId,
        path: path,
        body: payloadBody,
      );
      await _offlineStore.applyCompleteOrderOffline(
        assignmentId,
        shopId,
        items,
      );
      return {
        "queued_offline": true,
        "message": "Invoice data saved offline and will sync automatically.",
      };
    }
  }

  Future<Map<String, dynamic>> checkOutStop({
    required AuthSession session,
    required String assignmentId,
    required String shopId,
  }) async {
    final path = "/driver/assignments/$assignmentId/shops/$shopId/check-out/";
    try {
      final payload = await _post(path, session, body: const {});
      await _offlineStore.applyCheckOutOffline(assignmentId, shopId);
      return _toMap(payload["data"]);
    } catch (e) {
      if (!_isNetworkException(e)) rethrow;
      await _queueOperation(
        type: "check_out_stop",
        assignmentId: assignmentId,
        shopId: shopId,
        path: path,
        body: const {},
      );
      await _offlineStore.applyCheckOutOffline(assignmentId, shopId);
      return {
        "queued_offline": true,
        "message": "Check-out saved offline and will sync automatically.",
      };
    }
  }

  Future<Map<String, dynamic>> updateAssignmentLocation({
    required AuthSession session,
    required String assignmentId,
    required double latitude,
    required double longitude,
    double speedKph = 0,
    double heading = 0,
    DateTime? capturedAt,
  }) async {
    final payload = await _post(
      "/driver/assignments/$assignmentId/location/",
      session,
      body: {
        "latitude": latitude,
        "longitude": longitude,
        "speed_kph": speedKph,
        "heading": heading,
        if (capturedAt != null)
          "captured_at": capturedAt.toUtc().toIso8601String(),
      },
    );
    return _toMap(payload["data"]);
  }

  Future<bool> replayQueuedOperation({
    required AuthSession session,
    required Map<String, dynamic> operation,
  }) async {
    final path = operation["path"]?.toString() ?? "";
    if (path.isEmpty) return true;
    final body = _toMap(operation["body"]);
    try {
      await _post(path, session, body: body, queueOnNetworkFailure: false);
      return true;
    } catch (e) {
      if (_isAlreadyAppliedError(e)) {
        return true;
      }
      if (_isNetworkException(e)) {
        return false;
      }
      return true;
    }
  }

  Future<Map<String, dynamic>> _get(String path, AuthSession session) async {
    final accessToken = await _resolveAccessToken(session);
    http.Response response;
    try {
      response = await _client
          .get(
            Uri.parse("${AppConfig.apiBaseUrl}$path"),
            headers: _headers(accessToken),
          )
          .timeout(_requestTimeout);
    } on TimeoutException {
      throw Exception(
        "Connection timeout. Backend is not reachable at ${AppConfig.apiBaseUrl}.",
      );
    } on SocketException catch (e) {
      throw Exception(
        "Network error (${e.message}). Check backend URL ${AppConfig.apiBaseUrl}.",
      );
    }
    if (response.statusCode == 401) {
      final retry = await _retryWithRefresh(
        path: path,
        session: session,
        method: "GET",
      );
      if (retry != null) return retry;
    }
    return _decodeOrThrow(response);
  }

  Future<Map<String, dynamic>> _post(
    String path,
    AuthSession session, {
    required Map<String, dynamic> body,
    bool queueOnNetworkFailure = true,
  }) async {
    final accessToken = await _resolveAccessToken(session);
    http.Response response;
    try {
      response = await _client
          .post(
            Uri.parse("${AppConfig.apiBaseUrl}$path"),
            headers: _headers(accessToken),
            body: jsonEncode(body),
          )
          .timeout(_requestTimeout);
    } on TimeoutException {
      if (!queueOnNetworkFailure) rethrow;
      throw Exception(
        "Connection timeout. Backend is not reachable at ${AppConfig.apiBaseUrl}.",
      );
    } on SocketException catch (e) {
      if (!queueOnNetworkFailure) rethrow;
      throw Exception(
        "Network error (${e.message}). Check backend URL ${AppConfig.apiBaseUrl}.",
      );
    }
    if (response.statusCode == 401) {
      final retry = await _retryWithRefresh(
        path: path,
        session: session,
        method: "POST",
        body: body,
      );
      if (retry != null) return retry;
    }
    return _decodeOrThrow(response);
  }

  Future<Map<String, dynamic>?> _retryWithRefresh({
    required String path,
    required AuthSession session,
    required String method,
    Map<String, dynamic>? body,
  }) async {
    final refreshToken = session.refreshToken;
    if (refreshToken == null || refreshToken.isEmpty) return null;

    final newAccessToken = await _authApi.refreshAccessToken(
      refreshToken: refreshToken,
    );
    await AuthStorage.saveSession(
      session.copyWith(accessToken: newAccessToken),
    );

    late http.Response retriedResponse;
    if (method == "GET") {
      retriedResponse = await _client
          .get(
            Uri.parse("${AppConfig.apiBaseUrl}$path"),
            headers: _headers(newAccessToken),
          )
          .timeout(_requestTimeout);
    } else {
      retriedResponse = await _client
          .post(
            Uri.parse("${AppConfig.apiBaseUrl}$path"),
            headers: _headers(newAccessToken),
            body: jsonEncode(body ?? const {}),
          )
          .timeout(_requestTimeout);
    }
    return _decodeOrThrow(retriedResponse);
  }

  Future<String> _resolveAccessToken(AuthSession session) async {
    final stored = await AuthStorage.loadSession();
    final storedToken = stored?.accessToken ?? "";
    if (storedToken.isNotEmpty) return storedToken;
    return session.accessToken;
  }

  Map<String, String> _headers(String accessToken) {
    return {
      "Content-Type": "application/json",
      "Authorization": "Bearer $accessToken",
    };
  }

  Map<String, dynamic> _decodeOrThrow(http.Response response) {
    final payload = _toMap(_decode(response.body));
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return payload;
    }
    throw Exception(_extractMessage(payload, fallback: "Request failed."));
  }

  dynamic _decode(String body) {
    if (body.isEmpty) return <String, dynamic>{};
    return jsonDecode(body);
  }

  Map<String, dynamic> _toMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return value.cast<String, dynamic>();
    return <String, dynamic>{};
  }

  String _extractMessage(
    Map<String, dynamic> payload, {
    required String fallback,
  }) {
    final message = payload["message"];
    if (message is String && message.trim().isNotEmpty) return message;

    final error = payload["error"];
    if (error is String && error.trim().isNotEmpty) return error;
    if (error is Map) {
      final details = error["details"];
      if (details is Map) {
        for (final value in details.values) {
          if (value is List && value.isNotEmpty) return value.first.toString();
          if (value is String && value.trim().isNotEmpty) return value;
        }
      }
    }

    final detail = payload["detail"];
    if (detail is String && detail.trim().isNotEmpty) return detail;
    return fallback;
  }

  Future<void> _queueOperation({
    required String type,
    required String assignmentId,
    String? shopId,
    required String path,
    required Map<String, dynamic> body,
  }) async {
    final operationId = "${DateTime.now().microsecondsSinceEpoch}";
    await _offlineStore.enqueueOperation({
      "id": operationId,
      "type": type,
      "assignment_id": assignmentId,
      if (shopId != null && shopId.isNotEmpty) "shop_id": shopId,
      "path": path,
      "body": body,
      "created_at": DateTime.now().toUtc().toIso8601String(),
    });
  }

  bool _isNetworkException(Object error) {
    final text = error.toString().toLowerCase();
    return text.contains("network error") ||
        text.contains("connection timeout") ||
        text.contains("socketexception") ||
        text.contains("timeoutexception") ||
        text.contains("timed out");
  }

  bool _isAlreadyAppliedError(Object error) {
    final text = error.toString().toLowerCase();
    return text.contains("already") ||
        text.contains("completed") ||
        text.contains("checked in") ||
        text.contains("no pending stop");
  }
}
