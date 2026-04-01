import "package:flutter/material.dart";
import "package:url_launcher/url_launcher.dart";

import "../../auth/domain/auth_session.dart";
import "../data/driver_api.dart";
import "driver_stop_checkout_page.dart";

class DriverShopStopPage extends StatefulWidget {
  const DriverShopStopPage({
    super.key,
    required this.session,
    required this.assignmentId,
    required this.shopId,
  });

  final AuthSession session;
  final String assignmentId;
  final String shopId;

  @override
  State<DriverShopStopPage> createState() => _DriverShopStopPageState();
}

class _DriverShopStopPageState extends State<DriverShopStopPage> {
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
      final stop =
          (payload["stop"] as Map?)?.cast<String, dynamic>() ??
          <String, dynamic>{};
      if (!mounted) return;
      setState(() => _stopData = stop);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _openNavigation() async {
    final lat = _stopData["latitude"]?.toString() ?? "";
    final lng = _stopData["longitude"]?.toString() ?? "";
    if (lat.isEmpty || lng.isEmpty) return;
    final uri = Uri.parse(
      "https://www.google.com/maps/dir/?api=1&destination=$lat,$lng&travelmode=driving",
    );
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _callOwner() async {
    final phone = (_stopData["owner_mobile_number"]?.toString() ?? "").trim();
    if (phone.isEmpty) return;
    final digits = phone.replaceAll(RegExp(r"[^0-9+]"), "");
    final uri = Uri.parse("tel:$digits");
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _openCheckoutPage() async {
    if (!mounted) return;
    final checkedOut = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => DriverStopCheckoutPage(
          session: widget.session,
          assignmentId: widget.assignmentId,
          shopId: widget.shopId,
        ),
      ),
    );
    if (!mounted) return;
    if (checkedOut == true) {
      Navigator.of(context).pop(true);
      return;
    }
    await _load();
  }

