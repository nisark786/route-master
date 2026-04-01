import "dart:async";

import "../../auth/domain/auth_session.dart";
import "driver_chat_api.dart";
import "driver_chat_cache.dart";
import "driver_chat_outbox.dart";

class DriverChatSyncService {
  DriverChatSyncService._();
  static final DriverChatSyncService instance = DriverChatSyncService._();

  final DriverChatOutbox _outbox = DriverChatOutbox();
  final DriverChatApi _chatApi = DriverChatApi();
  final DriverChatCache _chatCache = DriverChatCache();

  Timer? _timer;
  bool _processing = false;
  AuthSession? _session;

  void start(AuthSession session) {
    _session = session;
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 8), (_) {
      unawaited(processQueue());
    });
    unawaited(processQueue());
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
    _session = null;
  }

  Future<void> processQueue() async {
    final session = _session;
    if (session == null || _processing) return;
    _processing = true;
    try {
      final queue = await _outbox.getQueuedOperations();
      for (final operation in queue) {
        final operationId = operation["id"]?.toString() ?? "";
        if (operationId.isEmpty) continue;

        final type = operation["type"]?.toString() ?? "";
        if (type != "TEXT") {
          await _outbox.removeOperation(operationId);
          continue;
        }

        final conversationId = operation["conversation_id"]?.toString() ?? "";
        final localMessageId = operation["local_message_id"]?.toString() ?? "";
        final content = operation["content"]?.toString() ?? "";
        if (conversationId.isEmpty || localMessageId.isEmpty || content.trim().isEmpty) {
          await _outbox.removeOperation(operationId);
          continue;
        }

        try {
          final sent = await _chatApi.sendTextMessage(
            session: session,
            conversationId: conversationId,
            content: content,
          );
          await _replaceLocalPendingWithSent(
            conversationId: conversationId,
            localMessageId: localMessageId,
            sentMessage: sent,
          );
          await _outbox.removeOperation(operationId);
        } catch (e) {
          if (_isNetworkException(e)) {
            break;
          }
          await _outbox.removeOperation(operationId);
        }
      }
    } finally {
      _processing = false;
    }
  }

  Future<void> _replaceLocalPendingWithSent({
    required String conversationId,
    required String localMessageId,
    required Map<String, dynamic> sentMessage,
  }) async {
    final cached = await _chatCache.getMessages(conversationId);
    if (cached.isEmpty) return;
    final withoutLocal = cached
        .where((item) => (item["id"]?.toString() ?? "") != localMessageId)
        .toList();
    final sentId = sentMessage["id"]?.toString() ?? "";
    final hasSentAlready = sentId.isNotEmpty &&
        withoutLocal.any((item) => (item["id"]?.toString() ?? "") == sentId);
    final next = hasSentAlready ? withoutLocal : [...withoutLocal, sentMessage];
    next.sort((a, b) {
      final aDate = DateTime.tryParse(a["created_at"]?.toString() ?? "");
      final bDate = DateTime.tryParse(b["created_at"]?.toString() ?? "");
      if (aDate == null && bDate == null) return 0;
      if (aDate == null) return -1;
      if (bDate == null) return 1;
      return aDate.compareTo(bDate);
    });
    await _chatCache.saveMessages(conversationId, next);
  }

  bool _isNetworkException(Object error) {
    final text = error.toString().toLowerCase();
    return text.contains("network error") ||
        text.contains("connection timeout") ||
        text.contains("socketexception") ||
        text.contains("timeoutexception") ||
        text.contains("timed out");
  }
}
