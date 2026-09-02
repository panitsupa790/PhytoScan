import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analysis_result.dart';
import 'package:mobile_app/screens/analyzing_screen.dart';
import 'package:mobile_app/services/analysis_api_service.dart';

const testResult = AnalysisResult(
  success: true,
  imageCount: 1,
  plant: PlantPrediction(
    code: 'snake_plant',
    nameTh: 'ลิ้นมังกรจาก API',
    nameEn: 'Snake Plant',
    confidence: 0.9,
  ),
  disease: DiseasePrediction(
    code: 'root_rot',
    nameTh: 'โรครากเน่าจาก API',
    nameEn: 'Root Rot',
    confidence: 0.8,
  ),
  symptoms: [],
  care: [],
  prevention: [],
);

void main() {
  final images = [XFile('web/favicon.png')];

  testWidgets('navigates to dynamic result after service success', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: AnalyzingScreen(
          images: images,
          analysisService: SuccessfulAnalysisService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('ลิ้นมังกรจาก API (Snake Plant)'), findsOneWidget);
    expect(find.text('โรครากเน่าจาก API (Root Rot)'), findsOneWidget);
  });

  testWidgets('shows error message and lets the user retry', (tester) async {
    final service = FailingAnalysisService();
    await tester.pumpWidget(
      MaterialApp(
        home: AnalyzingScreen(images: images, analysisService: service),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('วิเคราะห์ภาพไม่สำเร็จ'), findsOneWidget);
    expect(
      find.text(
        'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาตรวจสอบการเชื่อมต่อแล้วลองใหม่',
      ),
      findsOneWidget,
    );
    expect(find.text('ลองวิเคราะห์อีกครั้ง'), findsOneWidget);
    expect(find.text('กลับไปเลือกภาพใหม่'), findsOneWidget);

    final retryButton = find.text('ลองวิเคราะห์อีกครั้ง');
    await tester.ensureVisible(retryButton);
    await tester.pump();
    await tester.tap(retryButton);
    await tester.pump();
    await tester.pump();
    expect(service.callCount, 2);
  });
}

class SuccessfulAnalysisService implements AnalysisService {
  @override
  Future<AnalysisResult> analyze(List<XFile> images) async => testResult;
}

class FailingAnalysisService implements AnalysisService {
  int callCount = 0;

  @override
  Future<AnalysisResult> analyze(List<XFile> images) async {
    callCount++;
    throw const AnalysisApiException(
      errorCode: 'NETWORK_ERROR',
      userMessage:
          'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาตรวจสอบการเชื่อมต่อแล้วลองใหม่',
    );
  }
}
