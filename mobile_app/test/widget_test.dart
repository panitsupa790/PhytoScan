import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/main.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/models/analyze_result.dart';
import 'package:mobile_app/models/plant.dart';
import 'package:mobile_app/screens/profile_screen.dart';
import 'package:mobile_app/screens/result_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/theme/app_theme.dart';
import 'package:mobile_app/widgets/diagnosis_result_card.dart';

class FakeApi implements PhytoScanApi {
  @override
  Future<List<Plant>> fetchPlants() async => const [
    Plant(code: 'rose', nameTh: 'กุหลาบ', nameEn: 'Rose', diseaseCount: 8),
    Plant(
      code: 'marigold',
      nameTh: 'ดาวเรือง',
      nameEn: 'Marigold',
      diseaseCount: 3,
    ),
  ];

  @override
  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  }) {
    throw UnimplementedError();
  }
}

const plantPrediction = PredictionLabel(
  code: 'rose',
  nameTh: 'กุหลาบ',
  nameEn: 'Rose',
  confidence: 1,
);

void main() {
  testWidgets('profile reflects the six-plant registry without sunflower', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const Scaffold(body: ProfileScreen()),
      ),
    );

    expect(find.text('รองรับพืช 6 ชนิด'), findsOneWidget);
    expect(find.textContaining('Sunflower'), findsNothing);
  });

  testWidgets('splash allows guest access without authentication', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(MyApp(api: FakeApi()));
    expect(find.text('รู้ทันอาการ ดูแลได้เร็วขึ้น'), findsOneWidget);

    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(find.text('ใช้งานแบบผู้ใช้ทั่วไป'), findsOneWidget);

    await tester.ensureVisible(find.text('ใช้งานแบบผู้ใช้ทั่วไป'));
    await tester.tap(find.text('ใช้งานแบบผู้ใช้ทั่วไป'));
    await tester.pumpAndSettle();
    expect(find.text('ระบุชนิดพืช'), findsOneWidget);
  });

  testWidgets(
    'home dashboard offers automatic scan and manual plant selection',
    (WidgetTester tester) async {
      await tester.pumpWidget(MyApp(api: FakeApi(), startAtHome: true));
      await tester.pumpAndSettle();

      expect(find.text('ระบุชนิดพืช'), findsOneWidget);
      expect(find.text('กุหลาบ'), findsOneWidget);
      expect(find.text('ตรวจโรคพืช'), findsOneWidget);

      await tester.tap(find.byKey(const Key('identifyPlantButton')));
      await tester.pumpAndSettle();
      expect(find.text('จำแนกชนิดพืชอัตโนมัติ'), findsOneWidget);

      await tester.pageBack();
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.byKey(const Key('diagnosePlantButton')),
        220,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('diagnosePlantButton')));
      await tester.pumpAndSettle();
      expect(find.text('คุณกำลังตรวจพืชอะไร?'), findsOneWidget);
      expect(find.text('ดาวเรือง'), findsOneWidget);
    },
  );

  testWidgets('result screen prioritizes one result per image', (
    WidgetTester tester,
  ) async {
    final bytes = Uint8List.fromList(
      base64Decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC'
        'AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
      ),
    );
    final images = [
      XFile.fromData(bytes, name: 'one.png', mimeType: 'image/png'),
      XFile.fromData(bytes, name: 'two.png', mimeType: 'image/png'),
    ];
    const rust = PredictionLabel(
      code: 'Rose_Rust',
      nameTh: '',
      nameEn: 'Rose Rust',
      confidence: 0.94,
    );
    const blackSpot = PredictionLabel(
      code: 'Rose_Black_Spot',
      nameTh: '',
      nameEn: 'Rose Black Spot',
      confidence: 0.72,
    );
    const result = AnalyzeResult(
      imageCount: 2,
      plant: plantPrediction,
      disease: rust,
      symptoms: [],
      care: [],
      prevention: [],
      imageResults: [
        ImageResult(
          index: 0,
          filename: 'one.png',
          disease: rust,
          symptoms: [],
          care: [],
          prevention: [],
        ),
        ImageResult(
          index: 1,
          filename: 'two.png',
          disease: blackSpot,
          symptoms: [],
          care: [],
          prevention: [],
        ),
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: ResultScreen(result: result, images: images),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Rose Rust'), findsOneWidget);
    expect(find.text('Rose Black Spot'), findsOneWidget);
    expect(find.byKey(const ValueKey('result-home-button')), findsOneWidget);
    expect(find.byKey(const ValueKey('analyze-again-button')), findsOneWidget);
    expect(find.text('ผลการวินิจฉัยเบื้องต้นจากภาพถ่าย'), findsWidgets);
    expect(find.textContaining('%'), findsNothing);
    expect(
      find.text('ผลจากภาพที่ส่งมามีความแตกต่างกัน กรุณาตรวจผลแต่ละภาพ'),
      findsOneWidget,
    );

    final firstResultCard = find.byType(DiagnosisResultCard).first;
    await Scrollable.ensureVisible(
      tester.element(firstResultCard),
      alignment: 0.35,
    );
    await tester.pumpAndSettle();
    await tester.tap(firstResultCard);
    await tester.pumpAndSettle();
    expect(find.text('รายละเอียดผลตรวจ'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('ผลการวินิจฉัยเบื้องต้นจากภาพถ่าย'),
      220,
    );
    expect(find.text('ผลการวินิจฉัยเบื้องต้นจากภาพถ่าย'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
    await tester.scrollUntilVisible(
      find.text('รายละเอียดสำหรับรายการนี้ยังไม่พร้อมใช้งาน'),
      180,
    );
    expect(
      find.text('รายละเอียดสำหรับรายการนี้ยังไม่พร้อมใช้งาน'),
      findsOneWidget,
    );
  });
}
