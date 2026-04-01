import "package:flutter/foundation.dart";

class AppConfig {
  static const String _apiBaseUrlFromEnv = String.fromEnvironment(
    "API_BASE_URL",
    defaultValue: "",
  );

  static String get apiBaseUrl {
    final fromEnv = _apiBaseUrlFromEnv.trim();
    if (fromEnv.isNotEmpty && !_looksLikePlaceholder(fromEnv)) return fromEnv;
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      if (kReleaseMode) {
        throw StateError(
          "API_BASE_URL is required for Android APK builds. "
          "Use --dart-define=API_BASE_URL=http://192.168.220.81:8000/api",
        );
      }
      return "http://192.168.220.81:8000/api";
    }
    return "http://127.0.0.1:8000/api";
  }

  static bool _looksLikePlaceholder(String value) {
    final normalized = value.toLowerCase();
    return normalized.contains("192.168.x.x") || normalized.contains("x.x.x.x");
  }
}
