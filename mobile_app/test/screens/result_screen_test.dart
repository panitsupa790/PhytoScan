import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/analysis_result.dart';
import 'package:mobile_app/screens/result_screen.dart';

const dynamicResult = AnalysisResult(
  success: true,
  imageCount: 2,
  plant: PlantPrediction(
    code: 'hibiscus',
    nameTh: 'ชบาทดสอบ',
    nameEn: 'Test Hibiscus',
    confidence: 0.91,
  ),
  disease: DiseasePrediction(
    code: 'test_disease',
    nameTh: 'โรคจาก API',
    nameEn: 'API Disease',
    confidence: 0.84,
  ),
  symptoms: ['อาการเฉพาะจาก API'],
  care: ['วิธีดูแลเฉพาะจาก API'],
  prevention: ['วิธีป้องกันเฉพาะจาก API'],
);

void main() {
  testWidgets('shows dynamic plant, disease, and confidence', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: ResultScreen(images: [], result: dynamicResult),
      ),
    );

    expect(find.text('ชบาทดสอบ (Test Hibiscus)'), findsOneWidget);
    expect(find.text('โรคจาก API (API Disease)'), findsOneWidget);
    expect(find.textContaining('84%'), findsWidgets);
    expect(find.text('91%'), findsOneWidget);
  });

  testWidgets('shows symptoms, care, and prevention from the model', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: ResultScreen(images: [], result: dynamicResult),
      ),
    );

    await tester.tap(find.text('อาการ'));
    await tester.pump();
    expect(find.text('อาการเฉพาะจาก API'), findsOneWidget);

    await tester.tap(find.text('การดูแล'));
    await tester.pump();
    expect(find.text('วิธีดูแลเฉพาะจาก API'), findsOneWidget);

    await tester.tap(find.text('การป้องกัน'));
    await tester.pump();
    expect(find.text('วิธีป้องกันเฉพาะจาก API'), findsOneWidget);
  });
}