  Future<void> _checkIn() async {
    if (_isMutating) return;
    setState(() => _isMutating = true);
    try {
      final response = await _driverApi.checkInStop(
        session: widget.session,
        assignmentId: widget.assignmentId,
        shopId: widget.shopId,
      );
      if (!mounted) return;
      if (response["queued_offline"] == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              "No internet. Check-in saved offline and will sync automatically.",
            ),
          ),
        );
      }
      setState(() => _isMutating = false);
      await _openCheckoutPage();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
      setState(() => _isMutating = false);
    }
  }

  Future<void> _handleCheckInTap() async {
    final stopStatus = _stopData["status"]?.toString() ?? "PENDING";
    if (stopStatus == "COMPLETED") return;
    if (stopStatus == "CHECKED_IN") {
      await _openCheckoutPage();
      return;
    }
    await _checkIn();
  }

  Future<void> _skipToNextStop() async {
    final controller = TextEditingController();
    String? validationError;

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            return AlertDialog(
              title: const Text("Proceed to Next Shop"),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Enter reason for skipping this shop."),
                  const SizedBox(height: 10),
                  TextField(
                    controller: controller,
                    maxLines: 3,
                    decoration: InputDecoration(
                      hintText: "Reason",
                      errorText: validationError,
                      border: const OutlineInputBorder(),
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  child: const Text("Cancel"),
                ),
                ElevatedButton(
                  onPressed: () {
                    if (controller.text.trim().isEmpty) {
                      setLocalState(
                        () => validationError = "Reason is required.",
                      );
                      return;
                    }
                    Navigator.of(context).pop(true);
                  },
                  child: const Text("Submit"),
                ),
              ],
            );
          },
        );
      },
    );

    if (confirmed != true || !mounted) return;

    setState(() => _isMutating = true);
    try {
      final response = await _driverApi.skipStop(
        session: widget.session,
        assignmentId: widget.assignmentId,
        shopId: widget.shopId,
        reason: controller.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            response["queued_offline"] == true
                ? "No internet. Skip saved offline and will sync automatically."
                : "Shop skipped. Moving to next stop.",
          ),
        ),
      );
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) setState(() => _isMutating = false);
    }
  }

  String _displayAddress() {
    final locationDisplay =
        (_stopData["location_display_name"]?.toString() ?? "").trim();
    final address = (_stopData["address"]?.toString() ?? "").trim();
    if (locationDisplay.isNotEmpty) return locationDisplay;
    if (address.isNotEmpty) return address;
    return "-";
  }

  @override
  Widget build(BuildContext context) {
    final stopStatus = _stopData["status"]?.toString() ?? "PENDING";
    final isCheckedIn = stopStatus == "CHECKED_IN";
    final isCompleted = stopStatus == "COMPLETED";
    final imageUrl = (_stopData["shop_image"]?.toString() ?? "").trim();
    final shopName = _stopData["shop_name"]?.toString() ?? "Shop";
    final ownerName = _stopData["owner_name"]?.toString() ?? "-";
    final ownerMobile = _stopData["owner_mobile_number"]?.toString() ?? "-";
    final addressText = _displayAddress();

    return Scaffold(
      backgroundColor: const Color(0xFFF3F5F9),
      appBar: AppBar(title: const Text("Shop Details"), centerTitle: true),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            )
          : Column(
              children: [
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                    children: [
                      Text(
                        shopName,
                        style: const TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 10),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: imageUrl.isNotEmpty
                            ? AspectRatio(
                                aspectRatio: 16 / 9,
                                child: Image.network(
                                  imageUrl,
                                  fit: BoxFit.cover,
                                  errorBuilder: (context, error, stackTrace) =>
                                      Container(
                                        color: const Color(0xFFE2E8F0),
                                        alignment: Alignment.center,
                                        child: const Icon(
                                          Icons.storefront_outlined,
                                          color: Color(0xFF64748B),
                                          size: 42,
                                        ),
                                      ),
                                ),
                              )
                            : Container(
                                height: 190,
                                color: const Color(0xFFE2E8F0),
                                alignment: Alignment.center,
                                child: const Icon(
                                  Icons.storefront_outlined,
                                  color: Color(0xFF64748B),
                                  size: 42,
                                ),
                              ),
                      ),
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "Stop #${_stopData["position"] ?? "-"}",
                              style: const TextStyle(
                                color: Color(0xFF1D9BF0),
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              "Address",
                              style: TextStyle(
                                fontWeight: FontWeight.w700,
                                color: Color(0xFF64748B),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              addressText,
                              style: const TextStyle(
                                fontSize: 16,
                                color: Color(0xFF0F172A),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            if ((_stopData["landmark"]?.toString() ?? "")
                                .isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text(
                                "Landmark: ${_stopData["landmark"]}",
                                style: const TextStyle(
                                  fontSize: 14,
                                  color: Color(0xFF64748B),
                                ),
                              ),
                            ],
                            const SizedBox(height: 10),
                            Text(
                              "Owner: $ownerName",
                              style: const TextStyle(
                                fontSize: 14,
                                color: Color(0xFF475569),
                              ),
                            ),
                            Text(
                              "Mobile: $ownerMobile",
                              style: const TextStyle(
                                fontSize: 14,
                                color: Color(0xFF475569),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: _openNavigation,
                              icon: const Icon(Icons.navigation_outlined),
                              label: const Text("Navigate"),
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                  vertical: 14,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: _callOwner,
                              icon: const Icon(Icons.call_outlined),
                              label: const Text("Call Owner"),
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                  vertical: 14,
                                ),
                                backgroundColor: const Color(0xFF1D9BF0),
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: (_isMutating || isCompleted)
                              ? null
                              : _handleCheckInTap,
                          icon: const Icon(Icons.pin_drop_outlined),
                          label: Text(
                            isCompleted
                                ? "Checked Out"
                                : (isCheckedIn
                                      ? "Continue to Checkout"
                                      : "Check In"),
                          ),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            backgroundColor: const Color(0xFF1D9BF0),
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: (_isMutating || isCheckedIn || isCompleted)
                              ? null
                              : _skipToNextStop,
                          icon: const Icon(Icons.skip_next_outlined),
                          label: const Text("Skip"),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            backgroundColor: const Color(0xFF1D9BF0),
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
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
  }
}
