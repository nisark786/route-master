import "package:flutter/material.dart";
import "package:intl/intl.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:url_launcher/url_launcher.dart";

import "../../../core/notifications/push_notification_service.dart";
import "../../../core/storage/auth_storage.dart";
import "../../auth/data/auth_api.dart";
import "../../auth/domain/auth_session.dart";
import "../../auth/presentation/login_page.dart";
import "../data/driver_api.dart";
import "../data/driver_chat_api.dart";
import "../data/driver_chat_sync_service.dart";
import "../data/driver_sync_service.dart";
import "driver_assignment_inventory_page.dart";
import "driver_chat_page.dart";
import "driver_stops_page.dart";

class DriverHomePage extends StatefulWidget {
  const DriverHomePage({super.key, required this.session});

  final AuthSession session;

  @override
  State<DriverHomePage> createState() => _DriverHomePageState();
}

class _DriverHomePageState extends State<DriverHomePage> {
  final _driverApi = DriverApi();
  bool _isLoading = true;
  String? _startingAssignmentId;
  String? _loadingInventoryAssignmentId;
  String? _error;
  List<Map<String, dynamic>> _assignments = const [];
  DateTime? _lastUpdatedAt;
  int _queueTabIndex = 0;

  @override
  void initState() {
    super.initState();
    _loadAssignments();
  }

