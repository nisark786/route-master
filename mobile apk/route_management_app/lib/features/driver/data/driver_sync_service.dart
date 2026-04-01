import "dart:async";

import "../../auth/domain/auth_session.dart";
import "driver_api.dart";
import "driver_offline_store.dart";

class DriverSyncService {
  DriverSyncService._();
  static final DriverSyncService instance = DriverSyncService._();

  final DriverOfflineStore _offlineStore = DriverOfflineStore();
  final DriverApi _driverApi = DriverApi();

  Timer? _timer;
  bool _processing = false;
  AuthSession? _session;

  void start(AuthSession session) {
    _session = session;
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 15), (_) {
      unawaited(processQueue());
    });
    unawaited(processQueue());
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
    _session = null;
  }

  Future<void> processQueue() async {
    final session = _session;
    if (session == null || _processing) return;
    _processing = true;
    try {
      final operations = await _offlineStore.getQueuedOperations();
      for (final op in operations) {
        final operationId = op["id"]?.toString() ?? "";
        if (operationId.isEmpty) continue;
        final replayed = await _driverApi.replayQueuedOperation(
          session: session,
          operation: op,
        );
        if (replayed) {
          await _offlineStore.removeQueuedOperation(operationId);
          continue;
        }
        break;
      }
    } finally {
      _processing = false;
    }
  }
}
