import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analyze_outcome.dart';
import 'package:mobile_app/models/plant.dart';
import 'package:mobile_app/screens/login_screen.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/theme/app_theme.dart';

class _FakeApi implements PhytoScanApi {
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

Widget _subject({double textScale = 1}) {
  return MaterialApp(
    theme: AppTheme.light,
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(
        context,
      ).copyWith(textScaler: TextScaler.linear(textScale)),
      child: child!,
    ),
    home: LoginScreen(api: _FakeApi()),
  );
}

void main() {
  testWidgets('renders the Botanical Premium login hierarchy', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_subject());

    expect(find.text('PhytoScan'), findsOneWidget);
    expect(find.text('เติบโตไปด้วยกัน\nเริ่มต้นที่นี่'), findsOneWidget);
    expect(find.text('ยินดีต้อนรับ'), findsOneWidget);
    expect(find.byKey(const Key('loginEmailField')), findsOneWidget);
    expect(find.byKey(const Key('loginPasswordField')), findsOneWidget);
    expect(find.byKey(const Key('registerSegment')), findsOneWidget);
    expect(find.byKey(const Key('guestButton')), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is AnnotatedRegion<SystemUiOverlayStyle> &&
            widget.value.statusBarIconBrightness == Brightness.light,
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('password visibility keeps the existing field state', (
    tester,
  ) async {
    await tester.pumpWidget(_subject());
    final password = find.byKey(const Key('loginPasswordField'));
    expect(tester.widget<TextField>(password).obscureText, isTrue);

    await tester.ensureVisible(
      find.byKey(const Key('passwordVisibilityButton')),
    );
    await tester.tap(find.byKey(const Key('passwordVisibilityButton')));
    await tester.pump();

    expect(tester.widget<TextField>(password).obscureText, isFalse);
    expect(find.byTooltip('ซ่อนรหัสผ่าน'), findsOneWidget);
  });

  testWidgets('unavailable account actions preserve the existing message', (
    tester,
  ) async {
    await tester.pumpWidget(_subject());

    await tester.ensureVisible(find.byKey(const Key('loginButton')));
    await tester.tap(find.byKey(const Key('loginButton')));
    await tester.pump();
    expect(
      find.text('ระบบบัญชียังไม่เปิดใช้งาน กรุณาใช้งานแบบผู้ใช้ทั่วไป'),
      findsOneWidget,
    );

    await tester.ensureVisible(find.byKey(const Key('registerSegment')));
    await tester.tap(find.byKey(const Key('registerSegment')));
    await tester.pump();
    expect(
      find.text('ระบบบัญชียังไม่เปิดใช้งาน กรุณาใช้งานแบบผู้ใช้ทั่วไป'),
      findsOneWidget,
    );
  });

  testWidgets('guest action still replaces login with home', (tester) async {
    await tester.pumpWidget(_subject());
    await tester.ensureVisible(find.byKey(const Key('guestButton')));
    await tester.tap(find.byKey(const Key('guestButton')));
    await tester.pumpAndSettle();

    expect(find.text('ระบุชนิดพืช'), findsOneWidget);
    expect(find.byType(LoginScreen), findsNothing);
  });

  testWidgets('small screen and enlarged Thai text remain scrollable', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_subject(textScale: 1.3));
    await tester.ensureVisible(find.byKey(const Key('guestButton')));
    await tester.pump();

    expect(find.byType(SingleChildScrollView), findsOneWidget);
    expect(find.byKey(const Key('guestButton')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
