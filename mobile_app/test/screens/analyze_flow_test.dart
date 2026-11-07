import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/models/analyze_result.dart';
import 'package:mobile_app/models/plant.dart';
import 'package:mobile_app/models/scan_history_entry.dart';
import 'package:mobile_app/screens/analyze_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/scan_history_store.dart';
import 'package:mobile_app/theme/app_theme.dart';

const rose = Plant(
  code: 'rose',
  nameTh: 'กุหลาบ',
  nameEn: 'Rose',
  diseaseCount: 8,
);

const rosePrediction = PredictionLabel(
  code: 'rose',
  nameTh: 'กุหลาบ',
  nameEn: 'Rose',
  confidence: 0.95,
);

const diseasePrediction = PredictionLabel(
  code: 'Rose_Rust',
  nameTh: '',
  nameEn: 'Rose Rust',
  confidence: 0.87,
);

CompletedAnalyzeOutcome completed(int imageCount) => CompletedAnalyzeOutcome(
  AnalyzeResult(
    imageCount: imageCount,
    plant: rosePrediction,
    disease: diseasePrediction,
    symptoms: const [],
    care: const [],
    prevention: const [],
    imageResults: [
      for (var index = 0; index < imageCount; index++)
        ImageResult(
          index: index,
          filename: '$index.png',
          disease: diseasePrediction,
          symptoms: const [],
          care: const [],
          prevention: const [],
        ),
    ],
  ),
);

ManualConfirmationOutcome manual({bool inconsistent = false}) {
  final count = inconsistent ? 2 : 1;
  return ManualConfirmationOutcome(
    message: 'confirm',
    suggestedPlant: inconsistent ? null : rosePrediction,
    imagePredictions: [
      for (var index = 0; index < count; index++)
        ImagePlantPrediction(
          index: index,
          filename: '$index.png',
          plant: index == 0
              ? rosePrediction
              : const PredictionLabel(
                  code: 'marigold',
                  nameTh: 'ดาวเรือง',
                  nameEn: 'Marigold',
                  confidence: 0.94,
                ),
          margin: 0.2,
          accepted: false,
          reasons: inconsistent ? const [] : const ['low_margin'],
        ),
    ],
    reasons: inconsistent ? const ['inconsistent_plant'] : const ['low_margin'],
  );
}

XFile testImage(String name) {
  final bytes = Uint8List.fromList(
    base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC'
      'AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
    ),
  );
  return XFile.fromData(bytes, path: name, name: name, mimeType: 'image/png');
}

class QueueApi implements PhytoScanApi {
  QueueApi(this.responses);

  final List<Object> responses;
  final List<String?> plantCodes = [];
  final List<List<String>> imageBatches = [];

  @override
  Future<List<Plant>> fetchPlants() async => const [rose];

  @override
  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  }) async {
    plantCodes.add(plantCode);
    imageBatches.add(images.map((image) => image.path).toList());
    final response = responses.removeAt(0);
    if (response is ApiException) throw response;
    return response as AnalyzeOutcome;
  }
}

class MemoryHistoryStore implements ScanHistoryRepository {
  final entries = <ScanHistoryEntry>[];

  @override
  Future<void> add(ScanHistoryEntry entry) async => entries.insert(0, entry);

  @override
  Future<void> clear() async => entries.clear();

  @override
  Future<void> delete(String id) async {
    entries.removeWhere((entry) => entry.id == id);
  }

  @override
  Future<List<ScanHistoryEntry>> load() async => List.unmodifiable(entries);
}

