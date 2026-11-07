import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:image_picker/image_picker.dart';

import '../models/analyze_outcome.dart';
import '../models/plant.dart';
import '../models/plant_library.dart';
import '../models/scan_history_entry.dart';
import 'device_identity_store.dart';

abstract interface class PhytoScanApi {
  Future<List<Plant>> fetchPlants();

  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  });
}

abstract interface class PlantLibraryApi {
  Future<List<PlantLibrarySummary>> fetchPlantLibrary();

  Future<PlantLibraryDetail> fetchPlantLibraryDetail(String plantCode);
}

abstract interface class RemoteScanHistoryApi {
  Future<List<ScanHistoryEntry>> fetchHistory();

  Future<void> deleteHistory(String id);

  Future<void> clearHistory();
}

class ApiException implements Exception {
  const ApiException({required this.message, this.statusCode, this.errorCode});

  final int? statusCode;
  final String? errorCode;
  final String message;

  bool get canRetry =>
      statusCode == null ||
      statusCode! >= 500 ||
      errorCode == 'MODEL_UNAVAILABLE' ||
      errorCode == 'INFERENCE_FAILED';

  @override
  String toString() => message;
}

class ApiService
    implements PhytoScanApi, PlantLibraryApi, RemoteScanHistoryApi {
  const ApiService({
    this.baseUrl = const String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: '',
    ),
    http.Client? client,
    this.requestTimeout = const Duration(seconds: 45),
    this.deviceIdentityStore = const DeviceIdentityStore(),
  }) : _client = client;

  static const int maxImages = 3;
  static const int maxImageSizeBytes = 10 * 1024 * 1024;

  final String baseUrl;
  final http.Client? _client;
  final Duration requestTimeout;
  final DeviceIdentityStore deviceIdentityStore;

  String get effectiveBaseUrl {
    final configured = baseUrl.trim();
    if (configured.isNotEmpty) {
      return configured.endsWith('/')
          ? configured.substring(0, configured.length - 1)
          : configured;
    }
    if (kIsWeb) return 'http://127.0.0.1:8000';
    return switch (defaultTargetPlatform) {
      TargetPlatform.android => 'http://10.0.2.2:8000',
      _ => 'http://127.0.0.1:8000',
    };
  }

  Uri _uri(String path) => Uri.parse('$effectiveBaseUrl$path');

  @override
  Future<List<Plant>> fetchPlants() async {
    try {
      final request = http.Request('GET', _uri('/api/v1/plants'));
      await _addClientHeaders(request);
      final response = await _send(request);
      final body = _decode(response.body);
      if (response.statusCode != 200) {
        throw _apiError(response.statusCode, body, 'ไม่สามารถโหลดรายการพืชได้');
      }
      return (body['plants'] as List<dynamic>)
          .map((item) => Plant.fromJson(item as Map<String, dynamic>))
          .toList(growable: false);
    } on ApiException {
      rethrow;
    } on FormatException {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งข้อมูลกลับมาไม่ถูกต้อง',
      );
    } on TypeError {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งข้อมูลกลับมาไม่ถูกต้อง',
      );
    } catch (_) {
      throw const ApiException(
        errorCode: 'NETWORK_ERROR',
        message: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง',
      );
    }
  }

  @override
  Future<List<PlantLibrarySummary>> fetchPlantLibrary() async {
    try {
      final request = http.Request('GET', _uri('/api/v1/plant-library'));
      await _addClientHeaders(request);
      final response = await _send(request);
      final body = _decode(response.body);
      if (response.statusCode != 200) {
        throw _apiError(
          response.statusCode,
          body,
          'โหลดข้อมูลคลังพืชไม่สำเร็จ',
        );
      }
      return (body['plants'] as List<dynamic>)
          .map(
            (item) =>
                PlantLibrarySummary.fromJson(item as Map<String, dynamic>),
          )
          .toList(growable: false);
    } on ApiException {
      rethrow;
    } on FormatException catch (_) {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งข้อมูลคลังพืชกลับมาไม่ถูกต้อง',
      );
    } on TypeError catch (_) {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งข้อมูลคลังพืชกลับมาไม่ถูกต้อง',
      );
    } catch (_) {
      throw const ApiException(
        errorCode: 'NETWORK_ERROR',
        message: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง',
      );
    }
  }

  @override
  Future<PlantLibraryDetail> fetchPlantLibraryDetail(String plantCode) async {
    try {
      final encodedCode = Uri.encodeComponent(plantCode.trim().toLowerCase());
      final request = http.Request(
        'GET',
        _uri('/api/v1/plant-library/$encodedCode'),
      );
      await _addClientHeaders(request);
      final response = await _send(request);
      final body = _decode(response.body);
      if (response.statusCode != 200) {
        throw _apiError(
          response.statusCode,
          body,
          'โหลดรายละเอียดพืชไม่สำเร็จ',
        );
      }
      return PlantLibraryDetail.fromJson(body);
    } on ApiException {
      rethrow;
    } on FormatException catch (_) {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งรายละเอียดพืชกลับมาไม่ถูกต้อง',
      );
    } on TypeError catch (_) {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งรายละเอียดพืชกลับมาไม่ถูกต้อง',
      );
    } catch (_) {
      throw const ApiException(
        errorCode: 'NETWORK_ERROR',
        message: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง',
      );
    }
  }

  @override
  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  }) async {
    await _validateImages(images);
    final normalizedPlantCode = plantCode?.trim();
    final request = http.MultipartRequest('POST', _uri('/api/v1/analyze'));
    if (normalizedPlantCode != null && normalizedPlantCode.isNotEmpty) {
      request.fields['plant_code'] = normalizedPlantCode;
    }

    for (final image in images) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'images',
          await _readImageBytes(image),
          filename: image.name,
          contentType: _contentType(image),
        ),
      );
    }
    await _addClientHeaders(request);

    try {
      final response = await _send(request);
      final body = _decode(response.body);
      if (response.statusCode != 200) {
        throw _apiError(response.statusCode, body, 'วิเคราะห์ภาพไม่สำเร็จ');
      }
      var outcome = AnalyzeOutcome.fromJson(body);
      if (outcome case CompletedAnalyzeOutcome(:final result)) {
        outcome = CompletedAnalyzeOutcome(
          result,
          scanId: response.headers['x-scan-id'],
        );
      }
      _validateResponseOrder(outcome, images.length);
      return outcome;
    } on ApiException {
      rethrow;
    } on FormatException {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งข้อมูลกลับมาไม่ถูกต้อง',
      );
    } on TypeError {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งข้อมูลกลับมาไม่ถูกต้อง',
      );
    } catch (_) {
      throw const ApiException(
        errorCode: 'NETWORK_ERROR',
        message: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง',
      );
    }
  }

  @override
  Future<List<ScanHistoryEntry>> fetchHistory() async {
    final request = http.Request('GET', _uri('/api/v1/history?limit=100'));
    await _addClientHeaders(request);
    final response = await _send(request);
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw _apiError(response.statusCode, body, 'โหลดประวัติการสแกนไม่สำเร็จ');
    }
    try {
      return (body['items'] as List<dynamic>)
          .map(
            (item) => ScanHistoryEntry.fromJson(item as Map<String, dynamic>),
          )
          .toList(growable: false);
    } on TypeError {
      throw const ApiException(
        errorCode: 'INVALID_RESPONSE',
        message: 'เซิร์ฟเวอร์ส่งข้อมูลประวัติกลับมาไม่ถูกต้อง',
      );
    }
  }

  @override
  Future<void> deleteHistory(String id) async {
    final request = http.Request(
      'DELETE',
      _uri('/api/v1/history/${Uri.encodeComponent(id)}'),
    );
    await _addClientHeaders(request);
    final response = await _send(request);
    if (response.statusCode != 200 && response.statusCode != 404) {
      throw _apiError(
        response.statusCode,
        _decode(response.body),
        'ลบประวัติไม่สำเร็จ',
      );
    }
  }

  @override
  Future<void> clearHistory() async {
    final request = http.Request('DELETE', _uri('/api/v1/history'));
    await _addClientHeaders(request);
    final response = await _send(request);
    if (response.statusCode != 200) {
      throw _apiError(
        response.statusCode,
        _decode(response.body),
        'ล้างประวัติไม่สำเร็จ',
      );
    }
  }

  Future<void> _addClientHeaders(http.BaseRequest request) async {
    request.headers['X-Device-ID'] = await deviceIdentityStore.getOrCreate();
    request.headers['X-Client-Platform'] = kIsWeb
        ? 'web'
        : defaultTargetPlatform.name;
    request.headers['X-App-Version'] = '1.0.0';
  }

  Future<http.Response> _send(http.BaseRequest request) async {
    final client = _client ?? http.Client();
    try {
      final streamed = await client.send(request).timeout(requestTimeout);
      return await http.Response.fromStream(streamed).timeout(requestTimeout);
    } on TimeoutException {
      throw const ApiException(
        errorCode: 'NETWORK_TIMEOUT',
        message: 'การเชื่อมต่อใช้เวลานานเกินไป กรุณาลองอีกครั้ง',
      );
    } on http.ClientException {
      throw const ApiException(
        errorCode: 'NETWORK_ERROR',
        message: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง',
      );
    } finally {
      if (_client == null) client.close();
    }
  }

  Future<void> _validateImages(List<XFile> images) async {
    if (images.isEmpty) {
      throw const ApiException(
        statusCode: 400,
        errorCode: 'NO_IMAGES',
        message: 'กรุณาเลือกภาพอย่างน้อย 1 ภาพ',
      );
    }
    if (images.length > maxImages) {
      throw const ApiException(
        statusCode: 400,
        errorCode: 'TOO_MANY_IMAGES',
        message: 'ส่งภาพได้สูงสุด 3 ภาพ',
      );
    }
    for (final image in images) {
      final name = image.name.toLowerCase();
      final isJpeg = name.endsWith('.jpg') || name.endsWith('.jpeg');
      final isPng = name.endsWith('.png');
      final mime = image.mimeType?.toLowerCase();
      final mimeMatches =
          mime == null ||
          mime.isEmpty ||
          (isJpeg && mime == 'image/jpeg') ||
          (isPng && mime == 'image/png');
      if ((!isJpeg && !isPng) || !mimeMatches) {
        throw const ApiException(
          statusCode: 415,
          errorCode: 'UNSUPPORTED_FILE_TYPE',
          message: 'รองรับเฉพาะไฟล์ JPG, JPEG และ PNG',
        );
      }
      final length = await _imageLength(image);
      if (length > maxImageSizeBytes) {
        throw const ApiException(
          statusCode: 413,
          errorCode: 'FILE_TOO_LARGE',
          message: 'ไฟล์ภาพมีขนาดใหญ่เกิน 10 MB',
        );
      }
    }
  }

  Future<int> _imageLength(XFile image) async {
    try {
      return await image.length();
    } catch (_) {
      throw const ApiException(
        statusCode: 400,
        errorCode: 'INVALID_IMAGE',
        message: 'ไม่สามารถอ่านไฟล์ภาพได้',
      );
    }
  }

  Future<List<int>> _readImageBytes(XFile image) async {
    try {
      return await image.readAsBytes();
    } catch (_) {
      throw const ApiException(
        statusCode: 400,
        errorCode: 'INVALID_IMAGE',
        message: 'ไม่สามารถอ่านไฟล์ภาพได้',
      );
    }
  }

  void _validateResponseOrder(AnalyzeOutcome outcome, int imageCount) {
    final responseOrder = switch (outcome) {
      CompletedAnalyzeOutcome(:final result) => (
        count: result.imageCount,
        indexes: result.imageResults.map((item) => item.index).toList(),
      ),
      ManualConfirmationOutcome(:final imagePredictions) => (
        count: imagePredictions.length,
        indexes: imagePredictions.map((item) => item.index).toList(),
      ),
    };
    final expectedIndexes = List<int>.generate(imageCount, (index) => index);
    if (responseOrder.count != imageCount ||
        responseOrder.indexes.length != imageCount ||
        !_listEquals(responseOrder.indexes, expectedIndexes)) {
      throw const FormatException(
        'Image response order does not match request',
      );
    }
  }

  bool _listEquals(List<int> left, List<int> right) {
    if (left.length != right.length) return false;
    for (var index = 0; index < left.length; index++) {
      if (left[index] != right[index]) return false;
    }
    return true;
  }

  MediaType _contentType(XFile image) {
    return image.name.toLowerCase().endsWith('.png')
        ? MediaType('image', 'png')
        : MediaType('image', 'jpeg');
  }

  Map<String, dynamic> _decode(String body) {
    final decoded = jsonDecode(body);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Expected a JSON object');
    }
    return decoded;
  }

  ApiException _apiError(
    int statusCode,
    Map<String, dynamic> body,
    String fallback,
  ) {
    final message = body['message'];
    final errorCode = body['error_code'];
    return ApiException(
      statusCode: statusCode,
      errorCode: errorCode is String ? errorCode : 'HTTP_$statusCode',
      message: message is String && message.isNotEmpty ? message : fallback,
    );
  }
}
