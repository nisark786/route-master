import "package:flutter/material.dart";
import "package:url_launcher/url_launcher.dart";

import "../../auth/domain/auth_session.dart";
import "../data/driver_api.dart";

class DriverStopInvoicePage extends StatefulWidget {
  const DriverStopInvoicePage({
    super.key,
    required this.session,
    required this.assignmentId,
    required this.shopId,
    required this.whatsappUrl,
  });

  final AuthSession session;
  final String assignmentId;
  final String shopId;
  final String whatsappUrl;

  @override
  State<DriverStopInvoicePage> createState() => _DriverStopInvoicePageState();
}

class _DriverStopInvoicePageState extends State<DriverStopInvoicePage> {
  final _driverApi = DriverApi();
  bool _isLoading = true;
  bool _isMutating = false;
  String? _error;
  Map<String, dynamic> _stopData = const {};

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
      final payload = await _driverApi.getStopDetail(
        session: widget.session,
        assignmentId: widget.assignmentId,
        shopId: widget.shopId,
      );
      final stop = (payload["stop"] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
      if (!mounted) return;
      setState(() => _stopData = stop);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _sendWhatsappInvoice() async {
    final url = widget.whatsappUrl.trim();
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("WhatsApp invoice link not available.")),
      );
      return;
    }
    final uri = Uri.parse(url);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _viewInvoicePdf() async {
    final invoiceUrl = (_stopData["invoice_url"]?.toString() ?? "").trim();
    if (invoiceUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Invoice PDF not found.")),
      );
      return;
    }
    final uri = Uri.parse(invoiceUrl);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _checkOut() async {
    if (_isMutating) return;
    setState(() => _isMutating = true);
    try {
      final response = await _driverApi.checkOutStop(
        session: widget.session,
        assignmentId: widget.assignmentId,
        shopId: widget.shopId,
      );
      if (!mounted) return;
      if (response["queued_offline"] == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("No internet. Check-out saved offline and will sync automatically."),
          ),
        );
      }
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
      setState(() => _isMutating = false);
    }
  }

  double _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? "0") ?? 0;
  }

  @override
  Widget build(BuildContext context) {
    final items = (_stopData["ordered_items"] as List? ?? const [])
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();

    final totalFromStop = _toDouble(_stopData["invoice_total"]);
    final totalFromItems = items.fold<double>(
      0,
      (sum, item) => sum + _toDouble(item["line_total"]),
    );
    final grandTotal = totalFromStop > 0 ? totalFromStop : totalFromItems;

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FB),
      appBar: AppBar(title: const Text("Invoice Summary")),
      body: Padding(
        padding: const EdgeInsets.all(14),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
                : Column(
                    children: [
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _stopData["shop_name"]?.toString() ?? "Shop",
                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              "Invoice #: ${_stopData["invoice_number"] ?? "-"}",
                              style: const TextStyle(color: Color(0xFF64748B)),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                      Expanded(
                        child: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: const Color(0xFFE2E8F0)),
                          ),
                          child: items.isEmpty
                              ? const Center(child: Text("No ordered items found."))
                              : ListView.separated(
                                  itemCount: items.length,
                                  separatorBuilder: (_, _) => const Divider(height: 16),
                                  itemBuilder: (context, index) {
                                    final item = items[index];
                                    return Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            item["name"]?.toString() ?? "Item",
                                            style: const TextStyle(fontWeight: FontWeight.w600),
                                          ),
                                        ),
                                        Text(
                                          "${item["quantity"]} x Rs ${item["rate"]} = Rs ${item["line_total"]}",
                                          style: const TextStyle(fontWeight: FontWeight.w700),
                                        ),
                                      ],
                                    );
                                  },
                                ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Text(
                          "Grand Total: Rs ${grandTotal.toStringAsFixed(2)}",
                          textAlign: TextAlign.right,
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _viewInvoicePdf,
                              icon: const Icon(Icons.picture_as_pdf_outlined),
                              label: const Text("View PDF"),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: _sendWhatsappInvoice,
                              icon: const Icon(Icons.send_outlined),
                              label: const Text("Send WhatsApp"),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isMutating ? null : _checkOut,
                          child: const Text("Check Out"),
                        ),
                      ),
                    ],
                  ),
      ),
    );
  }
}
