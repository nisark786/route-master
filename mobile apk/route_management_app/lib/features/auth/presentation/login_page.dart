import "dart:async";

import "package:flutter/material.dart";

import "../../../core/notifications/push_notification_service.dart";
import "../../../core/storage/auth_storage.dart";
import "../../driver/data/driver_chat_api.dart";
import "../../driver/presentation/driver_home_page.dart";
import "../../shop_owner/presentation/shop_owner_home_page.dart";
import "../data/auth_api.dart";
import "../domain/auth_session.dart";
import "change_initial_password_page.dart";

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, this.initialError});

  final String? initialError;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _identifierController = TextEditingController();
  final _passwordController = TextEditingController();
  final _authApi = AuthApi();
  final _chatApi = DriverChatApi();

  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _error = widget.initialError;
  }

  @override
  void dispose() {
    _identifierController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final session = await _authApi.login(
        identifier: _identifierController.text,
        password: _passwordController.text,
      );
      await AuthStorage.saveSession(session);

      if (!mounted) return;

      if (session.mustChangePassword) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => ChangeInitialPasswordPage(session: session),
          ),
        );
        return;
      }

      if (session.role == UserRole.driver) {
        unawaited(_registerPushToken(session));
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => DriverHomePage(session: session)),
        );
        return;
      }

      if (session.role == UserRole.shopOwner) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => ShopOwnerHomePage(session: session),
          ),
        );
        return;
      }

      setState(
        () => _error = "Only DRIVER and SHOP_OWNER can login in this app.",
      );
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _registerPushToken(AuthSession session) async {
    try {
      final token = await PushNotificationService.instance.getOrRefreshToken();
      if (token == null || token.isEmpty) return;
      await _chatApi.registerPushToken(session: session, token: token);
    } catch (_) {
      // Non-blocking: login should not fail on push token errors.
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
                        const SizedBox(height: 8),
                        const Text(
                          "ROUTEMASTER",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.6,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          "Driver / Shop Owner Login",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF64748B),
                          ),
                        ),
                        const SizedBox(height: 24),
                        TextFormField(
                          controller: _identifierController,
                          keyboardType: TextInputType.phone,
                          autocorrect: false,
                          decoration: const InputDecoration(
                            labelText: "Mobile Number",
                            hintText: "Enter mobile number",
                          ),
                          validator: (value) {
                            final input = (value ?? "").trim();
                            if (input.isEmpty) {
                              return "Mobile number is required.";
                            }
                            if (input.length < 8) {
                              return "Enter a valid mobile number.";
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: "Password",
                          ),
                          validator: (value) {
                            if ((value ?? "").isEmpty) {
                              return "Password is required.";
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 16),
                        if (_error != null) ...[
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFEF2F2),
                              border: Border.all(
                                color: const Color(0xFFFECACA),
                              ),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              _error!,
                              style: const TextStyle(
                                color: Color(0xFFB91C1C),
                                fontWeight: FontWeight.w600,
                              ),
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
                              : const Text("Login"),
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
