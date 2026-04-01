import "package:flutter_local_notifications/flutter_local_notifications.dart";

class LocalNotificationService {
  LocalNotificationService._();

  static final LocalNotificationService instance = LocalNotificationService._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  final Set<String> _shownMessageIds = <String>{};
  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings(
      "@mipmap/ic_launcher",
    );
    const settings = InitializationSettings(android: androidSettings);
    await _plugin.initialize(settings);

    const channel = AndroidNotificationChannel(
      "chat_messages",
      "Chat Messages",
      description: "Notifications for incoming chat messages.",
      importance: Importance.high,
    );
    await _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(channel);
    await _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.requestNotificationsPermission();

    _initialized = true;
  }

  Future<void> showIncomingChatMessage({
    required String messageId,
    required String title,
    required String body,
  }) async {
    if (!_initialized || messageId.isEmpty) return;
    if (_shownMessageIds.contains(messageId)) return;

    _shownMessageIds.add(messageId);
    if (_shownMessageIds.length > 500) {
      _shownMessageIds.remove(_shownMessageIds.first);
    }

    const androidDetails = AndroidNotificationDetails(
      "chat_messages",
      "Chat Messages",
      channelDescription: "Notifications for incoming chat messages.",
      importance: Importance.high,
      priority: Priority.high,
      category: AndroidNotificationCategory.message,
      styleInformation: BigTextStyleInformation(""),
    );

    const details = NotificationDetails(android: androidDetails);
    await _plugin.show(
      messageId.hashCode,
      title,
      body,
      details,
      payload: "chat_message:$messageId",
    );
  }
}
