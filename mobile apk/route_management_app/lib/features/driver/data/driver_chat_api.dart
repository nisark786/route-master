import "dart:async";
import "dart:convert";
import "dart:io";

import "package:http/http.dart" as http;
import "package:http_parser/http_parser.dart";

import "../../../config/app_config.dart";
import "../../../core/storage/auth_storage.dart";
import "../../auth/data/auth_api.dart";
import "../../auth/domain/auth_session.dart";

class DriverChatApi {
  DriverChatApi({http.Client? client, AuthApi? authApi})
    : _client = client ?? http.Client(),
      _authApi = authApi ?? AuthApi(client: client);

  final http.Client _client;
  final AuthApi _authApi;
  static const Duration _requestTimeout = Duration(seconds: 12);

  Future<Map<String, dynamic>> loadDriverChatBootstrap(
    AuthSession session,
  ) async {
    final payload = await _get("/chat/conversations/", session);
    final data = _toMap(payload["data"]);
    final contacts = _toListOfMaps(data["contacts"]);
    final conversations = _toListOfMaps(data["conversations"]);

    if (contacts.isEmpty) {
      return {
        "contacts": contacts,
        "conversations": conversations,
        "activeContact": <String, dynamic>{},
        "activeConversation": <String, dynamic>{},
      };
    }

    final activeContact = contacts.first;
    Map<String, dynamic> activeConversation =
        conversations.cast<Map<String, dynamic>?>().firstWhere(
          (item) => _counterpartUserId(item) == activeContact["id"]?.toString(),
          orElse: () => null,
        ) ??
        <String, dynamic>{};

    if (activeConversation.isEmpty) {
      final started = await startConversation(
        session: session,
        targetUserId: activeContact["id"]?.toString() ?? "",
      );
      activeConversation = started;
    }

    return {
      "contacts": contacts,
      "conversations": conversations,
      "activeContact": activeContact,
      "activeConversation": activeConversation,
    };
  }

  Future<Map<String, dynamic>> startConversation({
    required AuthSession session,
    required String targetUserId,
  }) async {
    final payload = await _post(
      "/chat/conversations/start/",
      session,
      body: {"conversation_type": "DRIVER", "target_user_id": targetUserId},
    );
    return _toMap(payload["data"]);
  }

  Future<List<Map<String, dynamic>>> getMessages({
    required AuthSession session,
    required String conversationId,
  }) async {
    final payload = await _get(
      "/chat/conversations/$conversationId/messages/",
      session,
    );
    return _toListOfMaps(payload["data"]);
  }

  Future<Map<String, dynamic>> sendTextMessage({
    required AuthSession session,
    required String conversationId,
    required String content,
  }) async {
    final payload = await _post(
      "/chat/conversations/$conversationId/messages/",
      session,
      body: {"content": content},
    );
    return _toMap(payload["data"]);
  }

  Future<void> markConversationRead({
    required AuthSession session,
    required String conversationId,
  }) async {
    await _post(
      "/chat/conversations/$conversationId/read/",
      session,
      body: const {},
    );
  }

  Future<void> deleteMessage({
    required AuthSession session,
    required String conversationId,
    required String messageId,
  }) async {
    final accessToken = await resolveAccessToken(session);
    http.Response response;
    try {
      response = await _client
          .delete(
            Uri.parse("${AppConfig.apiBaseUrl}/chat/conversations/$conversationId/messages/$messageId/"),
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
        path: "/chat/conversations/$conversationId/messages/$messageId/",
        session: session,
        method: "DELETE",
      );
      if (retry != null) return;
    }
    _decodeOrThrow(response);
  }

  Future<void> registerPushToken({
    required AuthSession session,
    required String token,
    String platform = "ANDROID",
  }) async {
    await _post(
      "/chat/push/register/",
      session,
      body: {"token": token, "platform": platform},
    );
  }

  Future<void> unregisterPushToken({
    required AuthSession session,
    required String token,
  }) async {
    await _post("/chat/push/unregister/", session, body: {"token": token});
  }

  Future<Map<String, dynamic>> sendVoiceMessage({
    required AuthSession session,
    required String conversationId,
    required File audioFile,
    required int durationMs,
  }) async {
    final payload = await _postMultipart(
      "/chat/conversations/$conversationId/voice/",
      session,
      fields: {"duration_ms": "$durationMs"},
      files: {"audio": audioFile},
    );
    final data = _toMap(payload["data"]);
    return data;
  }

