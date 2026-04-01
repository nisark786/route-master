import "dart:async";

import "package:firebase_core/firebase_core.dart";
import "package:firebase_messaging/firebase_messaging.dart";
import "package:flutter/material.dart";
import "package:flutter/services.dart";

import "app/app_theme.dart";
import "core/notifications/local_notification_service.dart";
import "core/notifications/push_notification_service.dart";
import "core/storage/auth_storage.dart";
import "features/auth/domain/auth_session.dart";
import "features/auth/presentation/change_initial_password_page.dart";
import "features/auth/presentation/login_page.dart";
import "features/driver/data/foreground_location_service.dart";
import "features/driver/data/driver_chat_api.dart";
import "features/driver/data/driver_chat_sync_service.dart";
import "features/driver/data/driver_sync_service.dart";
import "features/driver/presentation/driver_home_page.dart";
import "features/shop_owner/presentation/shop_owner_home_page.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
  await LocalNotificationService.instance.initialize();
  await PushNotificationService.instance.initialize();
  await ForegroundLocationService.instance.initialize();
  runApp(const RouteMasterDriverApp());
}

class RouteMasterDriverApp extends StatelessWidget {
  const RouteMasterDriverApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "RouteMaster",
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const AuthGate(),
    );
  }
}

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  late Future<AuthSession?> _sessionFuture;
  final _chatApi = DriverChatApi();
  bool _pushSyncInProgress = false;
  String? _activeDriverSyncKey;

  @override
  void initState() {
    super.initState();
    _sessionFuture = AuthStorage.loadSession();
  }

  Future<void> _syncDriverPushToken(AuthSession session) async {
    if (_pushSyncInProgress || session.role != UserRole.driver) return;
    _pushSyncInProgress = true;
    try {
      final token = await PushNotificationService.instance.getOrRefreshToken();
      if (token == null || token.isEmpty) return;
      await _chatApi.registerPushToken(session: session, token: token);
    } catch (_) {
      // Keep login/app flow resilient even if push registration fails.
    } finally {
      _pushSyncInProgress = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<AuthSession?>(
      future: _sessionFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final session = snapshot.data;
        if (session == null) {
          return const LoginPage();
        }

        if (session.mustChangePassword) {
          return ChangeInitialPasswordPage(session: session);
        }

        if (session.role == UserRole.driver) {
          final syncKey = "${session.email}|${session.companyId ?? ""}";
          if (_activeDriverSyncKey != syncKey) {
            _activeDriverSyncKey = syncKey;
            DriverSyncService.instance.start(session);
            DriverChatSyncService.instance.start(session);
          }
          unawaited(_syncDriverPushToken(session));
          return DriverHomePage(session: session);
        }

        if (session.role == UserRole.shopOwner) {
          if (_activeDriverSyncKey != null) {
            _activeDriverSyncKey = null;
            DriverSyncService.instance.stop();
            DriverChatSyncService.instance.stop();
          }
          return ShopOwnerHomePage(session: session);
        }

        if (_activeDriverSyncKey != null) {
          _activeDriverSyncKey = null;
          DriverSyncService.instance.stop();
          DriverChatSyncService.instance.stop();
        }
        return const LoginPage(
          initialError:
              "Only DRIVER and SHOP_OWNER accounts are allowed in this app.",
        );
      },
    );
  }
}
