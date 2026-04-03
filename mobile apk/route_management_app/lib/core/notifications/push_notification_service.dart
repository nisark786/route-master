import "package:firebase_core/firebase_core.dart";
import "package:firebase_messaging/firebase_messaging.dart";
import "package:shared_preferences/shared_preferences.dart";

import "local_notification_service.dart";

const String _fcmTokenStorageKey = "push.fcm_token";

@pragma("vm:entry-point")
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  await LocalNotificationService.instance.initialize();
  final messageId =
      message.messageId ??
      message.data["message_id"]?.toString() ??
      DateTime.now().microsecondsSinceEpoch.toString();
  final title = message.notification?.title?.trim();
  final body = message.notification?.body?.trim();
  await LocalNotificationService.instance.showIncomingChatMessage(
    messageId: messageId,
    title: (title == null || title.isEmpty) ? "Route Master" : title,
    body: (body == null || body.isEmpty) ? "New message" : body,
  );
}

class PushNotificationService {
  PushNotificationService._();

  static final PushNotificationService instance = PushNotificationService._();
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  Future<void> initialize() async {
    await _messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );

    await _saveToken(await _messaging.getToken());
    _messaging.onTokenRefresh.listen(_saveToken);

    FirebaseMessaging.onMessage.listen((message) async {
      await LocalNotificationService.instance.initialize();
      final messageId =
          message.messageId ??
          message.data["message_id"]?.toString() ??
          DateTime.now().microsecondsSinceEpoch.toString();
      final title = message.notification?.title?.trim();
      final body = message.notification?.body?.trim();
      await LocalNotificationService.instance.showIncomingChatMessage(
        messageId: messageId,
        title: (title == null || title.isEmpty) ? "Route Master" : title,
        body: (body == null || body.isEmpty) ? "New message" : body,
      );
    });

    await _messaging.getInitialMessage();
  }

  Future<void> _saveToken(String? token) async {
    if (token == null || token.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_fcmTokenStorageKey, token);
  }

  Future<String?> getSavedToken() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_fcmTokenStorageKey);
    if (token == null || token.trim().isEmpty) return null;
    return token;
  }

  Future<String?> getOrRefreshToken() async {
    final saved = await getSavedToken();
    if (saved != null && saved.isNotEmpty) return saved;
    final fresh = await _messaging.getToken();
    await _saveToken(fresh);
    return fresh;
  }
}