  Future<String> resolveAccessToken(AuthSession session) async {
    final stored = await AuthStorage.loadSession();
    final storedToken = stored?.accessToken ?? "";
    if (storedToken.isNotEmpty) return storedToken;
    return session.accessToken;
  }

  Uri buildConversationSocketUri({
    required String conversationId,
    required String accessToken,
  }) {
    final apiUri = Uri.parse(AppConfig.apiBaseUrl);
    final pathSegments = List<String>.from(apiUri.pathSegments);
    if (pathSegments.isNotEmpty && pathSegments.last.isEmpty) {
      pathSegments.removeLast();
    }
    if (pathSegments.isNotEmpty && pathSegments.last == "api") {
      pathSegments.removeLast();
    }
    final wsScheme = apiUri.scheme == "https" ? "wss" : "ws";
    final path = [
      ...pathSegments,
      "ws",
      "chat",
      "conversations",
      conversationId,
      "",
    ].join("/");

    return apiUri.replace(
      scheme: wsScheme,
      path: path,
      queryParameters: {"token": accessToken},
    );
  }

  Future<Map<String, dynamic>> _get(String path, AuthSession session) async {
    final accessToken = await resolveAccessToken(session);
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
  }) async {
    final accessToken = await resolveAccessToken(session);
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
        method: "POST",
        body: body,
      );
      if (retry != null) return retry;
    }
    return _decodeOrThrow(response);
  }

  Future<Map<String, dynamic>> _postMultipart(
    String path,
    AuthSession session, {
    required Map<String, String> fields,
    required Map<String, File> files,
  }) async {
    Future<http.Response> sendWithToken(String token) async {
      final request = http.MultipartRequest(
        "POST",
        Uri.parse("${AppConfig.apiBaseUrl}$path"),
      );
      request.headers["Authorization"] = "Bearer $token";
      request.fields.addAll(fields);
      for (final entry in files.entries) {
        final filePath = entry.value.path;
        final filename = filePath.split(Platform.pathSeparator).last;
        request.files.add(
          await http.MultipartFile.fromPath(
            entry.key,
            filePath,
            filename: filename,
            contentType: _audioMediaTypeForPath(filePath),
          ),
        );
      }
      final streamed = await request.send().timeout(_requestTimeout);
      return http.Response.fromStream(streamed);
    }

    final accessToken = await resolveAccessToken(session);
    http.Response response;
    try {
      response = await sendWithToken(accessToken);
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
      final refreshToken = session.refreshToken;
      if (refreshToken != null && refreshToken.isNotEmpty) {
        final newAccessToken = await _authApi.refreshAccessToken(
          refreshToken: refreshToken,
        );
        await AuthStorage.saveSession(
          session.copyWith(accessToken: newAccessToken),
        );
        response = await sendWithToken(newAccessToken);
      }
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
    } else if (method == "DELETE") {
      retriedResponse = await _client
          .delete(
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

  List<Map<String, dynamic>> _toListOfMaps(dynamic value) {
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }

  String? _counterpartUserId(Map<String, dynamic>? conversation) {
    if (conversation == null) return null;
    final participants = _toListOfMaps(conversation["participants"]);
    for (final participant in participants) {
      final role = participant["role"]?.toString() ?? "";
      if (role == "COMPANY_ADMIN") {
        return participant["user_id"]?.toString();
      }
    }
    return null;
  }

  String extractMessage(
    Map<String, dynamic> payload, {
    String fallback = "Request failed.",
  }) {
    return _extractMessage(payload, fallback: fallback);
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

  MediaType _audioMediaTypeForPath(String path) {
    final lower = path.toLowerCase();
    if (lower.endsWith(".wav")) return MediaType("audio", "wav");
    if (lower.endsWith(".m4a")) return MediaType("audio", "mp4");
    if (lower.endsWith(".webm")) return MediaType("audio", "webm");
    if (lower.endsWith(".ogg")) return MediaType("audio", "ogg");
    if (lower.endsWith(".mp3")) return MediaType("audio", "mpeg");
    return MediaType("audio", "wav");
  }
}
