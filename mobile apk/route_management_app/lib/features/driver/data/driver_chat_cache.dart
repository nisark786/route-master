import "dart:convert";

import "package:shared_preferences/shared_preferences.dart";

class DriverChatCache {
  static const String _prefix = "driver_chat_cache_v1_";
  static const int _maxMessagesPerConversation = 300;

  String _key(String conversationId) => "$_prefix$conversationId";

  Future<List<Map<String, dynamic>>> getMessages(String conversationId) async {
    if (conversationId.trim().isEmpty) return const [];
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key(conversationId));
    if (raw == null || raw.trim().isEmpty) return const [];

    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return const [];
      return decoded
          .whereType<Map>()
          .map((item) => item.cast<String, dynamic>())
          .toList();
    } catch (_) {
      return const [];
    }
  }

  Future<void> saveMessages(
    String conversationId,
    List<Map<String, dynamic>> messages,
  ) async {
    if (conversationId.trim().isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    final trimmed = messages.length > _maxMessagesPerConversation
        ? messages.sublist(messages.length - _maxMessagesPerConversation)
        : messages;
    await prefs.setString(_key(conversationId), jsonEncode(trimmed));
  }
}

