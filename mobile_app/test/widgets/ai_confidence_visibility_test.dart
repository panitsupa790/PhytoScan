import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analyze_result.dart';
import 'package:mobile_app/screens/result_screen.dart';
import 'package:mobile_app/theme/app_theme.dart';
import 'package:mobile_app/widgets/diagnosis_result_card.dart';

XFile _image() {
  final bytes = Uint8List.fromList(
    base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC'
      'AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
    ),
  );
  return XFile.fromData(bytes, name: 'leaf.png', mimeType: 'image/png');
}

ImageResult _result({
  required String code,
  required String name,
  required double confidence,
}) {
  return ImageResult(
    index: 0,
    filename: 'leaf.png',
    disease: PredictionLabel(
      code: code,
      nameTh: '',
      nameEn: name,
      confidence: confidence,
    ),
    symptoms: const [],
    care: const [],
    prevention: const [],
  );
}

Future<void> _pumpCard(WidgetTester tester, ImageResult result) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(
        body: DiagnosisResultCard(
          image: _image(),
          result: result,
          onTap: () {},
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('disease result hides AI confidence', (tester) async {
    await _pumpCard(
      tester,
      _result(code: 'Rose_Rust', name: 'Rose Rust', confidence: 0.94),
    );

    expect(find.text('พบลักษณะที่อาจผิดปกติ'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
    expect(find.byType(LinearProgressIndicator), findsNothing);
  });

  testWidgets('healthy result uses a non-disease status without confidence', (
    tester,
  ) async {
    await _pumpCard(
      tester,
      _result(code: 'Rose_Healthy', name: 'Healthy Rose', confidence: 0.99),
    );

    expect(find.text('ภาพมีลักษณะสอดคล้องกับใบสุขภาพดี'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
  });

  testWidgets('unknown result does not claim an abnormality', (tester) async {
    await _pumpCard(
      tester,
      _result(code: 'unavailable', name: '', confidence: 0.0),
    );

    expect(find.text('ยังไม่มีผลวินิจฉัยพร้อมแสดง'), findsOneWidget);
    expect(find.text('ไม่พบข้อมูลผลวินิจฉัย'), findsOneWidget);
    expect(find.text('พบลักษณะที่อาจผิดปกติ'), findsNothing);
    expect(find.textContaining('%'), findsNothing);
  });

  testWidgets('empty result state remains clear without confidence', (
    tester,
  ) async {
    const result = AnalyzeResult(
      imageCount: 0,
      plant: PredictionLabel(
        code: 'rose',
        nameTh: 'กุหลาบ',
        nameEn: 'Rose',
        confidence: 0.91,
      ),
      disease: PredictionLabel(
        code: 'unavailable',
        nameTh: '',
        nameEn: '',
        confidence: 0.0,
      ),
      symptoms: [],
      care: [],
      prevention: [],
      imageResults: [],
    );
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: const ResultScreen(result: result, images: []),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('ไม่มีผลรายภาพสำหรับแสดงผล'), findsWidgets);
    expect(find.textContaining('%'), findsNothing);
  });
}
