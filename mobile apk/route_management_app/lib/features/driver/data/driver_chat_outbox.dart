import "dart:convert";

import "package:shared_preferences/shared_preferences.dart";

class DriverChatOutbox {
  static const String _queueKey = "driver.chat.outbox.v1";

  Future<void> enqueueText({
    required String operationId,
    required String conversationId,
    required String localMessageId,
    required String content,
  }) async {
    final queue = await getQueuedOperations();
    queue.add({
      "id": operationId,
      "type": "TEXT",
      "conversation_id": conversationId,
      "local_message_id": localMessageId,
      "content": content,
      "created_at": DateTime.now().toUtc().toIso8601String(),
    });
    await _save(queue);
  }

  Future<List<Map<String, dynamic>>> getQueuedOperations() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_queueKey);
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

  Future<void> removeOperation(String operationId) async {
    if (operationId.trim().isEmpty) return;
    final queue = await getQueuedOperations();
    final next = queue
        .where((item) => (item["id"]?.toString() ?? "") != operationId)
        .toList();
    await _save(next);
  }

  Future<void> removeByLocalMessageId(String localMessageId) async {
    if (localMessageId.trim().isEmpty) return;
    final queue = await getQueuedOperations();
    final next = queue
        .where((item) => (item["local_message_id"]?.toString() ?? "") != localMessageId)
        .toList();
    await _save(next);
  }

  Future<void> _save(List<Map<String, dynamic>> queue) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_queueKey, jsonEncode(queue));
  }
}
