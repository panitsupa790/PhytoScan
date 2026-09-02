import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/services/analysis_api_service.dart';

const runApiIntegration = bool.fromEnvironment('RUN_API_INTEGRATION');

void main() {
  test(
    'uploads a real PNG to the running FastAPI backend',
    () async {
      const service = AnalysisApiService(baseUrl: 'http://127.0.0.1:8000');

      final result = await service.analyze([XFile('web/favicon.png')]);

      expect(result.success, isTrue);
      expect(result.imageCount, 1);
      expect(result.plant.code, isNotEmpty);
      expect(result.disease.code, isNotEmpty);
    },
    skip: runApiIntegration ? false : 'Requires a local FastAPI server.',
  );
}
