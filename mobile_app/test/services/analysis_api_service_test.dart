import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/services/analysis_api_service.dart';

const successBody = {
  'success': true,
  'image_count': 2,
  'plant': {
    'code': 'snake_plant',
    'name_th': 'ลิ้นมังกร',
    'name_en': 'Snake Plant',
    'confidence': 0.91,
  },
  'disease': {
    'code': 'root_rot',
    'name_th': 'โรครากเน่า',
    'name_en': 'Root Rot',
    'confidence': 0.87,
  },
  'symptoms': ['อาการจาก API'],
  'care': ['การดูแลจาก API'],
  'prevention': ['การป้องกันจาก API'],
};

void main() {
  late Directory tempDirectory;

  setUp(() async {
    tempDirectory = await Directory.systemTemp.createTemp('phytoscan-test-');
  });

  tearDown(() async {
    await tempDirectory.delete(recursive: true);
  });

  test(
    'uploads every image with the images field and parses response',
    () async {
      final first = await _createImage(tempDirectory, 'first.jpg');
      final second = await _createImage(tempDirectory, 'second.png');
      final client = RecordingClient(
        responseBody: jsonEncode(successBody),
        statusCode: 200,
      );
      final service = AnalysisApiService(
        client: client,
        baseUrl: 'http://example.test:8000',
      );

      final result = await service.analyze([first, second]);

      expect(
        client.lastRequest?.url.toString(),
        'http://example.test:8000/api/v1/analyze',
      );
      expect(client.lastRequest?.files, hasLength(2));
      expect(
        client.lastRequest?.files.map((file) => file.field),
        everyElement('images'),
      );
      expect(
        client.lastRequest?.files.map((file) => file.contentType.toString()),
        ['image/jpeg', 'image/png'],
      );
      expect(result.imageCount, 2);
      expect(result.plant.nameTh, 'ลิ้นมังกร');
    },
  );

  test('maps backend error code to a user-friendly message', () async {
    final image = await _createImage(tempDirectory, 'leaf.jpg');
    final client = RecordingClient(
      responseBody: jsonEncode({
        'success': false,
        'error_code': 'INVALID_IMAGE',
        'message': 'backend detail',
      }),
      statusCode: 400,
    );
    final service = AnalysisApiService(client: client);

    await expectLater(
      service.analyze([image]),
      throwsA(
        isA<AnalysisApiException>()
            .having((error) => error.errorCode, 'errorCode', 'INVALID_IMAGE')
            .having(
              (error) => error.userMessage,
              'userMessage',
              'ไฟล์ภาพไม่ถูกต้อง กรุณาเลือกภาพใหม่',
            ),
      ),
    );
  });

  test('reports request timeout', () async {
    final image = await _createImage(tempDirectory, 'leaf.jpg');
    final client = DelayedClient(const Duration(milliseconds: 50));
    final service = AnalysisApiService(
      client: client,
      timeout: const Duration(milliseconds: 1),
    );

    await expectLater(
      service.analyze([image]),
      throwsA(
        isA<AnalysisApiException>().having(
          (error) => error.errorCode,
          'errorCode',
          'TIMEOUT',
        ),
      ),
    );
  });
}

Future<XFile> _createImage(Directory directory, String name) async {
  final file = File('${directory.path}${Platform.pathSeparator}$name');
  await file.writeAsBytes([1, 2, 3]);
  return XFile(file.path);
}

class RecordingClient extends http.BaseClient {
  final String responseBody;
  final int statusCode;
  http.MultipartRequest? lastRequest;

  RecordingClient({required this.responseBody, required this.statusCode});

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    lastRequest = request as http.MultipartRequest;
    await request.finalize().drain<void>();
    return http.StreamedResponse(
      Stream.value(utf8.encode(responseBody)),
      statusCode,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }
}

class DelayedClient extends http.BaseClient {
  final Duration delay;

  DelayedClient(this.delay);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    await request.finalize().drain<void>();
    await Future<void>.delayed(delay);
    return http.StreamedResponse(const Stream.empty(), 200);
  }
}
