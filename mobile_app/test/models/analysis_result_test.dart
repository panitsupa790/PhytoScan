import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/analysis_result.dart';

void main() {
  test('parses a successful analysis response', () {
    final result = AnalysisResult.fromJson({
      'success': true,
      'image_count': 2,
      'plant': {
        'code': 'hibiscus',
        'name_th': 'ชบา',
        'name_en': 'Hibiscus',
        'confidence': 0.94,
      },
      'disease': {
        'code': 'rust',
        'name_th': 'โรคราสนิม',
        'name_en': 'Rust',
        'confidence': 0.84,
      },
      'symptoms': ['อาการจาก API'],
      'care': ['การดูแลจาก API'],
      'prevention': ['การป้องกันจาก API'],
    });

    expect(result.success, isTrue);
    expect(result.imageCount, 2);
    expect(result.plant.nameTh, 'ชบา');
    expect(result.disease.nameEn, 'Rust');
    expect(result.disease.confidence, 0.84);
    expect(result.symptoms, ['อาการจาก API']);
    expect(result.care, ['การดูแลจาก API']);
    expect(result.prevention, ['การป้องกันจาก API']);
  });

  test('rejects confidence outside zero to one', () {
    expect(
      () => AnalysisResult.fromJson({
        'success': true,
        'image_count': 1,
        'plant': {
          'code': 'hibiscus',
          'name_th': 'ชบา',
          'name_en': 'Hibiscus',
          'confidence': 1.2,
        },
        'disease': {
          'code': 'rust',
          'name_th': 'โรคราสนิม',
          'name_en': 'Rust',
          'confidence': 0.84,
        },
        'symptoms': <String>[],
        'care': <String>[],
        'prevention': <String>[],
      }),
      throwsFormatException,
    );
  });
}
