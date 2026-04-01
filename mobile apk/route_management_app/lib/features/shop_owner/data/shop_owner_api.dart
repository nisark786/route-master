import "dart:convert";

import "package:http/http.dart" as http;

import "../../../config/app_config.dart";
import "../../../core/storage/auth_storage.dart";
import "../../auth/data/auth_api.dart";
import "../../auth/domain/auth_session.dart";

class ShopOwnerApi {
  ShopOwnerApi({http.Client? client, AuthApi? authApi})
      : _client = client ?? http.Client(),
        _authApi = authApi ?? AuthApi(client: client);

  final http.Client _client;
  final AuthApi _authApi;

  Future<Map<String, dynamic>> getDashboard(AuthSession session) async {
    final payload = await _get("/shop-owner/dashboard/", session);
    return _toMap(payload["data"]);
  }

  Future<List<Map<String, dynamic>>> listDeliveries(
    AuthSession session, {
    String? status,
    bool? hasInvoice,
  }) async {
    final query = <String, String>{};
    if ((status ?? "").trim().isNotEmpty) query["status"] = status!.trim();
    if (hasInvoice != null) query["has_invoice"] = hasInvoice ? "true" : "false";

    final payload = await _get("/shop-owner/deliveries/", session, query: query);
    final data = payload["data"];
    if (data is! List) return [];
    return data.whereType<Map>().map((item) => item.cast<String, dynamic>()).toList();
  }

  Future<Map<String, dynamic>> getDeliveryDetail({
    required AuthSession session,
    required String stopId,
  }) async {
    final payload = await _get("/shop-owner/deliveries/$stopId/", session);
    return _toMap(payload["data"]);
  }

  Future<Map<String, dynamic>> _get(
    String path,
    AuthSession session, {
    Map<String, String>? query,
  }) async {
    final accessToken = await _resolveAccessToken(session);
    final uri = Uri.parse("${AppConfig.apiBaseUrl}$path").replace(queryParameters: query);
    final response = await _client.get(uri, headers: _headers(accessToken));
    if (response.statusCode == 401) {
      final retry = await _retryWithRefresh(path: path, session: session, query: query);
      if (retry != null) return retry;
    }
    return _decodeOrThrow(response);
  }

  Future<Map<String, dynamic>?> _retryWithRefresh({
    required String path,
    required AuthSession session,
    Map<String, String>? query,
  }) async {
    final refreshToken = session.refreshToken;
    if (refreshToken == null || refreshToken.isEmpty) return null;

    final newAccessToken = await _authApi.refreshAccessToken(refreshToken: refreshToken);
    await AuthStorage.saveSession(session.copyWith(accessToken: newAccessToken));

    final retriedResponse = await _client.get(
      Uri.parse("${AppConfig.apiBaseUrl}$path").replace(queryParameters: query),
      headers: _headers(newAccessToken),
    );
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

  String _extractMessage(Map<String, dynamic> payload, {required String fallback}) {
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
}
