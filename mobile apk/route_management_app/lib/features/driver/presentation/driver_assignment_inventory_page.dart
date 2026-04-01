import "package:flutter/material.dart";
import "package:flutter/services.dart";

import "../../auth/domain/auth_session.dart";
import "../data/driver_api.dart";

class DriverAssignmentInventoryPage extends StatefulWidget {
  const DriverAssignmentInventoryPage({
    super.key,
    required this.session,
    required this.assignmentId,
    required this.routeName,
  });

  final AuthSession session;
  final String assignmentId;
  final String routeName;

  @override
  State<DriverAssignmentInventoryPage> createState() =>
      _DriverAssignmentInventoryPageState();
}

class _DriverAssignmentInventoryPageState
    extends State<DriverAssignmentInventoryPage> {
  final DriverApi _driverApi = DriverApi();
  bool _isLoading = true;
  bool _isSaving = false;
  bool _loadedFromCache = false;
  String? _error;
  String _searchQuery = "";
  List<Map<String, dynamic>> _products = const [];
  final Map<String, int> _selectedQtyByProductId = {};
  final Map<String, TextEditingController> _qtyControllers = {};

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
      final payload = await _driverApi.getAssignmentInventory(
        session: widget.session,
        assignmentId: widget.assignmentId,
      );
      _applyPayload(payload);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _applyPayload(Map<String, dynamic> payload) {
    final products = (payload["products"] as List? ?? const [])
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
    final selected = <String, int>{};
    for (final product in products) {
      final productId = product["id"]?.toString() ?? "";
      if (productId.isEmpty) continue;
      final loaded = int.tryParse("${product["loaded_quantity"] ?? 0}") ?? 0;
      if (loaded > 0) {
        selected[productId] = loaded;
      }
    }
    if (!mounted) return;
    setState(() {
      _products = products;
      _selectedQtyByProductId
        ..clear()
        ..addAll(selected);
      _loadedFromCache = payload["from_cache"] == true;
    });
    _syncControllers();
  }

  void _syncControllers() {
    final activeIds = _products
        .map((product) => product["id"]?.toString() ?? "")
        .where((id) => id.isNotEmpty)
        .toSet();

    _qtyControllers.removeWhere((productId, controller) {
      if (activeIds.contains(productId)) return false;
      controller.dispose();
      return true;
    });

    for (final product in _products) {
      final productId = product["id"]?.toString() ?? "";
      if (productId.isEmpty) continue;
      final selected = _selectedQtyByProductId[productId] ?? 0;
      final text = selected > 0 ? selected.toString() : "";
      final controller = _qtyControllers.putIfAbsent(
        productId,
        () => TextEditingController(text: text),
      );
      if (controller.text != text) {
        controller.value = TextEditingValue(
          text: text,
          selection: TextSelection.collapsed(offset: text.length),
        );
      }
    }
  }

  void _setQty(String productId, int nextQty, int maxAllowed) {
    final clamped = nextQty < 0
        ? 0
        : (nextQty > maxAllowed ? maxAllowed : nextQty);
    setState(() {
      if (clamped == 0) {
        _selectedQtyByProductId.remove(productId);
      } else {
        _selectedQtyByProductId[productId] = clamped;
      }
    });
    final text = clamped > 0 ? clamped.toString() : "";
    final controller = _qtyControllers[productId];
    if (controller != null && controller.text != text) {
      controller.value = TextEditingValue(
        text: text,
        selection: TextSelection.collapsed(offset: text.length),
      );
    }
  }

  void _onQtyChanged({
    required String productId,
    required String value,
    required int available,
  }) {
    final currentLoaded = _selectedQtyByProductId[productId] ?? 0;
    final maxAllowed = available + currentLoaded;
    final parsed = int.tryParse(value.trim()) ?? 0;
    if (parsed > maxAllowed) {
      _setQty(productId, maxAllowed, maxAllowed);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Cannot exceed available quantity ($maxAllowed)."),
        ),
      );
      return;
    }
    _setQty(productId, parsed, maxAllowed);
  }

  Future<void> _finish() async {
    if (_isSaving) return;
    final items = _selectedQtyByProductId.entries
        .where((entry) => entry.value > 0)
        .map((entry) => {"product_id": entry.key, "quantity": entry.value})
        .toList();

    setState(() => _isSaving = true);
    try {
      final payload = await _driverApi.saveAssignmentInventory(
        session: widget.session,
        assignmentId: widget.assignmentId,
        items: items,
      );
      if (!mounted) return;
      final queued = payload["queued_offline"] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            queued
                ? "No internet. Inventory saved offline and will sync automatically."
                : "Inventory saved successfully.",
          ),
        ),
      );
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final filteredProducts = _products.where((product) {
      final name = product["name"]?.toString().toLowerCase() ?? "";
      return name.contains(_searchQuery.toLowerCase());
    }).toList();

    return Scaffold(
      appBar: AppBar(title: Text("Load Inventory - ${widget.routeName}")),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  _error!,
                  style: const TextStyle(
                    color: Color(0xFFB91C1C),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            )
          : Column(
              children: [
                if (_loadedFromCache)
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF3C7),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFFFCD34D)),
                    ),
                    child: const Text(
                      "Offline mode: using cached data. Changes will auto-sync when internet returns.",
                      style: TextStyle(
                        color: Color(0xFF92400E),
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                  ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                  child: TextField(
                    onChanged: (value) => setState(() => _searchQuery = value),
                    decoration: InputDecoration(
                      hintText: "Search products...",
                      prefixIcon: const Icon(Icons.search_rounded),
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
                ),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                    itemCount: filteredProducts.length,
                    itemBuilder: (context, index) {
                      final product = filteredProducts[index];
                      final productId = product["id"]?.toString() ?? "";
                      if (productId.isEmpty) return const SizedBox.shrink();

                      final name = product["name"]?.toString() ?? "Product";
                      final available =
                          int.tryParse("${product["quantity_count"] ?? 0}") ??
                          0;
                      final selected = _selectedQtyByProductId[productId] ?? 0;
                      final maxAllowed = available + selected;
                      final rate = product["rate"]?.toString() ?? "-";
                      final imageUrl = product["image"]?.toString() ?? "";
                      final qtyController = _qtyControllers.putIfAbsent(
                        productId,
                        () => TextEditingController(
                          text: selected > 0 ? selected.toString() : "",
                        ),
                      );

                      return Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Row(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: imageUrl.isEmpty
                                  ? Container(
                                      width: 56,
                                      height: 56,
                                      color: const Color(0xFFF1F5F9),
                                      child: const Icon(
                                        Icons.inventory_2_outlined,
                                        color: Color(0xFF64748B),
                                      ),
                                    )
                                  : Image.network(
                                      imageUrl,
                                      width: 56,
                                      height: 56,
                                      fit: BoxFit.cover,
                                      errorBuilder:
                                          (context, error, stackTrace) =>
                                              Container(
                                                width: 56,
                                                height: 56,
                                                color: const Color(0xFFF1F5F9),
                                                child: const Icon(
                                                  Icons.inventory_2_outlined,
                                                  color: Color(0xFF64748B),
                                                ),
                                              ),
                                    ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    name,
                                    style: const TextStyle(
                                      color: Color(0xFF0F172A),
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    "Available: $available  |  Rate: Rs $rate",
                                    style: const TextStyle(
                                      color: Color(0xFF64748B),
                                      fontWeight: FontWeight.w600,
                                      fontSize: 12,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Row(
                                    children: [
                                      const Text(
                                        "Load qty",
                                        style: TextStyle(
                                          color: Color(0xFF475569),
                                          fontWeight: FontWeight.w700,
                                          fontSize: 12,
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      SizedBox(
                                        width: 120,
                                        child: TextField(
                                          controller: qtyController,
                                          enabled: !_isSaving,
                                          keyboardType: TextInputType.number,
                                          inputFormatters: [
                                            FilteringTextInputFormatter
                                                .digitsOnly,
                                          ],
                                          onChanged: (value) => _onQtyChanged(
                                            productId: productId,
                                            value: value,
                                            available: available,
                                          ),
                                          decoration: InputDecoration(
                                            hintText: "0 - $maxAllowed",
                                            isDense: true,
                                            contentPadding:
                                                const EdgeInsets.symmetric(
                                                  horizontal: 10,
                                                  vertical: 10,
                                                ),
                                            border: OutlineInputBorder(
                                              borderRadius:
                                                  BorderRadius.circular(8),
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
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
                Container(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
                  ),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _isSaving ? null : _finish,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1D9BF0),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      child: Text(_isSaving ? "Saving..." : "Finish"),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
