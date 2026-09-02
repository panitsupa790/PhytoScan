import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/config/api_config.dart';
import 'package:mobile_app/models/analysis_result.dart';

class AnalysisApiException implements Exception {
  final String? errorCode;
  final String userMessage;

  const AnalysisApiException({required this.userMessage, this.errorCode});

  factory AnalysisApiException.fromErrorCode(String? errorCode) {
    final message = switch (errorCode) {
      'INVALID_IMAGE' => 'ไฟล์ภาพไม่ถูกต้อง กรุณาเลือกภาพใหม่',
      'UNSUPPORTED_FILE_TYPE' => 'รองรับเฉพาะไฟล์ JPG, JPEG และ PNG',
      'FILE_TOO_LARGE' => 'รูปภาพมีขนาดใหญ่เกินกำหนด',
      'TOO_MANY_IMAGES' => 'เลือกภาพได้สูงสุด 3 ภาพ',
      'NO_IMAGES' => 'กรุณาเลือกภาพอย่างน้อย 1 ภาพ',
      _ => 'เกิดข้อผิดพลาดจากเซิร์ฟเวอร์ กรุณาลองใหม่อีกครั้ง',
    };

    return AnalysisApiException(errorCode: errorCode, userMessage: message);
  }

  @override
  String toString() => userMessage;
}

abstract interface class AnalysisService {
  Future<AnalysisResult> analyze(List<XFile> images);
}

class AnalysisApiService implements AnalysisService {
  final http.Client? _client;
  final String baseUrl;
  final Duration timeout;

  const AnalysisApiService({
    http.Client? client,
    this.baseUrl = ApiConfig.baseUrl,
    this.timeout = ApiConfig.analyzeTimeout,
  }) : _client = client;

  @override
  Future<AnalysisResult> analyze(List<XFile> images) async {
    if (images.isEmpty) {
      throw AnalysisApiException.fromErrorCode('NO_IMAGES');
    }
    if (images.length > 3) {
      throw AnalysisApiException.fromErrorCode('TOO_MANY_IMAGES');
    }

    final client = _client ?? http.Client();
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/api/v1/analyze'),
      );

      for (final image in images) {
        request.files.add(
          await http.MultipartFile.fromPath(
            'images',
            image.path,
            filename: image.name,
            contentType: _contentTypeFor(image),
          ),
        );
      }

      final streamedResponse = await client.send(request).timeout(timeout);
      final response = await http.Response.fromStream(streamedResponse);
      final responseJson = _decodeResponse(response);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return AnalysisResult.fromJson(responseJson);
      }

      throw AnalysisApiException.fromErrorCode(
        responseJson['error_code'] as String?,
      );
    } on AnalysisApiException {
      rethrow;
    } on TimeoutException {
      throw const AnalysisApiException(
        errorCode: 'TIMEOUT',
        userMessage: 'การวิเคราะห์ใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง',
      );
    } on SocketException {
      throw const AnalysisApiException(
        errorCode: 'NETWORK_ERROR',
        userMessage:
            'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาตรวจสอบการเชื่อมต่อแล้วลองใหม่',
      );
    } on http.ClientException {
      throw const AnalysisApiException(
        errorCode: 'NETWORK_ERROR',
        userMessage:
            'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาตรวจสอบการเชื่อมต่อแล้วลองใหม่',
      );
    } on FileSystemException {
      throw AnalysisApiException.fromErrorCode('INVALID_IMAGE');
    } on FormatException {
      throw const AnalysisApiException(
        errorCode: 'INVALID_RESPONSE',
        userMessage: 'เซิร์ฟเวอร์ส่งข้อมูลไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง',
      );
    } finally {
      if (_client == null) {
        client.close();
      }
    }
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    if (decoded is! Map) {
      throw const FormatException('Response must be a JSON object.');
    }
    return decoded.cast<String, dynamic>();
  }

  MediaType _contentTypeFor(XFile image) {
    final extension = image.name.toLowerCase().split('.').last;
    return switch (extension) {
      'jpg' || 'jpeg' => MediaType('image', 'jpeg'),
      'png' => MediaType('image', 'png'),
      _ => throw AnalysisApiException.fromErrorCode('UNSUPPORTED_FILE_TYPE'),
    };
  }
}
