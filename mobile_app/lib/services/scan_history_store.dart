import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/scan_history_entry.dart';
import 'api_service.dart';

abstract interface class ScanHistoryRepository {
  Future<List<ScanHistoryEntry>> load();

  Future<void> add(ScanHistoryEntry entry);

  Future<void> delete(String id);

  Future<void> clear();
}

class ScanHistoryStore implements ScanHistoryRepository {
  const ScanHistoryStore();

  static const _storageKey = 'scan_history_v1';
  static const _pendingDeletesKey = 'scan_history_pending_deletes_v1';
  static const _pendingClearKey = 'scan_history_pending_clear_v1';
  static const _maximumEntries = 100;

  @override
  Future<List<ScanHistoryEntry>> load() async {
    final preferences = await SharedPreferences.getInstance();
    final encodedEntries = preferences.getStringList(_storageKey) ?? const [];
    final entries = <ScanHistoryEntry>[];
    for (final encoded in encodedEntries) {
      try {
        final json = jsonDecode(encoded) as Map<String, dynamic>;
        entries.add(ScanHistoryEntry.fromJson(json));
      } on FormatException {
        // Ignore only the damaged row so the remaining local history is usable.
      } on TypeError {
        // Ignore rows written with an incompatible schema.
      }
    }
    entries.sort((a, b) => b.analyzedAt.compareTo(a.analyzedAt));
    return List.unmodifiable(entries);
  }

  @override
  Future<void> add(ScanHistoryEntry entry) async {
    final entries = [...await load()]
      ..removeWhere((item) => item.id == entry.id)
      ..insert(0, entry);
    await _write(entries.take(_maximumEntries));
  }

  @override
  Future<void> delete(String id) async {
    final entries = [...await load()]..removeWhere((item) => item.id == id);
    await _write(entries);
  }

  @override
  Future<void> clear() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(_storageKey);
  }

  Future<void> replaceAll(Iterable<ScanHistoryEntry> entries) async {
    await _write(entries.take(_maximumEntries));
  }

  Future<List<String>> pendingDeletes() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getStringList(_pendingDeletesKey) ?? const [];
  }

  Future<void> queueDelete(String id) async {
    final preferences = await SharedPreferences.getInstance();
    final pending = {...await pendingDeletes(), id};
    await preferences.setStringList(_pendingDeletesKey, pending.toList());
  }

  Future<void> removePendingDelete(String id) async {
    final preferences = await SharedPreferences.getInstance();
    final pending = [...await pendingDeletes()]..remove(id);
    await preferences.setStringList(_pendingDeletesKey, pending);
  }

  Future<bool> hasPendingClear() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getBool(_pendingClearKey) ?? false;
  }

  Future<void> setPendingClear(bool value) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool(_pendingClearKey, value);
  }

  Future<void> _write(Iterable<ScanHistoryEntry> entries) async {
    final preferences = await SharedPreferences.getInstance();
    final encoded = entries
        .map((entry) => jsonEncode(entry.toJson()))
        .toList(growable: false);
    await preferences.setStringList(_storageKey, encoded);
  }
}

class SyncedScanHistoryStore implements ScanHistoryRepository {
  const SyncedScanHistoryStore({
    required this.remote,
    this.local = const ScanHistoryStore(),
  });

  final RemoteScanHistoryApi remote;
  final ScanHistoryStore local;

  @override
  Future<List<ScanHistoryEntry>> load() async {
    final cached = await local.load();
    try {
      await _flushPendingChanges();
      final remoteEntries = await remote.fetchHistory();
      final remoteIds = remoteEntries.map((entry) => entry.id).toSet();
      final legacyLocalEntries = cached.where(
        (entry) =>
            !remoteIds.contains(entry.id) && !_looksLikeServerScanId(entry.id),
      );
      final entries = [...remoteEntries, ...legacyLocalEntries]
        ..sort((a, b) => b.analyzedAt.compareTo(a.analyzedAt));
      await local.replaceAll(entries);
      return List.unmodifiable(entries);
    } catch (_) {
      return cached;
    }
  }

  @override
  Future<void> add(ScanHistoryEntry entry) => local.add(entry);

  @override
  Future<void> delete(String id) async {
    await local.delete(id);
    try {
      await remote.deleteHistory(id);
    } catch (_) {
      await local.queueDelete(id);
    }
  }

  @override
  Future<void> clear() async {
    await local.clear();
    try {
      await remote.clearHistory();
      await local.setPendingClear(false);
    } catch (_) {
      await local.setPendingClear(true);
    }
  }

  Future<void> _flushPendingChanges() async {
    if (await local.hasPendingClear()) {
      await remote.clearHistory();
      await local.setPendingClear(false);
    }
    for (final id in await local.pendingDeletes()) {
      await remote.deleteHistory(id);
      await local.removePendingDelete(id);
    }
  }

  bool _looksLikeServerScanId(String value) => RegExp(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$',
  ).hasMatch(value);
}
