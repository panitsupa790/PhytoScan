import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/main.dart';

void main() {
  testWidgets('shows PhytoScan home screen', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.text('PhytoScan'), findsOneWidget);
    expect(find.text('วิเคราะห์โรคพืชจากภาพ'), findsOneWidget);
    expect(find.text('ถ่ายภาพ'), findsOneWidget);
    expect(find.text('เลือกจากแกลเลอรี'), findsOneWidget);
    expect(
      find.text('ถ่ายภาพใบพืชให้ชัด แสงเพียงพอ และมีพืชชนิดเดียวในภาพ'),
      findsOneWidget,
    );
  });
}
