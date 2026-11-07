import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/models/plant.dart';
import 'package:mobile_app/models/scan_history_entry.dart';
import 'package:mobile_app/screens/home_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/scan_history_store.dart';
import 'package:mobile_app/theme/app_theme.dart';

class _Api implements PhytoScanApi {
  @override
  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<List<Plant>> fetchPlants() async => const [];
}

class _History implements ScanHistoryRepository {
  final entries = <ScanHistoryEntry>[
    ScanHistoryEntry(
      id: 'one',
      analyzedAt: DateTime(2026, 10, 31, 14, 30),
      plantCode: 'rose',
      plantName: 'กุหลาบ',
      plantConfidence: 0.95,
      diseaseCode: 'Rose_Rust',
      diseaseName: 'โรคราสนิมกุหลาบ',
      diseaseConfidence: 0.87,
      diseaseNames: const ['โรคราสนิมกุหลาบ'],
      imageCount: 1,
      manuallyConfirmed: false,
    ),
  ];

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

void main() {
  testWidgets('history tab shows locally stored scan summaries', (
    tester,
  ) async {
    final history = _History();
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: HomeScreen(api: _Api(), historyStore: history),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('ประวัติ'));
    await tester.pumpAndSettle();

    expect(find.text('ประวัติการสแกน'), findsOneWidget);
    expect(find.text('กุหลาบ'), findsOneWidget);
    expect(find.text('โรคราสนิมกุหลาบ'), findsOneWidget);
    expect(find.text('1 ภาพ'), findsOneWidget);
    expect(find.textContaining('%'), findsNothing);
    expect(find.byType(LinearProgressIndicator), findsNothing);
  });
}
