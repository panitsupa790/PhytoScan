import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

XFile image({
  String name = 'leaf.jpg',
  String? mime = 'image/jpeg',
  int size = 3,
}) {
  return XFile.fromData(
    Uint8List(size),
    path: name,
    name: name,
    mimeType: mime,
  );
}

Map<String, dynamic> prediction(String code, double confidence) => {
  'code': code,
  'name_th': '',
  'name_en': code,
  'confidence': confidence,
};

Map<String, dynamic> completedBody({List<int> indexes = const [0]}) => {
  'success': true,
  'status': 'completed',
  'image_count': indexes.length,
  'plant': prediction('rose', 0.95),
  'disease': prediction('Rose_Rust', 0.87),
  'symptoms': <String>[],
  'care': <String>[],
  'prevention': <String>[],
  'image_results': [
    for (final index in indexes)
      {
        'index': index,
        'filename': '$index.jpg',
        'disease': prediction('Rose_Rust', 0.87),
        'symptoms': <String>[],
        'care': <String>[],
        'prevention': <String>[],
      },
  ],
};

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'phytoscan_device_id_v1': 'device-test-00000001',
    });
  });

  test('resolves platform defaults without a developer LAN address', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    addTearDown(() => debugDefaultTargetPlatformOverride = null);

    expect(const ApiService().effectiveBaseUrl, 'http://10.0.2.2:8000');
    expect(
      const ApiService(baseUrl: 'http://192.0.2.10:9000/').effectiveBaseUrl,
      'http://192.0.2.10:9000',
    );
  });

  test('automatic multipart request omits plant_code field', () async {
    late String requestBody;
    final client = MockClient((request) async {
      requestBody = request.body;
      return http.Response(jsonEncode(completedBody()), 200);
    });
    final api = ApiService(baseUrl: 'http://test', client: client);

    final outcome = await api.analyze(images: [image()]);

    expect(outcome, isA<CompletedAnalyzeOutcome>());
    expect(requestBody, isNot(contains('name="plant_code"')));
    expect(requestBody, contains('name="images"'));
  });

  test('sends stable device identity and keeps backend scan id', () async {
    late String? deviceId;
    final client = MockClient((request) async {
      deviceId = request.headers['X-Device-ID'];
      return http.Response(
        jsonEncode(completedBody()),
        200,
        headers: {'x-scan-id': 'scan-server-1'},
      );
    });
    final api = ApiService(baseUrl: 'http://test', client: client);

    final outcome = await api.analyze(images: [image()]);

    expect(deviceId, 'device-test-00000001');
    expect((outcome as CompletedAnalyzeOutcome).scanId, 'scan-server-1');
  });

  test('loads device-owned history from backend', () async {
    final client = MockClient((request) async {
      expect(request.headers['X-Device-ID'], 'device-test-00000001');
      return http.Response(
        jsonEncode({
          'items': [
            {
              'id': 'scan-1',
              'analyzed_at': '2026-10-31T10:00:00Z',
              'plant_code': 'rose',
              'plant_name_th': 'กุหลาบ',
              'plant_name_en': 'Rose',
              'plant_confidence': 0.95,
              'plant_source': 'automatic',
              'image_count': 1,
              'disease_code': 'Rose_Rust',
              'disease_name_th': '',
              'disease_name_en': 'Rose Rust',
              'disease_confidence': 0.87,
              'disease_names': ['Rose Rust'],
              'diseases': <Map<String, dynamic>>[],
            },
          ],
          'total': 1,
          'limit': 100,
          'offset': 0,
        }),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });
    final api = ApiService(baseUrl: 'http://test', client: client);

    final history = await api.fetchHistory();

    expect(history.single.id, 'scan-1');
    expect(history.single.plantName, 'กุหลาบ');
    expect(history.single.diseaseName, 'Rose Rust');
    expect(history.single.manuallyConfirmed, isFalse);
  });

  test('manual request sends non-empty plant_code', () async {
    late String requestBody;
    final client = MockClient((request) async {
      requestBody = request.body;
      return http.Response(jsonEncode(completedBody()), 200);
    });
    final api = ApiService(baseUrl: 'http://test', client: client);

    await api.analyze(plantCode: 'rose', images: [image()]);

    expect(requestBody, contains('name="plant_code"'));
    expect(requestBody, contains('rose'));
  });

  test(
    'blank plant code is omitted instead of sent as an empty field',
    () async {
      late String requestBody;
      final client = MockClient((request) async {
        requestBody = request.body;
        return http.Response(jsonEncode(completedBody()), 200);
      });
      final api = ApiService(baseUrl: 'http://test', client: client);

      await api.analyze(plantCode: '   ', images: [image()]);

      expect(requestBody, isNot(contains('name="plant_code"')));
    },
  );

  test('keeps backend status, error code, and message', () async {
    final client = MockClient(
      (_) async => http.Response(
        jsonEncode({
          'success': false,
          'error_code': 'MODEL_UNAVAILABLE',
          'message': 'Plant analysis model is unavailable',
        }),
        503,
      ),
    );
    final api = ApiService(baseUrl: 'http://test', client: client);

    try {
      await api.analyze(images: [image()]);
      fail('Expected ApiException');
    } on ApiException catch (error) {
      expect(error.statusCode, 503);
      expect(error.errorCode, 'MODEL_UNAVAILABLE');
      expect(error.message, 'Plant analysis model is unavailable');
      expect(error.canRetry, isTrue);
    }
  });

  test('rejects unsupported type before network request', () async {
    var requests = 0;
    final api = ApiService(
      baseUrl: 'http://test',
      client: MockClient((_) async {
        requests++;
        return http.Response('{}', 200);
      }),
    );

    await expectLater(
      api.analyze(
        images: [image(name: 'leaf.heic', mime: 'image/heic')],
      ),
      throwsA(
        isA<ApiException>().having(
          (error) => error.errorCode,
          'errorCode',
          'UNSUPPORTED_FILE_TYPE',
        ),
      ),
    );
    expect(requests, 0);
  });

  test('requires one to three images before network request', () async {
    var requests = 0;
    final api = ApiService(
      baseUrl: 'http://test',
      client: MockClient((_) async {
        requests++;
        return http.Response('{}', 200);
      }),
    );

    await expectLater(
      api.analyze(images: const []),
      throwsA(
        isA<ApiException>().having(
          (error) => error.errorCode,
          'errorCode',
          'NO_IMAGES',
        ),
      ),
    );
    await expectLater(
      api.analyze(
        images: List.generate(4, (index) => image(name: '$index.jpg')),
      ),
      throwsA(
        isA<ApiException>().having(
          (error) => error.errorCode,
          'errorCode',
          'TOO_MANY_IMAGES',
        ),
      ),
    );
    expect(requests, 0);
  });

  test('rejects files larger than 10 MB before network request', () async {
    final api = ApiService(
      baseUrl: 'http://test',
      client: MockClient((_) async => http.Response('{}', 200)),
    );

    await expectLater(
      api.analyze(images: [image(size: ApiService.maxImageSizeBytes + 1)]),
      throwsA(
        isA<ApiException>().having(
          (error) => error.errorCode,
          'errorCode',
          'FILE_TOO_LARGE',
        ),
      ),
    );
  });

  test('rejects response indexes that do not match upload order', () async {
    final api = ApiService(
      baseUrl: 'http://test',
      client: MockClient(
        (_) async =>
            http.Response(jsonEncode(completedBody(indexes: [1, 0])), 200),
      ),
    );

    await expectLater(
      api.analyze(
        images: [
          image(name: 'one.jpg'),
          image(name: 'two.jpg'),
        ],
      ),
      throwsA(
        isA<ApiException>().having(
          (error) => error.errorCode,
          'errorCode',
          'INVALID_RESPONSE',
        ),
      ),
    );
  });

  test('reports timeout as a retryable typed error', () async {
    final api = ApiService(
      baseUrl: 'http://test',
      requestTimeout: const Duration(milliseconds: 1),
      client: MockClient((_) async {
        await Future<void>.delayed(const Duration(milliseconds: 20));
        return http.Response(jsonEncode(completedBody()), 200);
      }),
    );

    await expectLater(
      api.analyze(images: [image()]),
      throwsA(
        isA<ApiException>()
            .having((error) => error.errorCode, 'errorCode', 'NETWORK_TIMEOUT')
            .having((error) => error.canRetry, 'canRetry', isTrue),
      ),
    );
  });

  test('reports offline client failure as a retryable typed error', () async {
    final api = ApiService(
      baseUrl: 'http://test',
      client: MockClient((_) async => throw http.ClientException('offline')),
    );

    await expectLater(
      api.analyze(images: [image()]),
      throwsA(
        isA<ApiException>()
            .having((error) => error.errorCode, 'errorCode', 'NETWORK_ERROR')
            .having((error) => error.canRetry, 'canRetry', isTrue),
      ),
    );
  });
}
