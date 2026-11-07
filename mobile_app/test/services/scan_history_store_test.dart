import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/analyze_result.dart';
import 'package:mobile_app/models/scan_history_entry.dart';
import 'package:mobile_app/services/scan_history_store.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

const plant = PredictionLabel(
  code: 'rose',
  nameTh: 'กุหลาบ',
  nameEn: 'Rose',
  confidence: 0.95,
);

const disease = PredictionLabel(
  code: 'Rose_Rust',
  nameTh: 'โรคราสนิมกุหลาบ',
  nameEn: 'Rose Rust',
  confidence: 0.87,
);

AnalyzeResult result() => const AnalyzeResult(
  imageCount: 1,
  plant: plant,
  disease: disease,
  symptoms: [],
  care: [],
  prevention: [],
  imageResults: [
    ImageResult(
      index: 0,
      filename: 'rose.png',
      disease: disease,
      symptoms: [],
      care: [],
      prevention: [],
    ),
  ],
);

class FakeRemoteHistory implements RemoteScanHistoryApi {
  List<ScanHistoryEntry> entries = [];
  bool offline = false;
  final deleted = <String>[];
  var clearCount = 0;

  @override
  Future<List<ScanHistoryEntry>> fetchHistory() async {
    if (offline) throw const ApiException(message: 'offline');
    return List.unmodifiable(entries);
  }

  @override
  Future<void> deleteHistory(String id) async {
    if (offline) throw const ApiException(message: 'offline');
    deleted.add(id);
    entries.removeWhere((entry) => entry.id == id);
  }

  @override
  Future<void> clearHistory() async {
    if (offline) throw const ApiException(message: 'offline');
    clearCount++;
    entries.clear();
  }
}

void main() {
  late ScanHistoryStore store;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    store = const ScanHistoryStore();
  });

  test('stores history newest first and restores its metadata', () async {
    final older = ScanHistoryEntry.fromResult(
      result: result(),
      manuallyConfirmed: false,
      analyzedAt: DateTime.utc(2026, 10, 30, 10),
    );
    final newer = ScanHistoryEntry.fromResult(
      result: result(),
      manuallyConfirmed: true,
      analyzedAt: DateTime.utc(2026, 10, 31, 10),
    );

    await store.add(older);
    await store.add(newer);
    final entries = await store.load();

    expect(entries.map((entry) => entry.id), [newer.id, older.id]);
    expect(entries.first.plantName, 'กุหลาบ');
    expect(entries.first.diseaseName, 'โรคราสนิมกุหลาบ');
    expect(entries.first.imageCount, 1);
    expect(entries.first.manuallyConfirmed, isTrue);
  });

  test('deletes one entry and clears all history', () async {
    final entry = ScanHistoryEntry.fromResult(
      result: result(),
      manuallyConfirmed: false,
    );
    await store.add(entry);

    await store.delete(entry.id);
    expect(await store.load(), isEmpty);

    await store.add(entry);
    await store.clear();
    expect(await store.load(), isEmpty);
  });

  test(
    'syncs remote history into local cache and falls back offline',
    () async {
      final remote = FakeRemoteHistory();
      final synced = SyncedScanHistoryStore(remote: remote, local: store);
      final entry = ScanHistoryEntry.fromResult(
        id: 'server-scan-1',
        result: result(),
        manuallyConfirmed: false,
      );
      remote.entries = [entry];

      expect((await synced.load()).single.id, 'server-scan-1');
      remote.offline = true;
      expect((await synced.load()).single.id, 'server-scan-1');
    },
  );

  test('queues an offline delete and flushes it after reconnecting', () async {
    final remote = FakeRemoteHistory();
    final synced = SyncedScanHistoryStore(remote: remote, local: store);
    final entry = ScanHistoryEntry.fromResult(
      id: 'server-scan-2',
      result: result(),
      manuallyConfirmed: false,
    );
    remote.entries = [entry];
    await synced.load();
    remote.offline = true;
    await synced.delete(entry.id);

    expect(await store.load(), isEmpty);
    remote.offline = false;
    expect(await synced.load(), isEmpty);
    expect(remote.deleted, contains(entry.id));
  });

  test(
    'keeps legacy local history when server synchronization starts',
    () async {
      final remote = FakeRemoteHistory();
      final synced = SyncedScanHistoryStore(remote: remote, local: store);
      final legacy = ScanHistoryEntry.fromResult(
        id: '1793440800000000-rose',
        result: result(),
        manuallyConfirmed: false,
        analyzedAt: DateTime.utc(2026, 10, 30),
      );
      final server = ScanHistoryEntry.fromResult(
        id: 'd1b2b0ad-c76f-4d48-8e66-a15998e04634',
        result: result(),
        manuallyConfirmed: false,
        analyzedAt: DateTime.utc(2026, 10, 31),
      );
      await store.add(legacy);
      remote.entries = [server];

      final entries = await synced.load();

      expect(entries.map((entry) => entry.id), [server.id, legacy.id]);
    },
  );
}
