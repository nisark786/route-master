import "dart:async";
import "dart:convert";
import "dart:io";

import "package:flutter/foundation.dart";
import "package:http/http.dart" as http;

import "../../../config/app_config.dart";
import "../domain/auth_session.dart";

class AuthApi {
  final http.Client _client;
  static const Duration _requestTimeout = Duration(seconds: 12);

  AuthApi({http.Client? client}) : _client = client ?? http.Client();

  Future<AuthSession> login({
    required String identifier,
    required String password,
  }) async {
    final baseUri = Uri.parse(AppConfig.apiBaseUrl);
    final host = baseUri.host.toLowerCase();
    if (!kIsWeb &&
        defaultTargetPlatform == TargetPlatform.android &&
        (host == "localhost" || host == "127.0.0.1")) {
      throw Exception(
        "Invalid API host for Android device: ${AppConfig.apiBaseUrl}. Use your PC LAN IP (for phone) or 10.0.2.2 (for emulator).",
      );
    }

    final uri = Uri.parse("${AppConfig.apiBaseUrl}/auth/mobile/login/");
    http.Response response;
    try {
      response = await _client
          .post(
            uri,
            headers: {
              "Content-Type": "application/json",
              "X-Client-Type": "mobile",
            },
            body: jsonEncode({
              "identifier": identifier.trim(),
              "password": password,
            }),
          )
          .timeout(_requestTimeout);
    } on TimeoutException {
      throw Exception(
        "Connection timeout. Backend is not reachable at ${AppConfig.apiBaseUrl}.",
      );
    } on SocketException catch (e) {
      throw Exception(
        "Network error (${e.message}). Check backend URL ${AppConfig.apiBaseUrl} and server status.",
      );
    }

    final payload = _decodeJson(response.body);

    if (response.statusCode != 200) {
      throw Exception(_extractErrorMessage(payload, fallback: "Login failed."));
    }

    final access = payload["access"]?.toString() ?? "";
    final refresh = payload["refresh"]?.toString() ?? "";
    final roleRaw = payload["role"]?.toString();
    final role = AuthSession.parseRole(roleRaw);
    final userEmail = payload["email"]?.toString() ?? "";
    final companyId = payload["company_id"]?.toString();
    final mustChangePassword = payload["must_change_password"] == true;

    if (access.isEmpty || role == null) {
      throw Exception("Invalid login response from server.");
    }

    return AuthSession(
      accessToken: access,
      refreshToken: refresh.isEmpty ? null : refresh,
      role: role,
      email: userEmail,
      mustChangePassword: mustChangePassword,
      companyId: companyId,
    );
  }

  Future<void> changeInitialPassword({
    required String accessToken,
    required String currentPassword,
    required String newPassword,
  }) async {
    final uri = Uri.parse(
      "${AppConfig.apiBaseUrl}/auth/change-initial-password/",
    );
    final response = await _client.post(
      uri,
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer $accessToken",
      },
      body: jsonEncode({
        "current_password": currentPassword,
        "new_password": newPassword,
        "confirm_password": newPassword,
      }),
    );
    if (response.statusCode != 200) {
      final payload = _decodeJson(response.body);
      throw Exception(
        _extractErrorMessage(payload, fallback: "Password update failed."),
      );
    }
  }

  Future<Map<String, dynamic>> getMe(String accessToken) async {
    final uri = Uri.parse("${AppConfig.apiBaseUrl}/auth/me/");
    http.Response response;
    try {
      response = await _client
          .get(
            uri,
            headers: {
              "Content-Type": "application/json",
              "Authorization": "Bearer $accessToken",
            },
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
    final payload = _decodeJson(response.body);
    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(payload, fallback: "Unable to load profile."),
      );
    }
    return payload;
  }

  Future<void> changePassword({
    required String accessToken,
    required String currentPassword,
    required String newPassword,
  }) async {
    await changeInitialPassword(
      accessToken: accessToken,
      currentPassword: currentPassword,
      newPassword: newPassword,
    );
  }

  Future<void> logout(String accessToken, {String? refreshToken}) async {
    final uri = Uri.parse("${AppConfig.apiBaseUrl}/auth/logout/");
    await _client.post(
      uri,
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer $accessToken",
      },
      body: jsonEncode({
        if ((refreshToken ?? "").isNotEmpty) "refresh": refreshToken,
      }),
    );
  }

  Future<String> refreshAccessToken({required String refreshToken}) async {
    final uri = Uri.parse("${AppConfig.apiBaseUrl}/auth/refresh/");
    final response = await _client.post(
      uri,
      headers: {"Content-Type": "application/json", "X-Client-Type": "mobile"},
      body: jsonEncode({"refresh": refreshToken}),
    );

    final payload = _decodeJson(response.body);
    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(payload, fallback: "Token refresh failed."),
      );
    }

    final access = payload["access"]?.toString() ?? "";
    if (access.isEmpty) {
      throw Exception("Invalid refresh response from server.");
    }
    return access;
  }

  Map<String, dynamic> _decodeJson(String body) {
    if (body.isEmpty) return {};
    final decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) return decoded;
    return {};
  }

  String _extractErrorMessage(
    Map<String, dynamic> payload, {
    required String fallback,
  }) {
    if (payload["message"] is String &&
        (payload["message"] as String).trim().isNotEmpty) {
      return payload["message"] as String;
    }
    if (payload["error"] is String &&
        (payload["error"] as String).trim().isNotEmpty) {
      return payload["error"] as String;
    }
    if (payload["detail"] is String &&
        (payload["detail"] as String).trim().isNotEmpty) {
      return payload["detail"] as String;
    }
    for (final value in payload.values) {
      if (value is List && value.isNotEmpty) {
        return value.first.toString();
      }
      if (value is String && value.trim().isNotEmpty) {
        return value;
      }
    }
    return fallback;
  }
}
