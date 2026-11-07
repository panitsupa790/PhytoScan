import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

class DeviceIdentityStore {
  const DeviceIdentityStore();

  static const _storageKey = 'phytoscan_device_id_v1';
  static String? _memoryFallback;

  Future<String> getOrCreate() async {
    try {
      final preferences = await SharedPreferences.getInstance();
      final existing = preferences.getString(_storageKey)?.trim();
      if (existing != null && existing.length >= 8) return existing;
      final generated = _memoryFallback ??= _uuidV4();
      await preferences.setString(_storageKey, generated);
      return generated;
    } catch (_) {
      return _memoryFallback ??= _uuidV4();
    }
  }

  String _uuidV4() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    String hex(int value) => value.toRadixString(16).padLeft(2, '0');
    final value = bytes.map(hex).join();
    return '${value.substring(0, 8)}-'
        '${value.substring(8, 12)}-'
        '${value.substring(12, 16)}-'
        '${value.substring(16, 20)}-'
        '${value.substring(20)}';
  }
}
