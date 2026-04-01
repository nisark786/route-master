import "package:flutter/material.dart";

import "../../../core/storage/auth_storage.dart";
import "../../driver/presentation/driver_home_page.dart";
import "../../shop_owner/presentation/shop_owner_home_page.dart";
import "../data/auth_api.dart";
import "../domain/auth_session.dart";

class ChangeInitialPasswordPage extends StatefulWidget {
  const ChangeInitialPasswordPage({super.key, required this.session});

  final AuthSession session;

  @override
  State<ChangeInitialPasswordPage> createState() => _ChangeInitialPasswordPageState();
}

class _ChangeInitialPasswordPageState extends State<ChangeInitialPasswordPage> {
  final _formKey = GlobalKey<FormState>();
  final _currentPasswordController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _authApi = AuthApi();

  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _currentPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      await _authApi.changeInitialPassword(
        accessToken: widget.session.accessToken,
        currentPassword: _currentPasswordController.text,
        newPassword: _newPasswordController.text,
      );

      final updatedSession = AuthSession(
        accessToken: widget.session.accessToken,
        refreshToken: widget.session.refreshToken,
        role: widget.session.role,
        email: widget.session.email,
        companyId: widget.session.companyId,
        mustChangePassword: false,
      );
      await AuthStorage.saveSession(updatedSession);

      if (!mounted) return;
      if (updatedSession.role == UserRole.driver) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => DriverHomePage(session: updatedSession)),
          (route) => false,
        );
      } else {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => ShopOwnerHomePage(session: updatedSession)),
          (route) => false,
        );
      }
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          "Change Temporary Password",
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          "You must set a new password before continuing.",
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 20),
                        TextFormField(
                          controller: _currentPasswordController,
                          obscureText: true,
                          decoration: const InputDecoration(labelText: "Temporary Password"),
                          validator: (value) =>
                              (value ?? "").isEmpty ? "Temporary password is required." : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _newPasswordController,
                          obscureText: true,
                          decoration: const InputDecoration(labelText: "New Password"),
                          validator: (value) {
                            if ((value ?? "").length < 8) return "New password must be at least 8 characters.";
                            return null;
                          },
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _confirmPasswordController,
                          obscureText: true,
                          decoration: const InputDecoration(labelText: "Confirm New Password"),
                          validator: (value) {
                            if (value != _newPasswordController.text) return "Password confirmation does not match.";
                            return null;
                          },
                        ),
                        const SizedBox(height: 16),
                        if (_error != null) ...[
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFEF2F2),
                              border: Border.all(color: const Color(0xFFFECACA)),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              _error!,
                              style: const TextStyle(color: Color(0xFFB91C1C), fontWeight: FontWeight.w600),
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],
                        ElevatedButton(
                          onPressed: _isLoading ? null : _submit,
                          child: _isLoading
                              ? const SizedBox(
                                  height: 18,
                                  width: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Text("Update Password"),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
