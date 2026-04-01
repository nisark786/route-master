import "package:shared_preferences/shared_preferences.dart";

import "../../features/auth/domain/auth_session.dart";

class AuthStorage {
  static const _keyToken = "auth.access_token";
  static const _keyRefreshToken = "auth.refresh_token";
  static const _keyRole = "auth.role";
  static const _keyEmail = "auth.email";
  static const _keyCompanyId = "auth.company_id";
  static const _keyMustChangePassword = "auth.must_change_password";

  static Future<void> saveSession(AuthSession session) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyToken, session.accessToken);
    if ((session.refreshToken ?? "").isNotEmpty) {
      await prefs.setString(_keyRefreshToken, session.refreshToken!);
    } else {
      await prefs.remove(_keyRefreshToken);
    }
    await prefs.setString(
      _keyRole,
      session.role == UserRole.driver ? "DRIVER" : "SHOP_OWNER",
    );
    await prefs.setString(_keyEmail, session.email);
    await prefs.setBool(_keyMustChangePassword, session.mustChangePassword);
    if (session.companyId != null && session.companyId!.isNotEmpty) {
      await prefs.setString(_keyCompanyId, session.companyId!);
    } else {
      await prefs.remove(_keyCompanyId);
    }
  }

  static Future<AuthSession?> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_keyToken);
    final refreshToken = prefs.getString(_keyRefreshToken);
    final roleValue = prefs.getString(_keyRole);
    final email = prefs.getString(_keyEmail);
    final role = AuthSession.parseRole(roleValue);
    final mustChangePassword = prefs.getBool(_keyMustChangePassword) ?? false;

    if (token == null || token.isEmpty || role == null || email == null || email.isEmpty) {
      return null;
    }

    return AuthSession(
      accessToken: token,
      refreshToken: refreshToken,
      role: role,
      email: email,
      mustChangePassword: mustChangePassword,
      companyId: prefs.getString(_keyCompanyId),
    );
  }

  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyToken);
    await prefs.remove(_keyRefreshToken);
    await prefs.remove(_keyRole);
    await prefs.remove(_keyEmail);
    await prefs.remove(_keyCompanyId);
    await prefs.remove(_keyMustChangePassword);
  }
}