  Future<void> _loadAssignments() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final data = await _driverApi.listAssignments(widget.session);
      if (!mounted) return;
      setState(() {
        _assignments = data;
        _lastUpdatedAt = DateTime.now();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _startAssignment(Map<String, dynamic> assignment) async {
    final assignmentId = assignment["id"]?.toString() ?? "";
    if (assignmentId.isEmpty) return;

    try {
      setState(() => _startingAssignmentId = assignmentId);
      final response = await _driverApi.startAssignment(
        session: widget.session,
        assignmentId: assignmentId,
      );
      if (!mounted) return;
      if (response["queued_offline"] == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              "No internet. Start saved offline and will sync automatically.",
            ),
          ),
        );
      }
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => DriverStopsPage(
            session: widget.session,
            assignmentId: assignmentId,
          ),
        ),
      );
      await _loadAssignments();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) setState(() => _startingAssignmentId = null);
    }
  }

  Future<void> _openInventory(Map<String, dynamic> assignment) async {
    final assignmentId = assignment["id"]?.toString() ?? "";
    if (assignmentId.isEmpty) return;
    try {
      setState(() => _loadingInventoryAssignmentId = assignmentId);
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => DriverAssignmentInventoryPage(
            session: widget.session,
            assignmentId: assignmentId,
            routeName: assignment["route_name"]?.toString() ?? "Route",
          ),
        ),
      );
      await _loadAssignments();
    } finally {
      if (mounted) setState(() => _loadingInventoryAssignmentId = null);
    }
  }

  bool _isScheduledForToday(Map<String, dynamic> assignment) {
    final scheduledAtRaw = assignment["scheduled_at"]?.toString() ?? "";
    final scheduledAt = DateTime.tryParse(scheduledAtRaw)?.toLocal();
    if (scheduledAt == null) return false;
    final now = DateTime.now();
    return scheduledAt.year == now.year &&
        scheduledAt.month == now.month &&
        scheduledAt.day == now.day;
  }

  Widget _buildAssignmentCard(Map<String, dynamic> assignment, int index) {
    final status = assignment["status"]?.toString() ?? "PENDING";
    final scheduledAt = DateTime.tryParse(
      assignment["scheduled_at"]?.toString() ?? "",
    );
    final localScheduledAt = scheduledAt?.toLocal();
    final scheduleText = localScheduledAt == null
        ? "-"
        : DateFormat("hh:mm a").format(localScheduledAt);
    final scheduleDateText = localScheduledAt == null
        ? "-"
        : DateFormat("dd MMM yyyy").format(localScheduledAt);
    final routeName = assignment["route_name"]?.toString() ?? "Route";
    final startPoint = assignment["start_point"]?.toString() ?? "-";
    final endPoint = assignment["end_point"]?.toString() ?? "-";
    final shops = assignment["shops_count"]?.toString() ?? "0";
    final vehiclePlate = assignment["vehicle_number_plate"]?.toString() ?? "-";
    final canOpenRoute = status == "ASSIGNED" || status == "IN_ROUTE";
    final canManageInventory = status == "ASSIGNED" || status == "IN_ROUTE";
    final isActionBusy =
        _startingAssignmentId == (assignment["id"]?.toString() ?? "");
    final isInventoryBusy =
        _loadingInventoryAssignmentId == (assignment["id"]?.toString() ?? "");

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x110F172A),
            blurRadius: 16,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  routeName,
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            "$startPoint -> $endPoint",
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: Colors.blueGrey.shade50),
                bottom: BorderSide(color: Colors.blueGrey.shade50),
              ),
            ),
            child: Row(
              children: [
                _statCell(
                  icon: Icons.storefront_outlined,
                  value: shops,
                  label: "SHOPS",
                ),
                _dividerCell(),
                _statCell(
                  icon: Icons.access_time_outlined,
                  value: scheduleText,
                  label: "START",
                ),
                _dividerCell(),
                _statCell(
                  icon: Icons.directions_car_outlined,
                  value: vehiclePlate,
                  label: "VEHICLE",
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(
                Icons.event_outlined,
                size: 16,
                color: Color(0xFF1D9BF0),
              ),
              const SizedBox(width: 6),
              Text(
                "Scheduled: $scheduleDateText",
                style: const TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed:
                      canManageInventory && !isInventoryBusy && !isActionBusy
                      ? () => _openInventory(assignment)
                      : null,
                  icon: const Icon(Icons.inventory_2_outlined),
                  label: Text(isInventoryBusy ? "Opening..." : "Add Inventory"),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF1D4ED8),
                    side: const BorderSide(color: Color(0xFF93C5FD)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                    textStyle: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: canOpenRoute && !isActionBusy && !isInventoryBusy
                      ? () => _startAssignment(assignment)
                      : null,
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: Text(
                    isActionBusy
                        ? "Opening..."
                        : status == "ASSIGNED"
                        ? "Start"
                        : status == "IN_ROUTE"
                        ? "Continue"
                        : "Route Completed",
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1D9BF0),
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: const Color(0xFFE2E8F0),
                    disabledForegroundColor: const Color(0xFF64748B),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                    textStyle: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statCell({
    required IconData icon,
    required String value,
    required String label,
  }) {
    return Expanded(
      child: Column(
        children: [
          Icon(icon, size: 16, color: const Color(0xFF1D9BF0)),
          const SizedBox(height: 3),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Color(0xFF0F172A),
              fontWeight: FontWeight.w700,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontWeight: FontWeight.w600,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }

  Widget _dividerCell() {
    return Container(
      width: 1,
      height: 32,
      color: Colors.blueGrey.shade100,
      margin: const EdgeInsets.symmetric(horizontal: 8),
    );
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final todayAssignments = _assignments.where(_isScheduledForToday).toList();
    final upcomingAssignments = _assignments.where((item) {
      final dt = DateTime.tryParse(
        item["scheduled_at"]?.toString() ?? "",
      )?.toLocal();
      if (dt == null) return false;
      return dt.isAfter(now) && !_isScheduledForToday(item);
    }).toList();
    final queueItems = _queueTabIndex == 0
        ? todayAssignments
        : upcomingAssignments;

    return Scaffold(
      backgroundColor: const Color(0xFFF3F6FB),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadAssignments,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
            children: [
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      "MY ASSIGNED ROUTES",
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF475569),
                        letterSpacing: 0.6,
                        fontSize: 13,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: "Refresh",
                    onPressed: _isLoading ? null : _loadAssignments,
                    icon: const Icon(Icons.notifications_none_rounded),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _queueTabIndex == 0
                          ? "Queue for Today"
                          : "Upcoming Routes",
                      style: TextStyle(
                        color: Color(0xFF0F172A),
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _queueTab(
                      label: "Today",
                      active: _queueTabIndex == 0,
                      onTap: () => setState(() => _queueTabIndex = 0),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _queueTab(
                      label: "Upcoming",
                      active: _queueTabIndex == 1,
                      onTap: () => setState(() => _queueTabIndex = 1),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              if (_isLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 40),
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
              else if (queueItems.isEmpty)
                Container(
                  margin: const EdgeInsets.only(top: 24),
                  padding: const EdgeInsets.all(20),
                  alignment: Alignment.center,
                  child: const Column(
                    children: [
                      Icon(
                        Icons.event_busy_outlined,
                        color: Color(0xFF94A3B8),
                        size: 30,
                      ),
                      SizedBox(height: 10),
                      Text(
                        "No routes in this queue",
                        style: TextStyle(
                          color: Color(0xFF475569),
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        "Switch queue tab or pull to refresh.",
                        style: TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                )
              else
                ...queueItems.asMap().entries.map(
                  (entry) => _buildAssignmentCard(entry.value, entry.key),
                ),
              if (queueItems.isNotEmpty)
                const Padding(
                  padding: EdgeInsets.only(top: 24, bottom: 80),
                  child: Column(
                    children: [
                      Icon(
                        Icons.check_circle_outline,
                        color: Color(0xFF94A3B8),
                        size: 28,
                      ),
                      SizedBox(height: 8),
                      Text(
                        "No more routes for today",
                        style: TextStyle(
                          color: Color(0xFF475569),
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        "Switch tabs to check upcoming assignments.",
                        style: TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              if (_lastUpdatedAt != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Center(
                    child: Text(
                      "Last updated ${DateFormat("hh:mm a").format(_lastUpdatedAt!)}",
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: Container(
        height: 74,
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
        ),
        child: Row(
          children: [
            _bottomNavItem(
              icon: Icons.route_outlined,
              label: "Routes",
              active: true,
            ),
            _bottomNavItem(
              icon: Icons.chat_bubble_outline_rounded,
              label: "Chat",
              onTap: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => DriverChatPage(session: widget.session),
                  ),
                );
              },
            ),
            _bottomNavItem(
              icon: Icons.settings_outlined,
              label: "Settings",
              onTap: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) =>
                        _DriverSettingsPage(session: widget.session),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _queueTab({
    required String label,
    required bool active,
    required VoidCallback onTap,
  }) {
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: onTap,
      child: Container(
        height: 36,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: active ? const Color(0xFF1D9BF0) : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: active ? const Color(0xFF1D9BF0) : const Color(0xFFE2E8F0),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? Colors.white : const Color(0xFF475569),
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }

  Widget _bottomNavItem({
    required IconData icon,
    required String label,
    bool active = false,
    VoidCallback? onTap,
  }) {
    final activeColor = const Color(0xFF1D9BF0);
    final idleColor = const Color(0xFF64748B);
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: active ? activeColor : idleColor, size: 21),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                color: active ? activeColor : idleColor,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DriverSettingsPage extends StatefulWidget {
  const _DriverSettingsPage({required this.session});

  final AuthSession session;

  @override
  State<_DriverSettingsPage> createState() => _DriverSettingsPageState();
}

class _DriverSettingsPageState extends State<_DriverSettingsPage> {
  static const _prefChatNotifications = "settings.driver.chat_notifications";
  static const _prefRouteNotifications = "settings.driver.route_notifications";
  static const _prefSoundVibration = "settings.driver.sound_vibration";

  final _authApi = AuthApi();
  final _chatApi = DriverChatApi();
  bool _isLoadingProfile = true;
  bool _isUpdatingPassword = false;
  bool _chatNotificationsEnabled = true;
  bool _routeNotificationsEnabled = true;
  bool _soundVibrationEnabled = true;
  String? _profileError;
  Map<String, dynamic> _profile = const {};

  @override
  void initState() {
    super.initState();
    _loadPreferences();
    _loadProfile();
  }

  Future<void> _loadPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _chatNotificationsEnabled = prefs.getBool(_prefChatNotifications) ?? true;
      _routeNotificationsEnabled =
          prefs.getBool(_prefRouteNotifications) ?? true;
      _soundVibrationEnabled = prefs.getBool(_prefSoundVibration) ?? true;
    });
  }

  Future<void> _saveBoolPref(String key, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, value);
  }

  Future<void> _loadProfile() async {
    setState(() {
      _isLoadingProfile = true;
      _profileError = null;
    });
    try {
      final data = await _authApi.getMe(widget.session.accessToken);
      if (!mounted) return;
      setState(() => _profile = data);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _profileError = e.toString().replaceFirst("Exception: ", "");
      });
    } finally {
      if (mounted) {
        setState(() => _isLoadingProfile = false);
      }
    }
  }

  String _roleLabel() {
    final roleRaw = (_profile["role"]?.toString() ?? "").toUpperCase();
    if (roleRaw == "DRIVER") return "Driver";
    if (roleRaw == "SHOP_OWNER") return "Shop Owner";
    if (widget.session.role == UserRole.driver) return "Driver";
    if (widget.session.role == UserRole.shopOwner) return "Shop Owner";
    return "-";
  }

  String _mobileLabel() {
    final value = (_profile["mobile_number"]?.toString() ?? "").trim();
    return value.isEmpty ? "-" : value;
  }

  String _driverNameLabel() {
    final value = (_profile["driver_name"]?.toString() ?? "").trim();
    if (value.isNotEmpty) return value;
    if (widget.session.role == UserRole.driver) return "Driver";
    return "-";
  }

  String _roleDisplayLabel() {
    if (widget.session.role == UserRole.driver) return "Driver";
    if (widget.session.role == UserRole.shopOwner) return "Shop Owner";
    return _roleLabel();
  }

  String _companyLabel() {
    final fromProfile = (_profile["company_name"]?.toString() ?? "").trim();
    if (fromProfile.isNotEmpty) return fromProfile;
    final value = (widget.session.companyId ?? "").trim();
    return value.isEmpty ? "-" : value;
  }

  Future<void> _toggleChatNotifications(bool value) async {
    setState(() => _chatNotificationsEnabled = value);
    await _saveBoolPref(_prefChatNotifications, value);
    try {
      final token = await PushNotificationService.instance.getSavedToken();
      if (token == null || token.isEmpty) return;
      if (value) {
        await _chatApi.registerPushToken(session: widget.session, token: token);
      } else {
        await _chatApi.unregisterPushToken(
          session: widget.session,
          token: token,
        );
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Notification preference saved locally.")),
      );
    }
  }

  Future<void> _toggleRouteNotifications(bool value) async {
    setState(() => _routeNotificationsEnabled = value);
    await _saveBoolPref(_prefRouteNotifications, value);
  }

  Future<void> _toggleSoundVibration(bool value) async {
    setState(() => _soundVibrationEnabled = value);
    await _saveBoolPref(_prefSoundVibration, value);
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _changePassword() async {
    final currentController = TextEditingController();
    final newController = TextEditingController();
    final confirmController = TextEditingController();
    String? dialogError;

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            return AlertDialog(
              title: const Text("Change Password"),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: currentController,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: "Current password",
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: newController,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: "New password",
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: confirmController,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: "Confirm new password",
                    ),
                  ),
                  if (dialogError != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      dialogError!,
                      style: const TextStyle(
                        color: Color(0xFFB91C1C),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(false),
                  child: const Text("Cancel"),
                ),
                FilledButton(
                  onPressed: () {
                    final current = currentController.text.trim();
                    final next = newController.text.trim();
                    final confirm = confirmController.text.trim();
                    if (current.isEmpty || next.isEmpty || confirm.isEmpty) {
                      setLocalState(
                        () => dialogError = "All fields are required.",
                      );
                      return;
                    }
                    if (next.length < 8) {
                      setLocalState(
                        () => dialogError =
                            "New password must be at least 8 characters.",
                      );
                      return;
                    }
                    if (next != confirm) {
                      setLocalState(
                        () => dialogError =
                            "New password and confirm password do not match.",
                      );
                      return;
                    }
                    Navigator.of(dialogContext).pop(true);
                  },
                  child: const Text("Update"),
                ),
              ],
            );
          },
        );
      },
    );
    if (confirmed != true) return;

    setState(() => _isUpdatingPassword = true);
    try {
      await _authApi.changePassword(
        accessToken: widget.session.accessToken,
        currentPassword: currentController.text.trim(),
        newPassword: newController.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Password updated successfully.")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) {
        setState(() => _isUpdatingPassword = false);
      }
    }
  }

  Future<void> _logout(BuildContext context) async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text("Confirm Logout"),
          content: const Text(
            "Are you sure you want to logout from this device?",
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text("Cancel"),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text("OK"),
            ),
          ],
        );
      },
    );
    if (shouldLogout != true) return;

    try {
      final token = await PushNotificationService.instance.getSavedToken();
      if (token != null && token.isNotEmpty) {
        await _chatApi.unregisterPushToken(
          session: widget.session,
          token: token,
        );
      }
    } catch (_) {
      // Best effort. Logout should continue even if unregister fails.
    }

    await AuthStorage.clearSession();
    DriverSyncService.instance.stop();
    DriverChatSyncService.instance.stop();
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginPage()),
      (route) => false,
    );
  }

  Widget _sectionCard({required String title, required Widget child}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  Widget _profileRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(
            width: 92,
            child: Text(
              label,
              style: const TextStyle(
                color: Color(0xFF64748B),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: Color(0xFF0F172A),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F6FB),
      appBar: AppBar(title: const Text("Settings")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionCard(
            title: "Profile",
            child: _isLoadingProfile
                ? const Center(child: CircularProgressIndicator())
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (_profileError != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Text(
                            _profileError!,
                            style: const TextStyle(
                              color: Color(0xFFB91C1C),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      _profileRow("Role", _roleLabel()),
                      _profileRow("Name", _driverNameLabel()),
                      _profileRow("Role", _roleDisplayLabel()),
                      _profileRow("Mobile", _mobileLabel()),
                      _profileRow("Company", _companyLabel()),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton.icon(
                          onPressed: _loadProfile,
                          icon: const Icon(Icons.refresh_rounded, size: 18),
                          label: const Text("Refresh"),
                        ),
                      ),
                    ],
                  ),
          ),
          _sectionCard(
            title: "Notifications",
            child: Column(
              children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text("Chat notifications"),
                  subtitle: const Text(
                    "Receive message alerts on this device.",
                  ),
                  value: _chatNotificationsEnabled,
                  onChanged: _toggleChatNotifications,
                ),
                const Divider(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text("Route notifications"),
                  subtitle: const Text(
                    "Get assignment and route status alerts.",
                  ),
                  value: _routeNotificationsEnabled,
                  onChanged: _toggleRouteNotifications,
                ),
                const Divider(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text("Sound & vibration"),
                  subtitle: const Text(
                    "Use sound and vibration for notifications.",
                  ),
                  value: _soundVibrationEnabled,
                  onChanged: _toggleSoundVibration,
                ),
              ],
            ),
          ),
          _sectionCard(
            title: "Security",
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.lock_outline_rounded),
                  title: const Text("Change password"),
                  subtitle: const Text("Update your account password."),
                  trailing: _isUpdatingPassword
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.chevron_right_rounded),
                  onTap: _isUpdatingPassword ? null : _changePassword,
                ),
                const Divider(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(
                    Icons.logout_rounded,
                    color: Color(0xFFB91C1C),
                  ),
                  title: const Text(
                    "Logout",
                    style: TextStyle(
                      color: Color(0xFFB91C1C),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  subtitle: const Text("Sign out from this device."),
                  onTap: () => _logout(context),
                ),
              ],
            ),
          ),
          _sectionCard(
            title: "Help & Support",
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.support_agent_rounded),
                  title: const Text("Contact support"),
                  subtitle: const Text("support.routemaster@gmail.com"),
                  onTap: () => _openUrl("mailto:support.routemaster@gmail.com"),
                ),
                const Divider(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.bug_report_outlined),
                  title: const Text("Report an issue"),
                  subtitle: const Text("Send bug details and screenshots."),
                  onTap: () => _openUrl(
                    "mailto:support.routemaster@gmail.com?subject=RouteMaster%20Driver%20Issue",
                  ),
                ),
                const Divider(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.help_outline_rounded),
                  title: const Text("FAQs"),
                  subtitle: const Text("Open help center in browser."),
                  onTap: () => _openUrl("https://routemaster.app/help"),
                ),
              ],
            ),
          ),
          _sectionCard(
            title: "About",
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text(
                  "RouteMaster Driver",
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF0F172A),
                  ),
                ),
                SizedBox(height: 6),
                Text(
                  "Version: 1.0.0+1",
                  style: TextStyle(
                    color: Color(0xFF475569),
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  "© 2026 RouteMaster. All rights reserved.",
                  style: TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
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

// ignore: unused_element
class _AllDriverRoutesPage extends StatelessWidget {
  const _AllDriverRoutesPage({
    required this.assignments,
    required this.onStartAssignment,
  });

  final List<Map<String, dynamic>> assignments;
  final Future<void> Function(Map<String, dynamic> assignment)
  onStartAssignment;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F6FB),
      appBar: AppBar(title: Text("All Routes (${assignments.length})")),
      body: assignments.isEmpty
          ? const Center(
              child: Text(
                "No assignments found.",
                style: TextStyle(
                  color: Color(0xFF64748B),
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
              itemCount: assignments.length,
              itemBuilder: (context, index) {
                final assignment = assignments[index];
                final routeName =
                    assignment["route_name"]?.toString() ?? "Route";
                final scheduledAt = DateTime.tryParse(
                  assignment["scheduled_at"]?.toString() ?? "",
                )?.toLocal();
                final scheduleLabel = scheduledAt == null
                    ? "-"
                    : DateFormat("dd MMM yyyy • hh:mm a").format(scheduledAt);
                final status = assignment["status"]?.toString() ?? "PENDING";
                final canOpenRoute =
                    status == "ASSIGNED" || status == "IN_ROUTE";
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        routeName,
                        style: const TextStyle(
                          color: Color(0xFF0F172A),
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        scheduleLabel,
                        style: const TextStyle(
                          color: Color(0xFF64748B),
                          fontWeight: FontWeight.w600,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: canOpenRoute
                              ? () => onStartAssignment(assignment)
                              : null,
                          child: Text(
                            status == "ASSIGNED"
                                ? "Start"
                                : status == "IN_ROUTE"
                                ? "Continue"
                                : status,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