Future<void> pumpAnalyze(
  WidgetTester tester,
  PhytoScanApi api,
  List<XFile> images, {
  Plant? plant,
  ScanHistoryRepository? historyStore,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light,
      home: AnalyzeScreen(
        api: api,
        plant: plant,
        initialImages: images,
        historyStore: historyStore ?? MemoryHistoryStore(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> submit(WidgetTester tester) async {
  final button = find.text('วิเคราะห์ด้วย PhytoScan');
  await tester.ensureVisible(button);
  await tester.tap(button);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('redesigned scan shows empty state and disabled sticky CTA', (
    tester,
  ) async {
    await pumpAnalyze(tester, QueueApi([]), const []);

    expect(find.text('ตรวจสุขภาพต้นไม้'), findsOneWidget);
    expect(find.text('สูงสุด 3 ภาพ'), findsOneWidget);
    expect(find.byKey(const ValueKey('scan-empty-upload')), findsOneWidget);
    expect(
      find.byKey(const ValueKey('scan-empty-selected-images')),
      findsOneWidget,
    );
    expect(find.text('เลือกภาพก่อนเริ่มวิเคราะห์'), findsOneWidget);
    final cta = tester.widget<FilledButton>(
      find.byKey(const ValueKey('analyze-submit')),
    );
    expect(cta.onPressed, isNull);
  });

  testWidgets('selected images show previews and can be removed', (
    tester,
  ) async {
    await pumpAnalyze(tester, QueueApi([]), [
      testImage('one.png'),
      testImage('two.png'),
    ]);

    expect(find.byKey(const ValueKey('scan-main-preview')), findsOneWidget);
    expect(find.byKey(const ValueKey('scan-thumbnail-0')), findsOneWidget);
    expect(find.byKey(const ValueKey('scan-thumbnail-1')), findsOneWidget);
    expect(find.text('2/3 ภาพ'), findsOneWidget);
    expect(find.text('วิเคราะห์ด้วย PhytoScan'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('remove-image-0')),
      260,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('remove-image-0')));
    await tester.pumpAndSettle();
    expect(find.text('1/3 ภาพ'), findsOneWidget);
  });

  testWidgets('scan layout does not overflow at 320x568 and 130 percent text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 1.3;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      tester.platformDispatcher.clearTextScaleFactorTestValue();
    });

    await pumpAnalyze(tester, QueueApi([]), const []);
    expect(tester.takeException(), isNull);
    expect(find.text('เลือกภาพก่อนเริ่มวิเคราะห์'), findsOneWidget);
  });

  testWidgets('automatic flow submits without plant code and shows source', (
    tester,
  ) async {
    final api = QueueApi([completed(1)]);
    await pumpAnalyze(tester, api, [testImage('one.png')]);

    await submit(tester);

    expect(api.plantCodes, [null]);
    expect(find.text('ระบุชนิดพืชจากภาพถ่ายโดยระบบ'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
  });

  testWidgets('completed analysis is added to local scan history', (
    tester,
  ) async {
    final history = MemoryHistoryStore();
    await pumpAnalyze(tester, QueueApi([completed(1)]), [
      testImage('one.png'),
    ], historyStore: history);

    await submit(tester);

    expect(history.entries, hasLength(1));
    expect(history.entries.single.plantName, 'กุหลาบ');
    expect(history.entries.single.imageCount, 1);
    expect(history.entries.single.manuallyConfirmed, isFalse);
  });

  testWidgets('manual confirmation resubmits the same images with plant code', (
    tester,
  ) async {
    final api = QueueApi([manual(), completed(1)]);
    await pumpAnalyze(tester, api, [testImage('one.png')]);

    await submit(tester);
    expect(find.text('ต้องยืนยันชนิดพืชก่อน'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
    await tester.tap(find.text('ยืนยันว่าเป็นกุหลาบ'));
    await tester.pumpAndSettle();

    expect(api.plantCodes, [null, 'rose']);
    expect(api.imageBatches, [
      ['one.png'],
      ['one.png'],
    ]);
    expect(find.text('ชนิดพืชนี้ได้รับการยืนยันโดยผู้ใช้'), findsOneWidget);
  });

  testWidgets('inconsistent plants can only return to edit the image set', (
    tester,
  ) async {
    final api = QueueApi([
      manual(inconsistent: true),
      manual(inconsistent: true),
    ]);
    await pumpAnalyze(tester, api, [
      testImage('one.png'),
      testImage('two.png'),
    ]);

    await submit(tester);

    expect(find.text('ภาพอาจเป็นพืชต่างชนิดกัน'), findsOneWidget);
    expect(find.textContaining('ยืนยันว่าเป็น'), findsNothing);
    await tester.tap(find.text('กลับไปแก้ไขชุดภาพ'));
    await tester.pumpAndSettle();
    await submit(tester);
    expect(find.text('ภาพอาจเป็นพืชต่างชนิดกัน'), findsOneWidget);
    expect(api.plantCodes, [null, null]);
    expect(api.imageBatches, [
      ['one.png', 'two.png'],
      ['one.png', 'two.png'],
    ]);
  });

  testWidgets('retry keeps selected images after a network error', (
    tester,
  ) async {
    final api = QueueApi([
      const ApiException(errorCode: 'NETWORK_ERROR', message: 'offline'),
      completed(1),
    ]);
    await pumpAnalyze(tester, api, [testImage('one.png')]);

    await submit(tester);
    expect(find.byKey(const ValueKey('analyze-error')), findsOneWidget);
    expect(
      find.text('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ต'),
      findsOneWidget,
    );
    await submit(tester);
    expect(api.plantCodes, [null, null]);
    expect(api.imageBatches, [
      ['one.png'],
      ['one.png'],
    ]);
    expect(find.text('ผลการวิเคราะห์'), findsOneWidget);
  });

  testWidgets('loading state prevents double submit', (tester) async {
    final completer = Completer<AnalyzeOutcome>();
    final api = _CompleterApi(completer);
    await pumpAnalyze(tester, api, [testImage('one.png')]);

    final button = find.text('วิเคราะห์ด้วย PhytoScan');
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pump();
    await tester.tap(button, warnIfMissed: false);
    await tester.pump();
    expect(api.calls, 1);

    completer.complete(completed(1));
    await tester.pumpAndSettle();
  });
}

class _CompleterApi implements PhytoScanApi {
  _CompleterApi(this.completer);

  final Completer<AnalyzeOutcome> completer;
  int calls = 0;

  @override
  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  }) {
    calls++;
    return completer.future;
  }

  @override
  Future<List<Plant>> fetchPlants() async => const [rose];
}
