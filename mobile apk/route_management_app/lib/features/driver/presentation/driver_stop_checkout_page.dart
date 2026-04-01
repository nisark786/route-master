import "package:flutter/material.dart";
import "package:flutter/services.dart";

import "../../auth/domain/auth_session.dart";
import "../data/driver_api.dart";
import "driver_stop_invoice_page.dart";

class DriverStopCheckoutPage extends StatefulWidget {
  const DriverStopCheckoutPage({
    super.key,
    required this.session,
    required this.assignmentId,
    required this.shopId,
  });

  final AuthSession session;
  final String assignmentId;
  final String shopId;

  @override
  State<DriverStopCheckoutPage> createState() => _DriverStopCheckoutPageState();
}

class _DriverStopCheckoutPageState extends State<DriverStopCheckoutPage> {
  final _driverApi = DriverApi();
  bool _isLoading = true;
  bool _isMutating = false;
  String? _error;
  List<Map<String, dynamic>> _products = const [];
  final Map<String, TextEditingController> _qtyControllers = {};
  String _query = "";

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final controller in _qtyControllers.values) {
      controller.dispose();
    }
    super.dispose();
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
      final products = (payload["products"] as List? ?? const [])
          .whereType<Map>()
          .map((item) => item.cast<String, dynamic>())
          .toList();

      final activeIds = products
          .map((product) => product["id"]?.toString() ?? "")
          .where((id) => id.isNotEmpty)
          .toSet();
      _qtyControllers.removeWhere((productId, controller) {
        if (activeIds.contains(productId)) return false;
        controller.dispose();
        return true;
      });

      for (final product in products) {
        final id = product["id"]?.toString() ?? "";
        if (id.isEmpty) continue;
        _qtyControllers.putIfAbsent(id, () => TextEditingController(text: ""));
      }

      if (!mounted) return;
      setState(() => _products = products);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  int _qtyOf(String id) {
    final raw = _qtyControllers[id]?.text.trim() ?? "";
    return int.tryParse(raw) ?? 0;
  }

  void _setQtyWithClamp({
    required String productId,
    required int maxAllowed,
    required String rawValue,
  }) {
    final parsed = int.tryParse(rawValue.trim()) ?? 0;
    final next = parsed < 0 ? 0 : (parsed > maxAllowed ? maxAllowed : parsed);
    final controller = _qtyControllers[productId];
    if (controller == null) return;
    final text = next <= 0 ? "" : next.toString();
    if (controller.text != text) {
      controller.value = TextEditingValue(
        text: text,
        selection: TextSelection.collapsed(offset: text.length),
      );
    }
    if (parsed > maxAllowed) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Cannot exceed available quantity ($maxAllowed)."),
        ),
      );
    }
    setState(() {});
  }

  Future<void> _completeOrderAndOpenInvoice() async {
    if (_isMutating) return;

    final items = <Map<String, dynamic>>[];
    for (final product in _products) {
      final id = product["id"]?.toString() ?? "";
      if (id.isEmpty) continue;
      final qty = _qtyOf(id);
      if (qty > 0) {
        items.add({"product_id": id, "quantity": qty});
      }
    }

    if (items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Enter quantity for at least one product."),
        ),
      );
      return;
    }

    setState(() => _isMutating = true);
    try {
      final payload = await _driverApi.completeStopOrder(
        session: widget.session,
        assignmentId: widget.assignmentId,
        shopId: widget.shopId,
        items: items,
      );

      if (!mounted) return;
      if (payload["queued_offline"] == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              "No internet. Invoice data saved offline and will sync automatically.",
            ),
          ),
        );
        Navigator.of(context).pop(true);
        return;
      }

      final whatsappUrl = payload["whatsapp_url"]?.toString() ?? "";
      final checkedOut = await Navigator.of(context).push<bool>(
        MaterialPageRoute(
          builder: (_) => DriverStopInvoicePage(
            session: widget.session,
            assignmentId: widget.assignmentId,
            shopId: widget.shopId,
            whatsappUrl: whatsappUrl,
          ),
        ),
      );

      if (!mounted) return;
      if (checkedOut == true) {
        Navigator.of(context).pop(true);
      } else {
        await _load();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) setState(() => _isMutating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final filteredProducts = _products.where((product) {
      if (_query.trim().isEmpty) return true;
      final name = product["name"]?.toString().toLowerCase() ?? "";
      return name.contains(_query.trim().toLowerCase());
    }).toList();

    final selectedCount = _products.where((product) {
      final id = product["id"]?.toString() ?? "";
      return id.isNotEmpty && _qtyOf(id) > 0;
    }).length;

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FB),
      appBar: AppBar(title: const Text("Checkout Products")),
      body: Padding(
        padding: const EdgeInsets.all(14),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
            ? Center(
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              )
            : Column(
                children: [
                  TextField(
                    onChanged: (value) => setState(() => _query = value),
                    decoration: InputDecoration(
                      hintText: "Search loaded products...",
                      prefixIcon: const Icon(Icons.search),
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.inventory_2_outlined,
                          color: Color(0xFF1D9BF0),
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            "$selectedCount products added for invoice",
                            style: const TextStyle(
                              color: Color(0xFF0F172A),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  Expanded(
                    child: ListView.separated(
                      itemCount: filteredProducts.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 10),
                      itemBuilder: (context, index) {
                        final product = filteredProducts[index];
                        final id = product["id"]?.toString() ?? "";
                        final image = product["image"]?.toString() ?? "";
                        final controller =
                            _qtyControllers[id] ??
                            TextEditingController(text: "");
                        final available =
                            int.tryParse("${product["quantity_count"] ?? 0}") ??
                            0;

                        return Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFFE2E8F0)),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(10),
                                child: image.isNotEmpty
                                    ? Image.network(
                                        image,
                                        width: 64,
                                        height: 64,
                                        fit: BoxFit.cover,
                                        errorBuilder:
                                            (context, error, stackTrace) =>
                                                Container(
                                                  width: 64,
                                                  height: 64,
                                                  color: const Color(
                                                    0xFFE2E8F0,
                                                  ),
                                                  child: const Icon(
                                                    Icons.inventory_2_outlined,
                                                    size: 20,
                                                  ),
                                                ),
                                      )
                                    : Container(
                                        width: 64,
                                        height: 64,
                                        color: const Color(0xFFE2E8F0),
                                        child: const Icon(
                                          Icons.inventory_2_outlined,
                                          size: 20,
                                        ),
                                      ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      product["name"]?.toString() ?? "Product",
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 15,
                                        color: Color(0xFF0F172A),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      "Rate: Rs ${product["rate"]}",
                                      style: const TextStyle(
                                        color: Color(0xFF1D9BF0),
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      "Available in vehicle: $available",
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: Color(0xFF64748B),
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    SizedBox(
                                      width: 140,
                                      child: TextField(
                                        controller: controller,
                                        keyboardType: TextInputType.number,
                                        inputFormatters: [
                                          FilteringTextInputFormatter
                                              .digitsOnly,
                                        ],
                                        onChanged: (value) => _setQtyWithClamp(
                                          productId: id,
                                          maxAllowed: available,
                                          rawValue: value,
                                        ),
                                        decoration: InputDecoration(
                                          labelText: "Quantity",
                                          hintText: "0 - $available",
                                          isDense: true,
                                          border: OutlineInputBorder(
                                            borderRadius: BorderRadius.circular(
                                              10,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _isMutating
                          ? null
                          : _completeOrderAndOpenInvoice,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        backgroundColor: const Color(0xFF1D9BF0),
                        foregroundColor: Colors.white,
                      ),
                      child: Text(
                        _isMutating ? "Creating..." : "Create Invoice",
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
