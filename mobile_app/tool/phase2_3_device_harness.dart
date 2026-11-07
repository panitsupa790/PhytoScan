import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/models/plant.dart';
import 'package:mobile_app/screens/analyze_screen.dart';
import 'package:mobile_app/screens/plant_selection_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/theme/app_theme.dart';

const _assetPath = String.fromEnvironment(
  'PHASE23_ASSET_PATH',
  defaultValue: 'assets/images/ai_6a0e0c4ae130b_1779305546.jpg',
);
const _requestTimeoutMs = int.fromEnvironment(
  'PHASE23_REQUEST_TIMEOUT_MS',
  defaultValue: 90000,
);
const _startAtManualSelection = bool.fromEnvironment(
  'PHASE23_MANUAL_SELECTION',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final data = await rootBundle.load(_assetPath);
  final image = XFile.fromData(
    Uint8List.sublistView(data),
    path: 'phase-2-3-project-fixture.jpg',
    name: 'phase-2-3-project-fixture.jpg',
    mimeType: 'image/jpeg',
  );
  runApp(_Harness(image: image));
}

class _Harness extends StatelessWidget {
  const _Harness({required this.image});

  final XFile image;

  @override
  Widget build(BuildContext context) {
    const api = _MeasuredApi(
      ApiService(requestTimeout: Duration(milliseconds: _requestTimeoutMs)),
    );
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: _startAtManualSelection
          ? const PlantSelectionScreen(api: api)
          : AnalyzeScreen(api: api, initialImages: [image]),
    );
  }
}

class _MeasuredApi implements PhytoScanApi {
  const _MeasuredApi(this.delegate);

  final PhytoScanApi delegate;

  int? get _currentRss => kIsWeb ? null : ProcessInfo.currentRss;

  @override
  Future<List<Plant>> fetchPlants() => delegate.fetchPlants();

  @override
  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  }) async {
    final watch = Stopwatch()..start();
    final rssBefore = _currentRss;
    try {
      final outcome = await delegate.analyze(
        plantCode: plantCode,
        images: images,
      );
      watch.stop();
      final status = switch (outcome) {
        CompletedAnalyzeOutcome() => 'completed',
        ManualConfirmationOutcome() => 'manual_confirmation_required',
      };
      // Machine-readable evidence for the Phase 2.3 device run.
      // ignore: avoid_print
      print(
        'PHASE23_DEVICE_API status=$status plant_code=${plantCode ?? "automatic"} '
        'images=${images.length} elapsed_ms=${watch.elapsedMilliseconds} '
        'rss_before=$rssBefore rss_after=$_currentRss',
      );
      return outcome;
    } catch (error) {
      watch.stop();
      // ignore: avoid_print
      print(
        'PHASE23_DEVICE_API status=error plant_code=${plantCode ?? "automatic"} '
        'images=${images.length} elapsed_ms=${watch.elapsedMilliseconds} '
        'rss_before=$rssBefore rss_after=$_currentRss error=$error',
      );
      rethrow;
    }
  }
}
