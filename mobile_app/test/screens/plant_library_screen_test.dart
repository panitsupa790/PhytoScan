import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/plant_library.dart';
import 'package:mobile_app/screens/plant_library_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/theme/app_theme.dart';

class _PlantLibraryApi implements PlantLibraryApi {
  const _PlantLibraryApi();

  @override
  Future<List<PlantLibrarySummary>> fetchPlantLibrary() async => const [
    PlantLibrarySummary(
      plantCode: 'rose',
      nameTh: 'กุหลาบ',
      nameEn: 'Rose',
      scientificName: 'Rosa spp.',
      summaryTh: 'ไม้พุ่มดอกที่มีหลายสายพันธุ์',
      coverImage: 'https://example.invalid/rose.jpg',
      coverAltTextTh: 'ภาพกุหลาบ',
      supportedDiseaseCount: 8,
      reviewStatus: 'needs_expert_review',
    ),
    PlantLibrarySummary(
      plantCode: 'marigold',
      nameTh: 'ดาวเรือง',
      nameEn: 'Marigold',
      scientificName: 'Tagetes erecta',
      summaryTh: 'ไม้ดอกสีเหลืองถึงส้ม',
      coverImage: 'https://example.invalid/marigold.jpg',
      coverAltTextTh: 'ภาพดาวเรือง',
      supportedDiseaseCount: 3,
      reviewStatus: 'needs_expert_review',
    ),
  ];

  @override
  Future<PlantLibraryDetail> fetchPlantLibraryDetail(String plantCode) {
    throw UnimplementedError();
  }
}

void main() {
  testWidgets('lists, searches, and opens a plant library entry', (
    tester,
  ) async {
    PlantLibrarySummary? opened;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: PlantLibraryScreen(
            api: const _PlantLibraryApi(),
            onOpenPlant: (plant) => opened = plant,
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.byKey(const ValueKey('plantLibrary-rose')), findsOneWidget);
    expect(find.byKey(const ValueKey('plantLibrary-marigold')), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('plantLibrarySearch')),
      'Tagetes',
    );
    await tester.pump();
    expect(find.byKey(const ValueKey('plantLibrary-rose')), findsNothing);
    expect(find.byKey(const ValueKey('plantLibrary-marigold')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('plantLibrary-marigold')));
    expect(opened?.plantCode, 'marigold');
  });
}
