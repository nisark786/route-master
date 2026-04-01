import "package:flutter/material.dart";
import "package:intl/intl.dart";

import "../../auth/domain/auth_session.dart";
import "../data/driver_api.dart";
import "../data/location_tracking_service.dart";
import "driver_shop_stop_page.dart";

class DriverStopsPage extends StatefulWidget {
  const DriverStopsPage({
    super.key,
    required this.session,
    required this.assignmentId,
  });

  final AuthSession session;
  final String assignmentId;

  @override
  State<DriverStopsPage> createState() => _DriverStopsPageState();
}

class _DriverStopsPageState extends State<DriverStopsPage> {
  final _driverApi = DriverApi();
  bool _isLoading = true;
  String? _error;
  Map<String, dynamic> _run = const {};
  List<Map<String, dynamic>> _stops = const [];

  @override
  void initState() {
    super.initState();
    LocationTrackingService.instance.start(
      session: widget.session,
      assignmentId: widget.assignmentId,
    );
    _load();
  }

  @override
  void dispose() {
    LocationTrackingService.instance.stop(assignmentId: widget.assignmentId);
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final run = await _driverApi.getAssignmentDetail(
        session: widget.session,
        assignmentId: widget.assignmentId,
      );
      final stops = (run["stops"] as List? ?? const [])
          .whereType<Map>()
          .map((item) => item.cast<String, dynamic>())
          .toList();
      if (!mounted) return;
      setState(() {
        _run = run;
        _stops = stops;
      });
      if ((run["status"]?.toString() ?? "") == "COMPLETED") {
        LocationTrackingService.instance.stop(assignmentId: widget.assignmentId);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _openStop(Map<String, dynamic> stop) async {
    final shopId = stop["shop_id"]?.toString() ?? "";
    if (shopId.isEmpty) return;
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => DriverShopStopPage(
          session: widget.session,
          assignmentId: widget.assignmentId,
          shopId: shopId,
        ),
      ),
    );
    await _load();
  }

  String _routeCode() {
    final raw = widget.assignmentId.replaceAll("-", "");
    if (raw.length >= 3) return "RT-${raw.substring(0, 3).toUpperCase()}";
    return "ROUTE";
  }

  String _subtitleText(Map<String, dynamic> stop) {
    final checkInAt = DateTime.tryParse(stop["check_in_at"]?.toString() ?? "");
    final checkOutAt = DateTime.tryParse(stop["check_out_at"]?.toString() ?? "");
    final status = stop["status"]?.toString() ?? "PENDING";

    if (status == "COMPLETED" && checkOutAt != null) {
      return "Completed ${DateFormat("hh:mm a").format(checkOutAt.toLocal())}";
    }
    if (status == "CHECKED_IN" && checkInAt != null) {
      return "Checked in ${DateFormat("hh:mm a").format(checkInAt.toLocal())}";
    }
    return "Next stop";
  }

  Color _statusAccent(Map<String, dynamic> stop, String nextPendingStopId) {
    final stopId = stop["id"]?.toString() ?? "";
    final status = stop["status"]?.toString() ?? "PENDING";

    if (status == "COMPLETED") return const Color(0xFF94A3B8);
    if (status == "CHECKED_IN") return const Color(0xFF1D9BF0);
    if (stopId == nextPendingStopId) return const Color(0xFF1D9BF0);
    return const Color(0xFFE2E8F0);
  }

  Color _cardBackground(Map<String, dynamic> stop, String nextPendingStopId) {
    final stopId = stop["id"]?.toString() ?? "";
    final status = stop["status"]?.toString() ?? "PENDING";
    if (status == "CHECKED_IN" || stopId == nextPendingStopId) {
      return const Color(0xFFEFF6FF);
    }
    return Colors.white;
  }

