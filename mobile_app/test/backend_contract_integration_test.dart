import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/services/api_service.dart';

const runBackendIntegration = bool.fromEnvironment('RUN_BACKEND_INTEGRATION');

void main() {
  test(
    'real backend supports six plants and automatic/manual analysis contract',
    () async {
      const api = ApiService(
        baseUrl: String.fromEnvironment(
          'API_BASE_URL',
          defaultValue: 'http://127.0.0.1:8000',
        ),
      );
      final plants = await api.fetchPlants();
      expect(plants.map((plant) => plant.code), [
        'chrysanthemum',
        'marigold',
        'money_plant',
        'rose',
        'snake_plant',
        'spider_plant',
      ]);
      expect(plants.any((plant) => plant.code == 'sunflower'), isFalse);

      final source = File('assets/images/ai_6a0e0c4ae130b_1779305546.jpg');
      expect(await source.exists(), isTrue);
      final image = XFile(
        source.path,
        name: 'integration-leaf.jpg',
        mimeType: 'image/jpeg',
      );
      final automatic = await api.analyze(images: [image]);
      switch (automatic) {
        case CompletedAnalyzeOutcome(:final result):
          expect(result.imageCount, 1);
          expect(result.imageResults.single.index, 0);
        case ManualConfirmationOutcome(:final suggestedPlant):
          expect(suggestedPlant, isNotNull);
          final confirmed = await api.analyze(
            plantCode: suggestedPlant!.code,
            images: [image],
          );
          expect(confirmed, isA<CompletedAnalyzeOutcome>());
      }
    },
    skip: runBackendIntegration
        ? false
        : 'Set RUN_BACKEND_INTEGRATION=true and start the backend',
  );
}
