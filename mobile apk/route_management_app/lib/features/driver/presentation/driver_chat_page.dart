import "dart:async";
import "dart:convert";
import "dart:io";

import "package:flutter/foundation.dart";
import "package:flutter/material.dart";
import "package:intl/intl.dart";
import "package:just_audio/just_audio.dart";
import "package:path_provider/path_provider.dart";
import "package:permission_handler/permission_handler.dart";
import "package:record/record.dart";

import "../../../config/app_config.dart";
import "../../../core/notifications/local_notification_service.dart";
import "../../auth/domain/auth_session.dart";
import "../data/driver_chat_api.dart";
import "../data/driver_chat_cache.dart";
import "../data/driver_chat_outbox.dart";

class DriverChatPage extends StatefulWidget {
  const DriverChatPage({super.key, required this.session});

  final AuthSession session;

  @override
  State<DriverChatPage> createState() => _DriverChatPageState();
}

class _DriverChatPageState extends State<DriverChatPage>
    with WidgetsBindingObserver {
  final _chatApi = DriverChatApi();
  final _chatCache = DriverChatCache();
  final _chatOutbox = DriverChatOutbox();
  final _composerController = TextEditingController();
  final _scrollController = ScrollController();
  final _audioRecorder = AudioRecorder();
  final _voicePlayer = AudioPlayer();
  final _recordingStopwatch = Stopwatch();

  bool _isLoading = true;
  bool _isSending = false;
  bool _isUploadingVoice = false;
  bool _isRecording = false;
  String? _error;
  String _socketStatus = "connecting";
  Map<String, dynamic> _contact = const {};
  Map<String, dynamic> _conversation = const {};
  List<Map<String, dynamic>> _messages = const [];
  WebSocket? _socket;
  StreamSubscription<dynamic>? _socketSubscription;
  Timer? _reconnectTimer;
  Timer? _typingStopTimer;
  Timer? _remoteTypingStopTimer;
  bool _disposed = false;
  bool _isLocalTyping = false;
  bool _counterpartIsTyping = false;
  bool _counterpartIsRecording = false;
  bool _counterpartIsOnline = false;
  bool _hasComposerText = false;
  String? _counterpartLastSeenAt;
  final List<String> _pendingLocalMessageIds = [];
  Timer? _recordingTicker;
  int _recordingDurationMs = 0;
  String? _playingMessageId;
  DateTime? _recordingStartedAt;
  final Map<String, String> _cachedAudioPaths = {};
  final Map<String, Map<String, dynamic>> _pendingVoiceUploads = {};
  final Set<String> _playedIncomingVoiceIds = <String>{};
  final Set<String> _selectedMessageIds = <String>{};
  Timer? _cacheFlushTimer;
  AppLifecycleState _appLifecycleState = AppLifecycleState.resumed;

  bool get _isSelectionMode => _selectedMessageIds.isNotEmpty;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _composerController.addListener(_onComposerChanged);
    _loadChat();
  }

  @override
  void dispose() {
    _disposed = true;
    WidgetsBinding.instance.removeObserver(this);
    _composerController.removeListener(_onComposerChanged);
    _composerController.dispose();
    _scrollController.dispose();
    _typingStopTimer?.cancel();
    _remoteTypingStopTimer?.cancel();
    _reconnectTimer?.cancel();
    _cacheFlushTimer?.cancel();
    _recordingTicker?.cancel();
    _recordingStopwatch.stop();
    _recordingStopwatch.reset();
    _sendTyping(false);
    _sendRecording(false);
    _audioRecorder.dispose();
    _voicePlayer.dispose();
    for (final path in _cachedAudioPaths.values) {
      try {
        File(path).deleteSync();
      } catch (_) {}
    }
    for (final pending in _pendingVoiceUploads.values) {
      final path = pending["path"]?.toString() ?? "";
      if (path.isEmpty) continue;
      try {
        File(path).deleteSync();
      } catch (_) {}
    }
    _socketSubscription?.cancel();
    _socket?.close();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _appLifecycleState = state;
  }

  Future<void> _loadChat() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final bootstrap = await _chatApi.loadDriverChatBootstrap(widget.session);
      final contact = _toMap(bootstrap["activeContact"]);
      final conversation = _toMap(bootstrap["activeConversation"]);
      final conversationId = conversation["id"]?.toString() ?? "";
      List<Map<String, dynamic>> cachedMessages = const [];
      if (conversationId.isNotEmpty) {
        cachedMessages = await _chatCache.getMessages(conversationId);
        if (mounted && cachedMessages.isNotEmpty) {
          _hydratePlayedVoiceIds(cachedMessages);
          setState(() {
            _contact = contact;
            _conversation = conversation;
            _messages = _sortMessages(cachedMessages);
          });
        }
      }
      final messages = conversationId.isEmpty
          ? const <Map<String, dynamic>>[]
          : await _chatApi.getMessages(
              session: widget.session,
              conversationId: conversationId,
            );

      if (!mounted) return;
      final mergedMessages = _mergeVoicePlayedState(
        incoming: messages,
        cached: cachedMessages,
      );
      _hydratePlayedVoiceIds(mergedMessages);
      setState(() {
        _contact = contact;
        _conversation = conversation;
        _messages = _sortMessages(mergedMessages);
        _counterpartIsOnline = contact["is_online"] == true;
        _counterpartLastSeenAt = contact["last_seen_at"]?.toString();
      });
      _scheduleCacheFlush();
      if (conversationId.isNotEmpty) {
        await _chatApi.markConversationRead(
          session: widget.session,
          conversationId: conversationId,
        );
        await _connectSocket(conversationId);
      }
      _scrollToBottom(jump: true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _connectSocket(String conversationId) async {
    await _socketSubscription?.cancel();
    await _socket?.close();
    _reconnectTimer?.cancel();
    _socket = null;

    try {
      final accessToken = await _chatApi.resolveAccessToken(widget.session);
      final uri = _chatApi.buildConversationSocketUri(
        conversationId: conversationId,
        accessToken: accessToken,
      );
      final socket = await WebSocket.connect(uri.toString());
      if (!mounted) {
        await socket.close();
        return;
      }

      setState(() => _socketStatus = "connected");
      _socket = socket;
      _socketSubscription = socket.listen(
        (rawEvent) async {
          try {
            final payload = jsonDecode(rawEvent.toString());
            if (payload is! Map<String, dynamic>) return;
            final event = payload["event"]?.toString() ?? "";
            if (!mounted) return;

            if (event == "message") {
              final message = _toMap(payload["message"]);
              if (message.isEmpty) return;
              setState(() {
                _upsertMessage(message);
                _reconcilePendingForMine(message);
              });
              _scrollToBottom();
              if (!_isMine(message)) {
                if (_appLifecycleState == AppLifecycleState.resumed) {
                  await _chatApi.markConversationRead(
                    session: widget.session,
                    conversationId: conversationId,
                  );
                } else {
                  await _notifyIncomingMessage(message);
                }
              }
              return;
            }

            if (event == "message_updated") {
              final message = _toMap(payload["message"]);
              if (message.isEmpty) return;
              setState(() => _upsertMessage(message));
              return;
            }

            if (event == "presence") {
              final userId = payload["user_id"]?.toString() ?? "";
              final contactId = _contact["id"]?.toString() ?? "";
              if (userId.isNotEmpty &&
                  contactId.isNotEmpty &&
                  userId == contactId) {
                setState(() {
                  _counterpartIsOnline = payload["is_online"] == true;
                  _counterpartLastSeenAt = payload["last_seen_at"]?.toString();
                });
              }
              return;
            }

            if (event == "typing") {
              final userId = payload["user_id"]?.toString() ?? "";
              final contactId = _contact["id"]?.toString() ?? "";
              if (userId.isNotEmpty &&
                  contactId.isNotEmpty &&
                  userId == contactId) {
                final isTyping = payload["is_typing"] == true;
                setState(() => _counterpartIsTyping = isTyping);
                _remoteTypingStopTimer?.cancel();
                if (isTyping) {
                  _remoteTypingStopTimer = Timer(
                    const Duration(seconds: 3),
                    () {
                      if (mounted) setState(() => _counterpartIsTyping = false);
                    },
                  );
                }
              }
              return;
            }

            if (event == "recording") {
              final userId = payload["user_id"]?.toString() ?? "";
              final contactId = _contact["id"]?.toString() ?? "";
              if (userId.isNotEmpty &&
                  contactId.isNotEmpty &&
                  userId == contactId) {
                setState(
                  () =>
                      _counterpartIsRecording = payload["is_recording"] == true,
                );
              }
              return;
            }
          } catch (_) {}
        },
        onDone: () {
          if (mounted) {
            setState(() => _socketStatus = "disconnected");
            _scheduleReconnect(conversationId);
          }
        },
        onError: (_) {
          if (mounted) {
            setState(() => _socketStatus = "error");
            _scheduleReconnect(conversationId);
          }
        },
        cancelOnError: false,
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _socketStatus = "unavailable";
        _error = e.toString().replaceFirst("Exception: ", "");
      });
      _scheduleReconnect(conversationId);
    }
  }

  Future<void> _sendMessage() async {
    final content = _composerController.text.trim();
    if (content.isEmpty || _isSending) return;
    final socket = _socket;
    final isSocketReady = socket != null && socket.readyState == WebSocket.open;

    final localId = "local-${DateTime.now().microsecondsSinceEpoch}";
    final localMessage = <String, dynamic>{
      "id": localId,
      "message_type": "TEXT",
      "content": content,
      "created_at": DateTime.now().toUtc().toIso8601String(),
      "updated_at": DateTime.now().toUtc().toIso8601String(),
      "sender_role": "DRIVER",
      "sender_email": "",
      "recipient_count": 1,
      "delivered_count": 0,
      "seen_count": 0,
      "_local_pending": true,
      "_queued_offline": !isSocketReady,
    };

    setState(() => _isSending = true);
    try {
      setState(() {
        if (isSocketReady) {
          _pendingLocalMessageIds.add(localId);
        }
        _messages = [..._messages, localMessage];
      });
      _scheduleCacheFlush();
      _scrollToBottom();
      _composerController.clear();
      _sendTyping(false);
      if (isSocketReady) {
        socket.add(jsonEncode({"content": content}));
      } else {
        final conversationId = _conversation["id"]?.toString() ?? "";
        if (conversationId.isNotEmpty) {
          final operationId = "chat-op-${DateTime.now().microsecondsSinceEpoch}";
          await _chatOutbox.enqueueText(
            operationId: operationId,
            conversationId: conversationId,
            localMessageId: localId,
            content: content,
          );
          _showMessage("No internet. Message queued and will sync automatically.");
        } else {
          _showMessage("Chat is not ready yet.");
        }
      }
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      _showMessage(e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
      }
    }
  }

  void _scrollToBottom({bool jump = false}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      final position = _scrollController.position.maxScrollExtent;
      if (jump) {
        _scrollController.jumpTo(position);
      } else {
        _scrollController.animateTo(
          position,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  void _scheduleReconnect(String conversationId) {
    if (_disposed || conversationId.isEmpty) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 2), () {
      if (!_disposed && mounted) {
        _connectSocket(conversationId);
      }
    });
  }

  void _scheduleCacheFlush() {
    final conversationId = _conversation["id"]?.toString() ?? "";
    if (conversationId.isEmpty) return;
    _cacheFlushTimer?.cancel();
    _cacheFlushTimer = Timer(const Duration(milliseconds: 300), () async {
      await _chatCache.saveMessages(conversationId, _messages);
    });
  }

  Future<void> _notifyIncomingMessage(Map<String, dynamic> message) async {
    if (_appLifecycleState == AppLifecycleState.resumed) return;
    final messageId = message["id"]?.toString() ?? "";
    if (messageId.isEmpty) return;

    final isVoice = message["message_type"]?.toString() == "VOICE";
    final body = isVoice
        ? "Voice message"
        : (message["content"]?.toString().trim() ?? "");
    final notificationBody = body.isEmpty ? "New message" : body;

    await LocalNotificationService.instance.showIncomingChatMessage(
      messageId: messageId,
      title: _chatDisplayName(),
      body: notificationBody,
    );
  }

  String _chatDisplayName() {
    final displayName = _contact["display_name"]?.toString().trim() ?? "";
    if (displayName.isNotEmpty) {
      return displayName;
    }
    return "Route Master";
  }

  void _onComposerChanged() {
    final hasText = _composerController.text.trim().isNotEmpty;
    if (_hasComposerText != hasText && mounted) {
      setState(() => _hasComposerText = hasText);
    }
    if (hasText && !_isLocalTyping) {
      _isLocalTyping = true;
      _sendTyping(true);
    }
    _typingStopTimer?.cancel();
    if (!hasText) {
      _isLocalTyping = false;
      _sendTyping(false);
      return;
    }
    _typingStopTimer = Timer(const Duration(milliseconds: 1300), () {
      if (!mounted) return;
      _isLocalTyping = false;
      _sendTyping(false);
    });
  }

  void _sendTyping(bool isTyping) {
    final socket = _socket;
    if (socket == null || socket.readyState != WebSocket.open) return;
    socket.add(jsonEncode({"event": "typing", "is_typing": isTyping}));
  }

  void _sendRecording(bool isRecording) {
    final socket = _socket;
    if (socket == null || socket.readyState != WebSocket.open) return;
    socket.add(jsonEncode({"event": "recording", "is_recording": isRecording}));
  }

  void _upsertMessage(Map<String, dynamic> message) {
    final id = message["id"]?.toString() ?? "";
    if (id.isEmpty) return;
    final index = _messages.indexWhere((item) => item["id"]?.toString() == id);
    if (index == -1) {
      _messages = _sortMessages([..._messages, message]);
      _scheduleCacheFlush();
      return;
    }
    final next = [..._messages];
    next[index] = {...next[index], ...message, "_local_pending": false};
    _messages = _sortMessages(next);
    _scheduleCacheFlush();
  }

  void _replaceMessageById(String id, Map<String, dynamic> nextMessage) {
    final index = _messages.indexWhere((item) => item["id"]?.toString() == id);
    if (index == -1) {
      _messages = _sortMessages([..._messages, nextMessage]);
      _scheduleCacheFlush();
      return;
    }
    final next = [..._messages];
    next[index] = nextMessage;
    _messages = _sortMessages(next);
    _scheduleCacheFlush();
  }

  void _reconcilePendingForMine(Map<String, dynamic> incoming) {
    if (!_isMine(incoming)) return;
    if (_pendingLocalMessageIds.isNotEmpty) {
      final localId = _pendingLocalMessageIds.removeAt(0);
      _messages = _messages
          .where((item) => item["id"]?.toString() != localId)
          .toList();
    }
    _reconcileQueuedOfflineLocal(incoming);
    _scheduleCacheFlush();
  }

  void _reconcileQueuedOfflineLocal(Map<String, dynamic> incoming) {
    if (incoming["message_type"]?.toString() != "TEXT") return;
    final incomingContent = (incoming["content"]?.toString() ?? "").trim();
    if (incomingContent.isEmpty) return;
    final index = _messages.indexWhere((item) {
      if (item["_queued_offline"] != true) return false;
      if (!_isMine(item)) return false;
      if (item["message_type"]?.toString() != "TEXT") return false;
      final content = (item["content"]?.toString() ?? "").trim();
      return content == incomingContent;
    });
    if (index == -1) return;
    final localId = _messages[index]["id"]?.toString() ?? "";
    _messages = _messages
        .where((item) => (item["id"]?.toString() ?? "") != localId)
        .toList();
  }

  String _messageId(Map<String, dynamic> message) {
    return message["id"]?.toString() ?? "";
  }

  bool _canSelectMessage(Map<String, dynamic> message) {
    return _isMine(message);
  }

  bool _isSelectedMessage(Map<String, dynamic> message) {
    final id = _messageId(message);
    if (id.isEmpty) return false;
    return _selectedMessageIds.contains(id);
  }

  void _toggleSelectionForMessage(Map<String, dynamic> message) {
    final messageId = _messageId(message);
    if (messageId.isEmpty || !_canSelectMessage(message)) return;
    setState(() {
      if (_selectedMessageIds.contains(messageId)) {
        _selectedMessageIds.remove(messageId);
      } else {
        _selectedMessageIds.add(messageId);
      }
    });
  }

  void _clearSelection() {
    if (_selectedMessageIds.isEmpty) return;
    setState(() => _selectedMessageIds.clear());
  }

  Future<void> _deleteSelectedMessages() async {
    if (_selectedMessageIds.isEmpty) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text("Delete Messages"),
          content: Text(
            _selectedMessageIds.length == 1
                ? "Delete this message?"
                : "Delete ${_selectedMessageIds.length} messages?",
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text("Cancel"),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text("Delete"),
            ),
          ],
        );
      },
    );
    if (confirmed != true) return;

    final conversationId = _conversation["id"]?.toString() ?? "";
    final targetIds = _selectedMessageIds.toList();
    var deletedCount = 0;
    final failedIds = <String>[];
    for (final messageId in targetIds) {
      final messageIndex = _messages.indexWhere(
        (item) => (item["id"]?.toString() ?? "") == messageId,
      );
      if (messageIndex == -1) {
        _selectedMessageIds.remove(messageId);
        continue;
      }

      final isLocalOnly = messageId.startsWith("local-");
      if (isLocalOnly) {
        final pending = _pendingVoiceUploads.remove(messageId);
        final pendingPath = pending?["path"]?.toString() ?? "";
        if (pendingPath.isNotEmpty) {
          try {
            final file = File(pendingPath);
            if (await file.exists()) {
              await file.delete();
            }
          } catch (_) {}
        }
        _messages = _messages.where((item) => _messageId(item) != messageId).toList();
        await _chatOutbox.removeByLocalMessageId(messageId);
        _selectedMessageIds.remove(messageId);
        deletedCount += 1;
        continue;
      }

      if (conversationId.isEmpty) {
        failedIds.add(messageId);
        continue;
      }

      try {
        await _chatApi.deleteMessage(
          session: widget.session,
          conversationId: conversationId,
          messageId: messageId,
        );
        _messages = _messages.where((item) => _messageId(item) != messageId).toList();
        _selectedMessageIds.remove(messageId);
        deletedCount += 1;
      } catch (_) {
        failedIds.add(messageId);
      }
    }

    if (!mounted) return;
    setState(() {
      if (failedIds.isEmpty) {
        _selectedMessageIds.clear();
      } else {
        _selectedMessageIds
          ..clear()
          ..addAll(failedIds);
      }
    });
    _scheduleCacheFlush();

    if (deletedCount > 0) {
      _showMessage(
        deletedCount == 1 ? "Message deleted." : "$deletedCount messages deleted.",
      );
    }
    if (failedIds.isNotEmpty) {
      _showMessage("Some messages could not be deleted.");
    }
  }

  List<Map<String, dynamic>> _sortMessages(List<Map<String, dynamic>> items) {
    final next = [...items];
    next.sort((a, b) {
      final aDate = DateTime.tryParse(a["created_at"]?.toString() ?? "");
      final bDate = DateTime.tryParse(b["created_at"]?.toString() ?? "");
      if (aDate == null && bDate == null) return 0;
      if (aDate == null) return -1;
      if (bDate == null) return 1;
      return aDate.compareTo(bDate);
    });
    return next;
  }

  String _formatTime(String? value) {
    final date = DateTime.tryParse(value ?? "")?.toLocal();
    if (date == null) return "";
    return DateFormat("hh:mm a").format(date);
  }

  String _formatDurationMs(int value) {
    final totalSeconds = (value / 1000).floor();
    final minutes = (totalSeconds ~/ 60).toString().padLeft(2, "0");
    final seconds = (totalSeconds % 60).toString().padLeft(2, "0");
    return "$minutes:$seconds";
  }

  String _formatDayLabel(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(date.year, date.month, date.day);
    final diff = today.difference(day).inDays;
    if (diff == 0) return "Today";
    if (diff == 1) return "Yesterday";
    return DateFormat("dd MMM yyyy").format(date);
  }

  List<Map<String, dynamic>> _buildFeedItems() {
    final items = <Map<String, dynamic>>[];
    String lastDay = "";
    for (final message in _messages) {
      final createdAt = DateTime.tryParse(
        message["created_at"]?.toString() ?? "",
      )?.toLocal();
      final dayLabel = createdAt != null ? _formatDayLabel(createdAt) : "";
      if (dayLabel.isNotEmpty && dayLabel != lastDay) {
        lastDay = dayLabel;
        items.add({"type": "day", "label": dayLabel, "key": "day-$dayLabel"});
      }
      items.add({
        "type": "message",
        "message": message,
        "key": message["id"]?.toString() ?? "",
      });
    }
    return items;
  }

  String? _resolveAudioUrl(String? raw) {
    if (raw == null || raw.trim().isEmpty) {
      return null;
    }
    final value = raw.trim();
    if (value.startsWith("http://") || value.startsWith("https://")) {
      return value;
    }
    final base = Uri.parse(AppConfig.apiBaseUrl);
    return base.replace(path: value).toString();
  }

  Future<void> _toggleAudio(Map<String, dynamic> message) async {
    final messageId = message["id"]?.toString() ?? "";
    final localAudioPath = message["_local_audio_path"]?.toString();
    final resolved = _resolveAudioUrl(message["audio_url"]?.toString());
    if ((resolved == null &&
            (localAudioPath == null || localAudioPath.isEmpty)) ||
        messageId.isEmpty) {
      return;
    }
    try {
      final isSameMessage = _playingMessageId == messageId;
      if (isSameMessage && _voicePlayer.playing) {
        await _voicePlayer.pause();
        if (mounted) setState(() => _playingMessageId = null);
        return;
      }
      if (!isSameMessage || !_voicePlayer.playing) {
        if (localAudioPath != null && localAudioPath.isNotEmpty) {
          final file = File(localAudioPath);
          if (await file.exists()) {
            await _voicePlayer.setFilePath(localAudioPath);
          } else if (resolved != null) {
            final tempPath = await _preparePlayableAudioFile(
              messageId: messageId,
              url: resolved,
            );
            await _voicePlayer.setFilePath(tempPath);
          } else {
            throw Exception("Audio not found.");
          }
        } else if (resolved != null) {
          final tempPath = await _preparePlayableAudioFile(
            messageId: messageId,
            url: resolved,
          );
          await _voicePlayer.setFilePath(tempPath);
        }
      }
      await _voicePlayer.play();
      if (!mounted) return;
      setState(() {
        _playingMessageId = messageId;
        if (!_isMine(message)) {
          _playedIncomingVoiceIds.add(messageId);
          _replaceMessageById(messageId, {
            ...message,
            "_voice_played": true,
          });
        }
      });
      _voicePlayer.playerStateStream
          .firstWhere(
            (state) => state.processingState == ProcessingState.completed,
          )
          .then((_) {
            if (mounted) setState(() => _playingMessageId = null);
          })
          .catchError((_) {});
    } catch (_) {
      _showMessage("Unable to play voice message.");
    }
  }

  Future<String> _preparePlayableAudioFile({
    required String messageId,
    required String url,
  }) async {
    final cached = _cachedAudioPaths[messageId];
    if (cached != null && await File(cached).exists()) {
      return cached;
    }
    final token = await _chatApi.resolveAccessToken(widget.session);
    final uri = Uri.parse(url);
    final client = HttpClient();
    try {
      final request = await client.getUrl(uri);
      request.headers.set(HttpHeaders.authorizationHeader, "Bearer $token");
      final response = await request.close();
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception("Audio download failed.");
      }
      final bytes = await consolidateHttpClientResponseBytes(response);
      final tempDir = await getTemporaryDirectory();
      final extension = _extractAudioExtension(url);
      final filePath =
          "${tempDir.path}${Platform.pathSeparator}chat_voice_$messageId$extension";
      final file = File(filePath);
      await file.writeAsBytes(bytes, flush: true);
      _cachedAudioPaths[messageId] = filePath;
      return filePath;
    } finally {
      client.close();
    }
  }

  String _extractAudioExtension(String url) {
    final path = Uri.tryParse(url)?.path.toLowerCase() ?? "";
    if (path.endsWith(".wav")) return ".wav";
    if (path.endsWith(".webm")) return ".webm";
    if (path.endsWith(".ogg")) return ".ogg";
    if (path.endsWith(".mp3")) return ".mp3";
    return ".m4a";
  }

  Future<void> _startRecording() async {
    if (_isRecording || _isUploadingVoice) return;
    try {
      var hasPermission = await _audioRecorder.hasPermission();
      if (!hasPermission) {
        final result = await Permission.microphone.request();
        hasPermission = result.isGranted;
      }
      if (!hasPermission) {
        _showMessage("Microphone permission is required.");
        return;
      }
      final tempDir = await getTemporaryDirectory();
      final ts = DateTime.now().millisecondsSinceEpoch;
      final recordingTargets = <Map<String, dynamic>>[
        {
          "path": "${tempDir.path}${Platform.pathSeparator}voice_$ts.wav",
          "config": const RecordConfig(
            encoder: AudioEncoder.wav,
            sampleRate: 16000,
          ),
        },
        {
          "path": "${tempDir.path}${Platform.pathSeparator}voice_$ts.m4a",
          "config": const RecordConfig(
            encoder: AudioEncoder.aacLc,
            bitRate: 128000,
            sampleRate: 44100,
          ),
        },
      ];
      var started = false;
      for (final target in recordingTargets) {
        try {
          await _audioRecorder.start(
            target["config"] as RecordConfig,
            path: target["path"] as String,
          );
          started = true;
          break;
        } catch (_) {}
      }
      if (!started) {
        throw Exception("No supported recording encoder.");
      }
      _recordingStopwatch
        ..reset()
        ..start();
      _recordingStartedAt = DateTime.now();
      _recordingTicker?.cancel();
      _recordingTicker = Timer.periodic(const Duration(milliseconds: 120), (_) {
        if (!mounted) return;
        setState(
          () => _recordingDurationMs = _recordingStopwatch.elapsedMilliseconds,
        );
      });
      setState(() {
        _isRecording = true;
        _recordingDurationMs = 0;
      });
      _sendRecording(true);
    } catch (_) {
      _showMessage("Unable to start recording.");
    }
  }

  Future<void> _cancelRecording() async {
    if (!_isRecording) return;
    try {
      await _audioRecorder.stop();
    } catch (_) {}
    _recordingTicker?.cancel();
    _recordingStopwatch
      ..stop()
      ..reset();
    _recordingStartedAt = null;
    if (mounted) {
      setState(() {
        _isRecording = false;
        _recordingDurationMs = 0;
      });
    }
    _sendRecording(false);
  }

  Future<void> _sendRecordedVoice() async {
    if (!_isRecording || _isUploadingVoice) return;
    setState(() => _isUploadingVoice = true);
    String? path;
    try {
      path = await _audioRecorder.stop();
      _recordingTicker?.cancel();
      _recordingStopwatch.stop();
      _sendRecording(false);

      final startedAt = _recordingStartedAt;
      final durationByWallClock = startedAt == null
          ? 0
          : DateTime.now().difference(startedAt).inMilliseconds;
      var duration = durationByWallClock > 0
          ? durationByWallClock
          : (_recordingDurationMs > 0
                ? _recordingDurationMs
                : _recordingStopwatch.elapsedMilliseconds);
      duration = duration < 1000 ? 1000 : duration;
      _recordingStopwatch.reset();
      _recordingStartedAt = null;
      setState(() {
        _isRecording = false;
        _recordingDurationMs = 0;
      });

      if (path == null || path.isEmpty) {
        _showMessage("Voice recording failed.");
        return;
      }
      final conversationId = _conversation["id"]?.toString() ?? "";
      if (conversationId.isEmpty) return;
      final localId = "local-voice-${DateTime.now().microsecondsSinceEpoch}";
      final localMessage = <String, dynamic>{
        "id": localId,
        "message_type": "VOICE",
        "content": "",
        "audio_url": "",
        "duration_ms": duration,
        "created_at": DateTime.now().toUtc().toIso8601String(),
        "updated_at": DateTime.now().toUtc().toIso8601String(),
        "sender_role": "DRIVER",
        "recipient_count": 1,
        "delivered_count": 0,
        "seen_count": 0,
        "_local_pending": true,
        "_upload_state": "uploading",
        "_local_audio_path": path,
      };
      setState(() {
        _messages = [..._messages, localMessage];
      });
      _scheduleCacheFlush();
      _scrollToBottom();
      _pendingVoiceUploads[localId] = {
        "conversation_id": conversationId,
        "path": path,
        "duration_ms": duration,
      };
      unawaited(_uploadPendingVoice(localId));
    } catch (e) {
      _showMessage(e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _isUploadingVoice = false);
    }
  }

  Future<void> _uploadPendingVoice(String localMessageId) async {
    final pending = _pendingVoiceUploads[localMessageId];
    if (pending == null) return;
    final conversationId = pending["conversation_id"]?.toString() ?? "";
    final path = pending["path"]?.toString() ?? "";
    final duration = pending["duration_ms"] as int? ?? 1000;
    try {
      final sent = await _chatApi.sendVoiceMessage(
        session: widget.session,
        conversationId: conversationId,
        audioFile: File(path),
        durationMs: duration,
      );
      if (!mounted) return;
      setState(() {
        _pendingVoiceUploads.remove(localMessageId);
        _messages = _messages
            .where((item) => item["id"]?.toString() != localMessageId)
            .toList();
        _upsertMessage(sent);
      });
      _scrollToBottom();
      final file = File(path);
      if (await file.exists()) {
        try {
          await file.delete();
        } catch (_) {}
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        final existing = _messages.firstWhere(
          (item) => item["id"]?.toString() == localMessageId,
          orElse: () => <String, dynamic>{},
        );
        if (existing.isNotEmpty) {
          _replaceMessageById(localMessageId, {
            ...existing,
            "_local_pending": false,
            "_upload_state": "failed",
          });
        }
      });
      final reason = e.toString().replaceFirst("Exception: ", "");
      _showMessage("Voice upload failed: $reason");
    }
  }

  Future<void> _retryVoiceUpload(String localMessageId) async {
    final pending = _pendingVoiceUploads[localMessageId];
    if (pending == null) return;
    setState(() {
      final existing = _messages.firstWhere(
        (item) => item["id"]?.toString() == localMessageId,
        orElse: () => <String, dynamic>{},
      );
      if (existing.isNotEmpty) {
        _replaceMessageById(localMessageId, {
          ...existing,
          "_upload_state": "uploading",
          "_local_pending": true,
        });
      }
    });
    await _uploadPendingVoice(localMessageId);
  }

  String _presenceLabel() {
    if (_counterpartIsTyping) return "typing...";
    if (_counterpartIsRecording) return "recording...";
    if (_counterpartIsOnline) return "online";
    final lastSeen = DateTime.tryParse(_counterpartLastSeenAt ?? "")?.toLocal();
    if (lastSeen != null) {
      return "last seen ${DateFormat("dd MMM, hh:mm a").format(lastSeen)}";
    }
    return _socketStatus == "connected" ? "chat ready" : "connecting...";
  }

  String _deliveryState(Map<String, dynamic> message) {
    if (message["_queued_offline"] == true) {
      return "queued_offline";
    }
    if (message["_local_pending"] == true) {
      return "pending";
    }
    final recipientCount =
        int.tryParse("${message["recipient_count"] ?? 0}") ?? 0;
    final deliveredCount =
        int.tryParse("${message["delivered_count"] ?? 0}") ?? 0;
    final seenCount = int.tryParse("${message["seen_count"] ?? 0}") ?? 0;
    if (recipientCount > 0 && seenCount >= recipientCount) {
      return "seen";
    }
    if (recipientCount > 0 && deliveredCount >= recipientCount) {
      return "delivered";
    }
    return "sent";
  }

  Widget _deliveryIcon(Map<String, dynamic> message) {
    final state = _deliveryState(message);
    if (state == "queued_offline") {
      return const Icon(
        Icons.cloud_off_rounded,
        size: 15,
        color: Color(0xFFE2E8F0),
      );
    }
    if (state == "pending") {
      return const SizedBox(
        width: 12,
        height: 12,
        child: CircularProgressIndicator(
          strokeWidth: 1.5,
          color: Color(0xFFFFFFFF),
        ),
      );
    }
    if (state == "seen") {
      return const Icon(
        Icons.done_all_rounded,
        size: 15,
        color: Color(0xFF93C5FD),
      );
    }
    if (state == "delivered") {
      return const Icon(
        Icons.done_all_rounded,
        size: 15,
        color: Color(0xFFE2E8F0),
      );
    }
    return const Icon(Icons.done_rounded, size: 15, color: Color(0xFFE2E8F0));
  }

  bool _isMine(Map<String, dynamic> message) {
    return message["sender_role"]?.toString() == "DRIVER";
  }

  bool _isIncomingVoiceUnplayed(Map<String, dynamic> message) {
    if (_isMine(message)) return false;
    if (message["message_type"]?.toString() != "VOICE") return false;
    if (message["_voice_played"] == true) return false;
    final messageId = message["id"]?.toString() ?? "";
    if (messageId.isEmpty) return true;
    return !_playedIncomingVoiceIds.contains(messageId);
  }

  void _hydratePlayedVoiceIds(List<Map<String, dynamic>> messages) {
    for (final message in messages) {
      if (message["message_type"]?.toString() != "VOICE") continue;
      if (_isMine(message)) continue;
      if (message["_voice_played"] == true) {
        final messageId = message["id"]?.toString() ?? "";
        if (messageId.isNotEmpty) {
          _playedIncomingVoiceIds.add(messageId);
        }
      }
    }
  }

  List<Map<String, dynamic>> _mergeVoicePlayedState({
    required List<Map<String, dynamic>> incoming,
    required List<Map<String, dynamic>> cached,
  }) {
    if (incoming.isEmpty) return incoming;
    if (cached.isEmpty) return incoming;
    final playedById = <String>{};
    for (final message in cached) {
      final messageId = message["id"]?.toString() ?? "";
      if (messageId.isEmpty) continue;
      if (message["_voice_played"] == true) {
        playedById.add(messageId);
      }
    }
    if (playedById.isEmpty) return incoming;
    return incoming
        .map((message) {
          final messageId = message["id"]?.toString() ?? "";
          if (messageId.isEmpty) return message;
          if (playedById.contains(messageId)) {
            return {
              ...message,
              "_voice_played": true,
            };
          }
          return message;
        })
        .toList();
  }

  Map<String, dynamic> _toMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return value.cast<String, dynamic>();
    return <String, dynamic>{};
  }

  @override
  Widget build(BuildContext context) {
    final feedItems = _buildFeedItems();

    return Scaffold(
      backgroundColor: const Color(0xFFF3F6FB),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: const Color(0xFF0F172A),
        titleSpacing: 0,
        leading: _isSelectionMode
            ? IconButton(
                onPressed: _clearSelection,
                icon: const Icon(Icons.close_rounded),
              )
            : null,
        title: _isSelectionMode
            ? Text(
                "${_selectedMessageIds.length} selected",
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _chatDisplayName(),
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                  Text(
                    _presenceLabel(),
                    style: TextStyle(
                      fontSize: 11,
                      color: _counterpartIsOnline
                          ? const Color(0xFF16A34A)
                          : const Color(0xFF64748B),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
        actions: _isSelectionMode
            ? [
                IconButton(
                  onPressed: _deleteSelectedMessages,
                  icon: const Icon(Icons.delete_outline_rounded),
                ),
              ]
            : const [],
      ),
      body: Column(
        children: [
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.chat_bubble_outline_rounded,
                            size: 34,
                            color: Color(0xFF94A3B8),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            _error!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Color(0xFFB91C1C),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 12),
                          ElevatedButton(
                            onPressed: _loadChat,
                            child: const Text("Retry"),
                          ),
                        ],
                      ),
                    ),
                  )
                : _conversation.isEmpty
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        "No company admin chat is available yet.",
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Color(0xFF64748B),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                    itemCount: feedItems.length,
                    itemBuilder: (context, index) {
                      final item = feedItems[index];
                      if (item["type"] == "day") {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Center(
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: const Color(0xFFE2E8F0),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                item["label"]?.toString() ?? "",
                                style: const TextStyle(
                                  color: Color(0xFF334155),
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ),
                        );
                      }
                      final message = _toMap(item["message"]);
                      final isMine = _isMine(message);
                      final isVoice =
                          message["message_type"]?.toString() == "VOICE";
                      final isIncomingVoiceUnplayed =
                          _isIncomingVoiceUnplayed(message);
                      final uploadState =
                          message["_upload_state"]?.toString() ?? "";
                      final canRetryVoice =
                          isVoice && isMine && uploadState == "failed";
                      final isSelected = _isSelectedMessage(message);
                      final canSelect = _canSelectMessage(message);
                      return Align(
                        alignment: isMine
                            ? Alignment.centerRight
                            : Alignment.centerLeft,
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onLongPress: canSelect
                              ? () => _toggleSelectionForMessage(message)
                              : null,
                          onTap: _isSelectionMode && canSelect
                              ? () => _toggleSelectionForMessage(message)
                              : null,
                          child: Container(
                          margin: const EdgeInsets.only(bottom: 10),
                          constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.75,
                            minWidth: isVoice ? 210 : 0,
                          ),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? (isMine
                                    ? const Color(0xFF0EA5E9)
                                    : const Color(0xFFE0F2FE))
                                : (isMine
                                    ? const Color(0xFF1D9BF0)
                                    : Colors.white),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(
                              color: isSelected
                                  ? const Color(0xFF0284C7)
                                  : (isMine
                                      ? const Color(0xFF1D9BF0)
                                      : const Color(0xFFE2E8F0)),
                              width: isSelected ? 1.5 : 1,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (isVoice)
                                InkWell(
                                  onTap: _isSelectionMode
                                      ? null
                                      : () => _toggleAudio(message),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        _playingMessageId ==
                                                    (message["id"]
                                                            ?.toString() ??
                                                        "") &&
                                                _voicePlayer.playing
                                            ? Icons.pause_circle_filled_rounded
                                            : Icons.play_circle_fill_rounded,
                                        color: isMine
                                            ? Colors.white
                                            : isIncomingVoiceUnplayed
                                            ? const Color(0xFF1D4ED8)
                                            : const Color(0xFF0F172A),
                                      ),
                                      const SizedBox(width: 8),
                                      Text(
                                        "Voice ${_formatDurationMs(int.tryParse("${message["duration_ms"] ?? 0}") ?? 0)}",
                                        style: TextStyle(
                                          color: isMine
                                              ? Colors.white
                                              : isIncomingVoiceUnplayed
                                              ? const Color(0xFF1D4ED8)
                                              : const Color(0xFF0F172A),
                                          fontSize: 14,
                                          fontWeight: isIncomingVoiceUnplayed
                                              ? FontWeight.w800
                                              : FontWeight.w700,
                                        ),
                                      ),
                                      if (canRetryVoice) ...[
                                        const SizedBox(width: 8),
                                        InkWell(
                                          onTap: _isSelectionMode
                                              ? null
                                              : () => _retryVoiceUpload(
                                                  message["id"]?.toString() ??
                                                      "",
                                                ),
                                          child: Icon(
                                            Icons.refresh_rounded,
                                            color: isMine
                                                ? const Color(0xFFE2E8F0)
                                                : const Color(0xFF334155),
                                            size: 18,
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                )
                              else
                                Text(
                                  message["content"]?.toString() ?? "",
                                  style: TextStyle(
                                    color: isMine
                                        ? Colors.white
                                        : const Color(0xFF0F172A),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              const SizedBox(height: 6),
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    _formatTime(
                                      message["created_at"]?.toString(),
                                    ),
                                    style: TextStyle(
                                      color: isMine
                                          ? const Color(0xFFE2E8F0)
                                          : const Color(0xFF94A3B8),
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  if (isMine) ...[
                                    const SizedBox(width: 4),
                                    _deliveryIcon(message),
                                  ],
                                ],
                              ),
                            ],
                          ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
          SafeArea(
            top: false,
            child: Container(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (_isRecording)
                          Container(
                            width: double.infinity,
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF1F5F9),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: const Color(0xFFE2E8F0),
                              ),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.mic_rounded,
                                  color: Color(0xFFDC2626),
                                  size: 18,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  _formatDurationMs(_recordingDurationMs),
                                  style: const TextStyle(
                                    color: Color(0xFF0F172A),
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const Spacer(),
                                TextButton(
                                  onPressed: _cancelRecording,
                                  child: const Text("Cancel"),
                                ),
                                const SizedBox(width: 6),
                                ElevatedButton(
                                  onPressed: _isUploadingVoice
                                      ? null
                                      : _sendRecordedVoice,
                                  child: _isUploadingVoice
                                      ? const SizedBox(
                                          width: 14,
                                          height: 14,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : const Text("Send"),
                                ),
                              ],
                            ),
                          ),
                        TextField(
                          controller: _composerController,
                          enabled: !_isSelectionMode,
                          minLines: 1,
                          maxLines: 4,
                          textInputAction: TextInputAction.newline,
                          decoration: InputDecoration(
                            hintText: _isRecording
                                ? "Recording..."
                                : "Type your message...",
                            filled: true,
                            fillColor: const Color(0xFFF8FAFC),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 14,
                            ),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(16),
                              borderSide: const BorderSide(
                                color: Color(0xFFE2E8F0),
                              ),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(16),
                              borderSide: const BorderSide(
                                color: Color(0xFFE2E8F0),
                              ),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(16),
                              borderSide: const BorderSide(
                                color: Color(0xFF1D9BF0),
                              ),
                            ),
                          ),
                          onSubmitted: (_) => _sendMessage(),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    height: 52,
                    width: 52,
                    child: ElevatedButton(
                      onPressed: _isSelectionMode
                          ? null
                          : _isRecording
                          ? null
                          : _hasComposerText
                          ? (_isSending ? null : _sendMessage)
                          : _startRecording,
                      style: ElevatedButton.styleFrom(
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                        backgroundColor: const Color(0xFF0F172A),
                        foregroundColor: Colors.white,
                      ),
                      child: _isSending
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : Icon(
                              _hasComposerText
                                  ? Icons.send_rounded
                                  : Icons.mic_rounded,
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