  @override
  Widget build(BuildContext context) {
    final progress = (_run["progress"] as Map?)?.cast<String, dynamic>() ?? const {};
    final completed = progress["completed_stops"] ?? 0;
    final total = progress["total_stops"] ?? _stops.length;
    final nextPendingStopId = _run["next_pending_stop_id"]?.toString() ?? "";

    return Scaffold(
      backgroundColor: const Color(0xFFF3F5F9),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF3F5F9),
        elevation: 0,
        title: Text(
          "ROUTE ${_routeCode()}",
          style: const TextStyle(
            color: Color(0xFF475569),
            fontWeight: FontWeight.w800,
            fontSize: 14,
            letterSpacing: 0.6,
          ),
        ),
        centerTitle: true,
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 16),
          children: [
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.only(top: 80),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF2F2),
                  border: Border.all(color: const Color(0xFFFECACA)),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _error!,
                  style: const TextStyle(
                    color: Color(0xFFB91C1C),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              )
            else ...[
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            "DAILY PROGRESS",
                            style: TextStyle(
                              color: Colors.blueGrey.shade400,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.6,
                            ),
                          ),
                          const SizedBox(height: 6),
                          RichText(
                            text: TextSpan(
                              style: const TextStyle(color: Color(0xFF0F172A)),
                              children: [
                                TextSpan(
                                  text: "$completed/$total ",
                                  style: const TextStyle(
                                    fontSize: 36,
                                    fontWeight: FontWeight.w900,
                                    height: 0.95,
                                  ),
                                ),
                                const TextSpan(
                                  text: "Stops Finished",
                                  style: TextStyle(
                                    color: Color(0xFF64748B),
                                    fontWeight: FontWeight.w600,
                                    fontSize: 14,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.inventory_2_outlined, color: Color(0xFF1D9BF0), size: 28),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Text(
                "DELIVERY SCHEDULE",
                style: TextStyle(
                  color: Colors.blueGrey.shade400,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.7,
                ),
              ),
              const SizedBox(height: 10),
              ..._stops.map((stop) {
                final accent = _statusAccent(stop, nextPendingStopId);
                final cardBg = _cardBackground(stop, nextPendingStopId);
                final isCurrent = (stop["id"]?.toString() ?? "") == nextPendingStopId;
                final title = stop["shop_name"]?.toString() ?? "-";
                final address = stop["address"]?.toString().trim().isNotEmpty == true
                    ? stop["address"].toString()
                    : (stop["location_display_name"]?.toString() ?? "-");

                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 28,
                        child: Column(
                          children: [
                            Container(
                              width: 22,
                              height: 22,
                              decoration: BoxDecoration(
                                color: accent,
                                shape: BoxShape.circle,
                                border: Border.all(color: Colors.white, width: 2),
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                "${stop["position"] ?? "-"}",
                                style: TextStyle(
                                  color: accent == const Color(0xFFE2E8F0)
                                      ? const Color(0xFF64748B)
                                      : Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 10,
                                ),
                              ),
                            ),
                            Container(width: 1, height: 58, color: const Color(0xFFE2E8F0)),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: cardBg,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isCurrent ? const Color(0xFFBFDBFE) : const Color(0xFFE2E8F0),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      title,
                                      style: TextStyle(
                                        color: isCurrent ? const Color(0xFF1D9BF0) : const Color(0xFF1E293B),
                                        fontWeight: FontWeight.w800,
                                        fontSize: 21,
                                      ),
                                    ),
                                  ),
                                  if (isCurrent)
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF1D9BF0),
                                        borderRadius: BorderRadius.circular(999),
                                      ),
                                      child: const Text(
                                        "CURRENT",
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 10,
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                address,
                                style: const TextStyle(
                                  color: Color(0xFF64748B),
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              const SizedBox(height: 10),
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      _subtitleText(stop),
                                      style: const TextStyle(
                                        color: Color(0xFF64748B),
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                  SizedBox(
                                    height: 34,
                                    child: ElevatedButton(
                                      onPressed: () => _openStop(stop),
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: const Color(0xFF1D9BF0),
                                        foregroundColor: Colors.white,
                                        padding: const EdgeInsets.symmetric(horizontal: 16),
                                        textStyle: const TextStyle(fontWeight: FontWeight.w700),
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                      ),
                                      child: const Text("Go"),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}
