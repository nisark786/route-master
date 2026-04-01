import "package:flutter/material.dart";
import "package:intl/intl.dart";
import "package:url_launcher/url_launcher.dart";

import "../../../core/storage/auth_storage.dart";
import "../../auth/data/auth_api.dart";
import "../../auth/domain/auth_session.dart";
import "../../auth/presentation/login_page.dart";
import "../data/shop_owner_api.dart";

class ShopOwnerHomePage extends StatefulWidget {
  const ShopOwnerHomePage({super.key, required this.session});

  final AuthSession session;

  @override
  State<ShopOwnerHomePage> createState() => _ShopOwnerHomePageState();
}

class _ShopOwnerHomePageState extends State<ShopOwnerHomePage> {
  final _shopOwnerApi = ShopOwnerApi();
  final _authApi = AuthApi();

  bool _isLoading = true;
  bool _isLoggingOut = false;
  String? _error;
  Map<String, dynamic> _metrics = const {};
  List<Map<String, dynamic>> _deliveries = const [];
  List<Map<String, dynamic>> _recentInvoices = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final dashboard = await _shopOwnerApi.getDashboard(widget.session);
      final deliveries = await _shopOwnerApi.listDeliveries(widget.session);

      if (!mounted) return;
      setState(() {
        _metrics = (dashboard["metrics"] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
        _recentInvoices = (dashboard["recent_invoices"] as List? ?? const [])
            .whereType<Map>()
            .map((item) => item.cast<String, dynamic>())
            .toList();
        _deliveries = deliveries;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _logout() async {
    if (_isLoggingOut) return;
    setState(() => _isLoggingOut = true);
    try {
      await _authApi.logout(
        widget.session.accessToken,
        refreshToken: widget.session.refreshToken,
      );
    } catch (_) {}
    await AuthStorage.clearSession();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginPage()),
      (route) => false,
    );
  }

  Future<void> _openInvoice(String url) async {
    if (url.trim().isEmpty) return;
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  String _formatDateTime(dynamic value) {
    final parsed = DateTime.tryParse(value?.toString() ?? "");
    if (parsed == null) return "-";
    return DateFormat("dd MMM yyyy, hh:mm a").format(parsed.toLocal());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Shop Owner Dashboard"),
        actions: [
          IconButton(onPressed: _isLoading ? null : _load, icon: const Icon(Icons.refresh)),
          TextButton(
            onPressed: _isLoggingOut ? null : _logout,
            child: Text(_isLoggingOut ? "..." : "Logout"),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
                : ListView(
                    children: [
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                "Today Overview",
                                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 10),
                              Text("Open Deliveries: ${_metrics["open_deliveries"] ?? 0}"),
                              Text("Pending: ${_metrics["pending_deliveries"] ?? 0}"),
                              Text("Checked In: ${_metrics["checked_in_deliveries"] ?? 0}"),
                              Text("Completed Today: ${_metrics["completed_today"] ?? 0}"),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                "Deliveries",
                                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 10),
                              if (_deliveries.isEmpty)
                                const Text("No deliveries found.")
                              else
                                ..._deliveries.take(30).map(
                                  (delivery) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      "${delivery["route_name"] ?? "-"} | ${delivery["status"] ?? "-"}",
                                      style: const TextStyle(fontWeight: FontWeight.w700),
                                    ),
                                    subtitle: Text(
                                      "Driver: ${delivery["driver_name"] ?? "-"}\n"
                                      "Checked In: ${_formatDateTime(delivery["check_in_at"])}",
                                    ),
                                    trailing: (delivery["invoice_url"]?.toString() ?? "").isNotEmpty
                                        ? IconButton(
                                            icon: const Icon(Icons.receipt_long),
                                            onPressed: () => _openInvoice(delivery["invoice_url"].toString()),
                                          )
                                        : null,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                "Recent Invoices",
                                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                              ),
                              const SizedBox(height: 10),
                              if (_recentInvoices.isEmpty)
                                const Text("No invoices generated yet.")
                              else
                                ..._recentInvoices.map(
                                  (invoice) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      "${invoice["invoice_number"] ?? "-"} | INR ${invoice["invoice_total"] ?? "0.00"}",
                                      style: const TextStyle(fontWeight: FontWeight.w700),
                                    ),
                                    subtitle: Text(_formatDateTime(invoice["check_out_at"])),
                                    trailing: IconButton(
                                      icon: const Icon(Icons.open_in_new),
                                      onPressed: () => _openInvoice(invoice["invoice_url"]?.toString() ?? ""),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
      ),
    );
  }
}
