import "dart:convert";

import "package:shared_preferences/shared_preferences.dart";

class DriverOfflineStore {
  static const String _assignmentsKey = "driver.cache.assignments.v1";
  static const String _queueKey = "driver.sync.queue.v1";
  static const String _assignmentDetailPrefix =
      "driver.cache.assignment_detail.v1.";
  static const String _stopDetailPrefix = "driver.cache.stop_detail.v1.";
  static const String _assignmentInventoryPrefix =
      "driver.cache.assignment_inventory.v1.";

  Future<void> saveAssignments(List<Map<String, dynamic>> assignments) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_assignmentsKey, jsonEncode(assignments));
  }

  Future<List<Map<String, dynamic>>> getAssignments() async {
    final prefs = await SharedPreferences.getInstance();
    return _decodeList(prefs.getString(_assignmentsKey));
  }

  Future<void> saveAssignmentDetail(
    String assignmentId,
    Map<String, dynamic> detail,
  ) async {
    if (assignmentId.trim().isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      "$_assignmentDetailPrefix$assignmentId",
      jsonEncode(detail),
    );
  }

  Future<Map<String, dynamic>> getAssignmentDetail(String assignmentId) async {
    if (assignmentId.trim().isEmpty) return const {};
    final prefs = await SharedPreferences.getInstance();
    return _decodeMap(prefs.getString("$_assignmentDetailPrefix$assignmentId"));
  }

  Future<void> saveStopDetail(
    String assignmentId,
    String shopId,
    Map<String, dynamic> detail,
  ) async {
    if (assignmentId.trim().isEmpty || shopId.trim().isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    final key = "$_stopDetailPrefix$assignmentId.$shopId";
    await prefs.setString(key, jsonEncode(detail));
  }

  Future<Map<String, dynamic>> getStopDetail(
    String assignmentId,
    String shopId,
  ) async {
    if (assignmentId.trim().isEmpty || shopId.trim().isEmpty) return const {};
    final prefs = await SharedPreferences.getInstance();
    final key = "$_stopDetailPrefix$assignmentId.$shopId";
    return _decodeMap(prefs.getString(key));
  }

  Future<void> saveAssignmentInventory(
    String assignmentId,
    Map<String, dynamic> payload,
  ) async {
    if (assignmentId.trim().isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      "$_assignmentInventoryPrefix$assignmentId",
      jsonEncode(payload),
    );
  }

  Future<Map<String, dynamic>> getAssignmentInventory(
    String assignmentId,
  ) async {
    if (assignmentId.trim().isEmpty) return const {};
    final prefs = await SharedPreferences.getInstance();
    return _decodeMap(
      prefs.getString("$_assignmentInventoryPrefix$assignmentId"),
    );
  }

  Future<void> enqueueOperation(Map<String, dynamic> operation) async {
    final queue = await getQueuedOperations();
    queue.add(operation);
    await _saveQueue(queue);
  }

  Future<List<Map<String, dynamic>>> getQueuedOperations() async {
    final prefs = await SharedPreferences.getInstance();
    return _decodeList(prefs.getString(_queueKey));
  }

  Future<void> removeQueuedOperation(String operationId) async {
    if (operationId.trim().isEmpty) return;
    final queue = await getQueuedOperations();
    final next = queue
        .where((item) => (item["id"]?.toString() ?? "") != operationId)
        .toList();
    await _saveQueue(next);
  }

  Future<void> _saveQueue(List<Map<String, dynamic>> queue) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_queueKey, jsonEncode(queue));
  }

  Future<void> applyStartAssignmentOffline(String assignmentId) async {
    final assignments = await getAssignments();
    var changedAssignments = false;
    final updatedAssignments = assignments.map((item) {
      if ((item["id"]?.toString() ?? "") != assignmentId) return item;
      changedAssignments = true;
      return {...item, "status": "IN_ROUTE"};
    }).toList();
    if (changedAssignments) {
      await saveAssignments(updatedAssignments);
    }

    final detail = await getAssignmentDetail(assignmentId);
    if (detail.isNotEmpty) {
      final next = {...detail, "status": "IN_ROUTE"};
      await saveAssignmentDetail(assignmentId, next);
    }
  }

  Future<void> applyCheckInOffline(String assignmentId, String shopId) async {
    final detail = await getAssignmentDetail(assignmentId);
    if (detail.isNotEmpty) {
      final nextStops = _updateStops(
        detail["stops"],
        shopId: shopId,
        patch: {
          "status": "CHECKED_IN",
          "check_in_at": DateTime.now().toUtc().toIso8601String(),
        },
      );
      final next = {
        ...detail,
        "status": "IN_ROUTE",
        "next_pending_stop_id": _findNextPendingStopId(nextStops),
        "stops": nextStops,
      };
      await saveAssignmentDetail(assignmentId, next);
    }

    final stopDetail = await getStopDetail(assignmentId, shopId);
    if (stopDetail.isNotEmpty) {
      final stop = _decodeMap(stopDetail["stop"]);
      final nextStop = {
        ...stop,
        "status": "CHECKED_IN",
        "check_in_at": DateTime.now().toUtc().toIso8601String(),
      };
      await saveStopDetail(assignmentId, shopId, {
        ...stopDetail,
        "stop": nextStop,
      });
    }
  }

  Future<void> applySkipStopOffline(
    String assignmentId,
    String shopId,
    String reason,
  ) async {
    final detail = await getAssignmentDetail(assignmentId);
    if (detail.isNotEmpty) {
      final nextStops = _updateStops(
        detail["stops"],
        shopId: shopId,
        patch: {
          "status": "SKIPPED",
          "skip_reason": reason,
          "check_out_at": DateTime.now().toUtc().toIso8601String(),
        },
      );
      final next = {
        ...detail,
        "next_pending_stop_id": _findNextPendingStopId(nextStops),
        "stops": nextStops,
      };
      await saveAssignmentDetail(assignmentId, next);
    }

    final stopDetail = await getStopDetail(assignmentId, shopId);
    if (stopDetail.isNotEmpty) {
      final stop = _decodeMap(stopDetail["stop"]);
      final nextStop = {...stop, "status": "SKIPPED", "skip_reason": reason};
      await saveStopDetail(assignmentId, shopId, {
        ...stopDetail,
        "stop": nextStop,
      });
    }
  }

  Future<void> applyCompleteOrderOffline(
    String assignmentId,
    String shopId,
    List<Map<String, dynamic>> items,
  ) async {
    final stopDetail = await getStopDetail(assignmentId, shopId);
    if (stopDetail.isEmpty) return;
    final products = _decodeList(stopDetail["products"]);
    final productById = <String, Map<String, dynamic>>{
      for (final product in products)
        (product["id"]?.toString() ?? ""): product,
    };
    final orderedItems = <Map<String, dynamic>>[];
    double total = 0;
    for (final item in items) {
      final productId = item["product_id"]?.toString() ?? "";
      final qty = int.tryParse("${item["quantity"] ?? 0}") ?? 0;
      if (productId.isEmpty || qty <= 0) continue;
      final product = productById[productId] ?? const <String, dynamic>{};
      final rate = double.tryParse("${product["rate"] ?? 0}") ?? 0;
      final lineTotal = rate * qty;
      total += lineTotal;
      orderedItems.add({
        "product_id": productId,
        "name": product["name"] ?? "Product",
        "quantity": qty,
        "rate": rate,
        "line_total": lineTotal,
      });
    }

    final stop = _decodeMap(stopDetail["stop"]);
    final nextStop = {
      ...stop,
      "ordered_items": orderedItems,
      "invoice_total": total,
      "invoice_number": stop["invoice_number"] ?? "PENDING-SYNC",
    };
    await saveStopDetail(assignmentId, shopId, {
      ...stopDetail,
      "stop": nextStop,
    });
  }

  Future<void> applyCheckOutOffline(String assignmentId, String shopId) async {
    final nowIso = DateTime.now().toUtc().toIso8601String();
    final detail = await getAssignmentDetail(assignmentId);
    if (detail.isNotEmpty) {
      final nextStops = _updateStops(
        detail["stops"],
        shopId: shopId,
        patch: {"status": "COMPLETED", "check_out_at": nowIso},
      );
      final totalStops = nextStops.length;
      final completedStops = nextStops
          .where((stop) => (stop["status"]?.toString() ?? "") == "COMPLETED")
          .length;
      final routeCompleted = totalStops > 0 && completedStops >= totalStops;
      final next = {
        ...detail,
        "status": routeCompleted
            ? "COMPLETED"
            : (detail["status"] ?? "IN_ROUTE"),
        "progress": {
          ..._decodeMap(detail["progress"]),
          "total_stops": totalStops,
          "completed_stops": completedStops,
        },
        "next_pending_stop_id": _findNextPendingStopId(nextStops),
        "stops": nextStops,
      };
      await saveAssignmentDetail(assignmentId, next);
    }

    final stopDetail = await getStopDetail(assignmentId, shopId);
    if (stopDetail.isNotEmpty) {
      final stop = _decodeMap(stopDetail["stop"]);
      final nextStop = {...stop, "status": "COMPLETED", "check_out_at": nowIso};
      await saveStopDetail(assignmentId, shopId, {
        ...stopDetail,
        "stop": nextStop,
      });
    }
  }

  Future<void> applyAssignmentInventoryOffline(
    String assignmentId,
    List<Map<String, dynamic>> items,
  ) async {
    final cached = await getAssignmentInventory(assignmentId);
    if (cached.isEmpty) return;

    final products = _decodeList(cached["products"]);
    final desiredById = <String, int>{};
    for (final item in items) {
      final productId = item["product_id"]?.toString() ?? "";
      final qty = int.tryParse("${item["quantity"] ?? 0}") ?? 0;
      if (productId.isEmpty || qty <= 0) continue;
      desiredById[productId] = qty;
    }

    final loadedById = <String, int>{};
    for (final product in products) {
      final productId = product["id"]?.toString() ?? "";
      if (productId.isEmpty) continue;
      loadedById[productId] =
          int.tryParse("${product["loaded_quantity"] ?? 0}") ?? 0;
    }

    final nextProducts = <Map<String, dynamic>>[];
    for (final product in products) {
      final productId = product["id"]?.toString() ?? "";
      if (productId.isEmpty) {
        nextProducts.add(product);
        continue;
      }

      final currentLoaded = loadedById[productId] ?? 0;
      final desiredLoaded = desiredById[productId] ?? 0;
      final delta = desiredLoaded - currentLoaded;
      final currentAvailable =
          int.tryParse("${product["quantity_count"] ?? 0}") ?? 0;
      final nextAvailable = currentAvailable - delta;

      nextProducts.add({
        ...product,
        "loaded_quantity": desiredLoaded,
        "quantity_count": nextAvailable < 0 ? 0 : nextAvailable,
      });
    }

    final loadedItems = <Map<String, dynamic>>[];
    var loadedTotal = 0;
    for (final product in nextProducts) {
      final productId = product["id"]?.toString() ?? "";
      final productName = product["name"]?.toString() ?? "Product";
      final qty = int.tryParse("${product["loaded_quantity"] ?? 0}") ?? 0;
      if (productId.isEmpty || qty <= 0) continue;
      loadedTotal += qty;
      loadedItems.add({
        "product_id": productId,
        "product_name": productName,
        "quantity": qty,
      });
    }

    final nextPayload = {
      ...cached,
      "products": nextProducts,
      "loaded_items": loadedItems,
      "loaded_items_count": loadedItems.length,
      "loaded_quantity_total": loadedTotal,
    };
    await saveAssignmentInventory(assignmentId, nextPayload);
  }

  List<Map<String, dynamic>> _updateStops(
    dynamic rawStops, {
    required String shopId,
    required Map<String, dynamic> patch,
  }) {
    final stops = _decodeList(rawStops);
    return stops.map((stop) {
      if ((stop["shop_id"]?.toString() ?? "") != shopId) return stop;
      return {...stop, ...patch};
    }).toList();
  }

  String? _findNextPendingStopId(List<Map<String, dynamic>> stops) {
    for (final stop in stops) {
      final status = stop["status"]?.toString() ?? "";
      if (status != "COMPLETED" && status != "SKIPPED") {
        final stopId = stop["id"]?.toString() ?? "";
        return stopId.isEmpty ? null : stopId;
      }
    }
    return null;
  }

  List<Map<String, dynamic>> _decodeList(dynamic raw) {
    if (raw is List) {
      return raw
          .whereType<Map>()
          .map((item) => item.cast<String, dynamic>())
          .toList();
    }
    if (raw is String && raw.trim().isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          return decoded
              .whereType<Map>()
              .map((item) => item.cast<String, dynamic>())
              .toList();
        }
      } catch (_) {}
    }
    return const [];
  }

  Map<String, dynamic> _decodeMap(dynamic raw) {
    if (raw is Map<String, dynamic>) return raw;
    if (raw is Map) return raw.cast<String, dynamic>();
    if (raw is String && raw.trim().isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is Map) return decoded.cast<String, dynamic>();
      } catch (_) {}
    }
    return const {};
  }
}
