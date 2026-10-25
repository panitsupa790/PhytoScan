import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:image_picker/image_picker.dart';

import '../models/analyze_result.dart';
import '../models/plant.dart';

abstract interface class PhytoScanApi {
  Future<List<Plant>> fetchPlants();

  Future<AnalyzeResult> analyze({
    required String plantCode,
    required List<XFile> images,
  });
}

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class ApiService implements PhytoScanApi {
  const ApiService({
    this.baseUrl = const String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000',
    ),
  });

  final String baseUrl;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  @override
  Future<List<Plant>> fetchPlants() async {
    try {
      final response = await http.get(_uri('/api/v1/plants'));
      final body = _decode(response.body);
      if (response.statusCode != 200) {
        throw ApiException(_message(body, 'ไม่สามารถโหลดรายการพืชได้'));
      }
      return (body['plants'] as List<dynamic>)
          .map((item) => Plant.fromJson(item as Map<String, dynamic>))
          .toList(growable: false);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง');
    }
  }

  @override
  Future<AnalyzeResult> analyze({
    required String plantCode,
    required List<XFile> images,
  }) async {
    final request = http.MultipartRequest('POST', _uri('/api/v1/analyze'))
      ..fields['plant_code'] = plantCode;

    for (final image in images) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'images',
          await image.readAsBytes(),
          filename: image.name,
          contentType: _contentType(image),
        ),
      );
    }

    try {
      final streamed = await request.send();
      final response = await http.Response.fromStream(streamed);
      final body = _decode(response.body);
      if (response.statusCode != 200) {
        throw ApiException(_message(body, 'วิเคราะห์ภาพไม่สำเร็จ'));
      }
      return AnalyzeResult.fromJson(body);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองอีกครั้ง');
    }
  }

  MediaType _contentType(XFile image) {
    final mime = image.mimeType?.toLowerCase();
    if (mime == 'image/png' || image.name.toLowerCase().endsWith('.png')) {
      return MediaType('image', 'png');
    }
    return MediaType('image', 'jpeg');
  }

  Map<String, dynamic> _decode(String body) {
    try {
      return jsonDecode(body) as Map<String, dynamic>;
    } catch (_) {
      throw const ApiException('เซิร์ฟเวอร์ส่งข้อมูลกลับมาไม่ถูกต้อง');
    }
  }

  String _message(Map<String, dynamic> body, String fallback) {
    final message = body['message'];
    return message is String && message.isNotEmpty ? message : fallback;
  }
}
