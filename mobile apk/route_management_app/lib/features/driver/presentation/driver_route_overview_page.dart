import "package:flutter/material.dart";

import "../../auth/domain/auth_session.dart";
import "../data/driver_api.dart";
import "driver_stops_page.dart";

class DriverRouteOverviewPage extends StatefulWidget {
  const DriverRouteOverviewPage({
    super.key,
    required this.session,
    required this.assignmentId,
  });

  final AuthSession session;
  final String assignmentId;

  @override
  State<DriverRouteOverviewPage> createState() => _DriverRouteOverviewPageState();
}

class _DriverRouteOverviewPageState extends State<DriverRouteOverviewPage> {
  final _driverApi = DriverApi();
  bool _isLoading = true;
  String? _error;
  Map<String, dynamic> _run = const {};

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
      final run = await _driverApi.getAssignmentDetail(
        session: widget.session,
        assignmentId: widget.assignmentId,
      );
      if (!mounted) return;
      setState(() => _run = run);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _goToStops() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => DriverStopsPage(
          session: widget.session,
          assignmentId: widget.assignmentId,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Scaffold(
        appBar: AppBar(title: const Text("Route Details"), automaticallyImplyLeading: false),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _run["route_name"]?.toString() ?? "Route",
                                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                                ),
                                const SizedBox(height: 8),
                                Text("Start: ${_run["start_point"] ?? "-"}"),
                                Text("End: ${_run["end_point"] ?? "-"}"),
                                const Divider(height: 20),
                                Text("Vehicle: ${_run["vehicle_name"] ?? "-"}"),
                                Text("Number Plate: ${_run["vehicle_number_plate"] ?? "-"}"),
                                Text("Fuel: ${_run["fuel_percentage"] ?? 0}%"),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _goToStops,
                            child: const Text("Continue"),
                          ),
                        ),
                      ],
                    ),
        ),
      ),
    );
  }
}
