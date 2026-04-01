enum UserRole {
  driver,
  shopOwner,
}

class AuthSession {
  const AuthSession({
    required this.accessToken,
    this.refreshToken,
    required this.role,
    required this.email,
    required this.mustChangePassword,
    this.companyId,
  });

  final String accessToken;
  final String? refreshToken;
  final UserRole role;
  final String email;
  final bool mustChangePassword;
  final String? companyId;

  AuthSession copyWith({
    String? accessToken,
    String? refreshToken,
    UserRole? role,
    String? email,
    bool? mustChangePassword,
    String? companyId,
  }) {
    return AuthSession(
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      role: role ?? this.role,
      email: email ?? this.email,
      mustChangePassword: mustChangePassword ?? this.mustChangePassword,
      companyId: companyId ?? this.companyId,
    );
  }

  static UserRole? parseRole(String? role) {
    if (role == "DRIVER") return UserRole.driver;
    if (role == "SHOP_OWNER") return UserRole.shopOwner;
    return null;
  }
}
