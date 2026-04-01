import "package:flutter/material.dart";

import "../../../core/storage/auth_storage.dart";
import "../../auth/data/auth_api.dart";
import "../../auth/domain/auth_session.dart";
import "../../auth/presentation/login_page.dart";

class RoleHomeScaffold extends StatefulWidget {
  const RoleHomeScaffold({
    super.key,
    required this.title,
    required this.subtitle,
    required this.session,
  });

  final String title;
  final String subtitle;
  final AuthSession session;

  @override
  State<RoleHomeScaffold> createState() => _RoleHomeScaffoldState();
}

class _RoleHomeScaffoldState extends State<RoleHomeScaffold> {
  bool _isLoggingOut = false;
  final _authApi = AuthApi();

  Future<void> _logout() async {
    if (_isLoggingOut) return;
    setState(() => _isLoggingOut = true);

    try {
      await _authApi.logout(
        widget.session.accessToken,
        refreshToken: widget.session.refreshToken,
      );
    } catch (_) {
      // Ignore logout API errors and clear local session anyway.
    }

    await AuthStorage.clearSession();
    if (!mounted) return;

    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginPage()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "ROUTEMASTER",
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          TextButton(
            onPressed: _isLoggingOut ? null : _logout,
            child: Text(_isLoggingOut ? "..." : "Logout"),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.title,
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      widget.subtitle,
                      style: const TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w600),
                    ),
                    const Divider(height: 24),
                    Text(
                      "Signed in as: ${widget.session.email}",
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    if ((widget.session.companyId ?? "").isNotEmpty)
                      Text(
                        "Company: ${widget.session.companyId}",
                        style: const TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w600),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  "Backend auth connected. Add role-specific features here next.",
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
