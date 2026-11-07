import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/analyze_outcome.dart';

Map<String, dynamic> prediction(String code, double confidence) => {
  'code': code,
  'name_th': '',
  'name_en': code,
  'confidence': confidence,
};

void main() {
  test(
    'parses completed outcome without changing the existing result model',
    () {
      final outcome = AnalyzeOutcome.fromJson({
        'success': true,
        'status': 'completed',
        'image_count': 1,
        'plant': prediction('rose', 0.95),
        'disease': prediction('Rose_Rust', 0.87),
        'symptoms': <String>[],
        'care': <String>[],
        'prevention': <String>[],
        'image_results': [
          {
            'index': 0,
            'filename': 'leaf.jpg',
            'disease': prediction('Rose_Rust', 0.87),
            'symptoms': <String>[],
            'care': <String>[],
            'prevention': <String>[],
          },
        ],
      });

      expect(outcome, isA<CompletedAnalyzeOutcome>());
      final completed = outcome as CompletedAnalyzeOutcome;
      expect(completed.result.plant.code, 'rose');
      expect(completed.result.imageResults.single.index, 0);
    },
  );

  test('parses manual confirmation and inconsistent plant state', () {
    final outcome = AnalyzeOutcome.fromJson({
      'success': false,
      'status': 'manual_confirmation_required',
      'message': 'confirm',
      'suggested_plant': null,
      'image_predictions': [
        {
          'index': 0,
          'filename': 'one.jpg',
          'plant': prediction('rose', 0.98),
          'margin': 0.9,
          'accepted': false,
          'reasons': <String>[],
        },
        {
          'index': 1,
          'filename': 'two.jpg',
          'plant': prediction('marigold', 0.97),
          'margin': 0.88,
          'accepted': false,
          'reasons': <String>[],
        },
      ],
      'reasons': ['inconsistent_plant'],
    });

    expect(outcome, isA<ManualConfirmationOutcome>());
    final manual = outcome as ManualConfirmationOutcome;
    expect(manual.hasInconsistentPlants, isTrue);
    expect(manual.suggestedPlant, isNull);
    expect(manual.imagePredictions.map((row) => row.index), [0, 1]);
  });

  test('rejects unknown response status', () {
    expect(
      () => AnalyzeOutcome.fromJson({'status': 'unknown'}),
      throwsFormatException,
    );
  });
}
