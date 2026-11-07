import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/main.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/models/plant.dart';
import 'package:mobile_app/services/api_service.dart';

class _HomeApi implements PhytoScanApi {
  const _HomeApi();

  static const plants = [
    Plant(
      code: 'chrysanthemum',
      nameTh: 'เบญจมาศ',
      nameEn: 'Chrysanthemum',
      diseaseCount: 4,
    ),
    Plant(
      code: 'marigold',
      nameTh: 'ดาวเรือง',
      nameEn: 'Marigold',
      diseaseCount: 3,
    ),
    Plant(
      code: 'money_plant',
      nameTh: 'พลูด่าง',
      nameEn: 'Money Plant',
      diseaseCount: 2,
    ),
    Plant(code: 'rose', nameTh: 'กุหลาบ', nameEn: 'Rose', diseaseCount: 8),
    Plant(
      code: 'snake_plant',
      nameTh: 'ลิ้นมังกร',
      nameEn: 'Snake Plant',
      diseaseCount: 3,
    ),
    Plant(
      code: 'spider_plant',
      nameTh: 'เศรษฐีเรือนใน',
      nameEn: 'Spider Plant',
      diseaseCount: 2,
    ),
  ];

  @override
  Future<List<Plant>> fetchPlants() async => plants;

  @override
  Future<AnalyzeOutcome> analyze({
    String? plantCode,
    required List<XFile> images,
  }) {
    throw UnimplementedError();
  }
}

void main() {
  Future<void> pumpHome(WidgetTester tester) async {
    await tester.pumpWidget(const MyApp(api: _HomeApi(), startAtHome: true));
    await tester.pumpAndSettle();
  }

  testWidgets(
    'uses the live plant catalogue for count and Thai/English search',
    (tester) async {
      await pumpHome(tester);

      expect(find.text('6 ชนิด'), findsOneWidget);
      expect(find.text('เริ่มดูแลต้นไม้'), findsNothing);
      expect(find.text('ตรวจสุขภาพต้นไม้'), findsNothing);
      expect(find.byKey(const ValueKey('supportedPlant-rose')), findsOneWidget);
      expect(find.textContaining('Sunflower'), findsNothing);

      await tester.enterText(
        find.byKey(const Key('plantSearchField')),
        'Marigold',
      );
      await tester.pump();
      expect(
        find.byKey(const ValueKey('supportedPlant-marigold')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('supportedPlant-rose')), findsNothing);

      await tester.enterText(find.byKey(const Key('plantSearchField')), 'ลิ้น');
      await tester.pump();
      expect(
        find.byKey(const ValueKey('supportedPlant-snake_plant')),
        findsOneWidget,
      );

      await tester.enterText(
        find.byKey(const Key('plantSearchField')),
        'ไม่รองรับ',
      );
      await tester.pump();
      expect(find.text('ไม่พบพืชที่ค้นหา'), findsOneWidget);
    },
  );

  testWidgets('keeps automatic identification and manual diagnosis separate', (
    tester,
  ) async {
    await pumpHome(tester);

    final identify = find.byKey(const Key('identifyPlantButton'));
    await tester.ensureVisible(identify);
    await tester.tap(identify);
    await tester.pumpAndSettle();
    expect(find.text('จำแนกชนิดพืชอัตโนมัติ'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    final diagnose = find.byKey(const Key('diagnosePlantButton'));
    await tester.scrollUntilVisible(
      diagnose,
      220,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(diagnose);
    await tester.pumpAndSettle();
    expect(find.text('คุณกำลังตรวจพืชอะไร?'), findsOneWidget);
    expect(find.text('ดาวเรือง'), findsOneWidget);
  });

  testWidgets('photography guidance reflects controlled-background scope', (
    tester,
  ) async {
    await pumpHome(tester);

    final tips = find.byKey(const Key('photographyTipsButton'));
    await tester.scrollUntilVisible(
      tips,
      260,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(tips);
    await tester.pumpAndSettle();

    expect(find.text('ถ่ายภาพให้พร้อมวิเคราะห์'), findsOneWidget);
    expect(find.text('ใช้พื้นหลังเรียบ'), findsOneWidget);
    expect(find.text('หนึ่งชนิดต่อหนึ่งชุดภาพ'), findsOneWidget);
    expect(find.textContaining('ภาพใบพืชที่มีพื้นหลังเรียบ'), findsOneWidget);
  });

  testWidgets('profile shortcut preserves the five-tab navigation', (
    tester,
  ) async {
    await pumpHome(tester);

    await tester.tap(find.byKey(const Key('homeProfileButton')));
    await tester.pumpAndSettle();
    expect(find.text('รองรับพืช 6 ชนิด'), findsOneWidget);
    expect(find.text('หน้าหลัก'), findsOneWidget);
    expect(find.byKey(const Key('floatingScanButton')), findsOneWidget);
    expect(find.text('สแกน'), findsNothing);
    expect(find.text('ประวัติ'), findsOneWidget);
    expect(find.text('โปรไฟล์'), findsWidgets);
  });

  testWidgets('scan button floats across the bar and all five actions work', (
    tester,
  ) async {
    await pumpHome(tester);

    final bar = tester.getRect(
      find.byKey(const Key('bottomNavigationSurface')),
    );
    final scanButton = tester.getRect(
      find.byKey(const Key('floatingScanButton')),
    );
    final scanFace = tester.getRect(
      find.byKey(const Key('floatingScanButtonFace')),
    );
    expect(scanButton.width, 52);
    expect(scanButton.height, 52);
    expect(scanFace.width, 44);
    expect(scanFace.height, 44);
    expect(scanFace.top, lessThan(bar.top));
    expect((scanFace.center.dy - bar.top).abs(), lessThanOrEqualTo(6));
    final logicalWidth =
        tester.view.physicalSize.width / tester.view.devicePixelRatio;
    expect(scanFace.center.dx, closeTo(logicalWidth / 2, 1));
    expect(find.text('สแกน'), findsNothing);

    AnimatedOpacity indicator(String label) => tester.widget<AnimatedOpacity>(
      find.byKey(ValueKey('bottomNavIndicator-$label')),
    );
    expect(indicator('หน้าหลัก').opacity, 1);
    expect(indicator('คลังพืช').opacity, 0);

    await tester.tap(find.byKey(const ValueKey('bottomNav-คลังพืช')));
    await tester.pumpAndSettle();
    expect(find.text('คลังพืชยังไม่พร้อมใช้งาน'), findsOneWidget);
    expect(indicator('คลังพืช').opacity, 1);

    await tester.tapAt(Offset(scanButton.center.dx, bar.top - 8));
    await tester.pumpAndSettle();
    expect(find.text('จำแนกชนิดพืชอัตโนมัติ'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('bottomNav-ประวัติ')));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('ประวัติการสแกน'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('bottomNav-โปรไฟล์')));
    await tester.pumpAndSettle();
    expect(find.text('รองรับพืช 6 ชนิด'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('bottomNav-หน้าหลัก')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('plantSearchField')), findsOneWidget);
  });

  testWidgets('does not overflow at 320x568 with 130 percent text scale', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 1.3;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      tester.platformDispatcher.clearTextScaleFactorTestValue();
    });

    await pumpHome(tester);
    expect(tester.takeException(), isNull);

    await tester.tap(find.byKey(const Key('plantSearchField')));
    await tester.enterText(find.byKey(const Key('plantSearchField')), 'Rose');
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
