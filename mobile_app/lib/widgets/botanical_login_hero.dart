import 'package:flutter/material.dart';

import '../theme/login_design_tokens.dart';

class BotanicalLoginHero extends StatelessWidget {
  const BotanicalLoginHero({super.key});

  @override
  Widget build(BuildContext context) {
    final textScaler = MediaQuery.textScalerOf(context);
    final largeText = textScaler.scale(16) > 21;

    return Semantics(
      header: true,
      label: 'PhytoScan ผู้ช่วยดูแลสุขภาพพืช',
      child: Stack(
        fit: StackFit.expand,
        children: [
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [LoginColors.heroTop, LoginColors.heroBottom],
                stops: [0.05, 1],
              ),
            ),
          ),
          Positioned(
            right: -72,
            top: -86,
            child: Container(
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  colors: [
                    LoginColors.accentGreen.withValues(alpha: 0.16),
                    LoginColors.accentGreen.withValues(alpha: 0),
                  ],
                ),
                shape: BoxShape.circle,
              ),
            ),
          ),
          const CustomPaint(painter: _BotanicalLeafPainter()),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 14, 24, 54),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: LoginColors.white.withValues(alpha: 0.13),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: LoginColors.white.withValues(alpha: 0.2),
                        ),
                      ),
                      child: const Icon(
                        Icons.eco_rounded,
                        color: LoginColors.accentGreen,
                        size: 25,
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'PhytoScan',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: LoginColors.white,
                              fontSize: 21,
                              height: 1.1,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.3,
                            ),
                          ),
                          SizedBox(height: 3),
                          Text(
                            'ผู้ช่วยดูแลสุขภาพพืชของคุณ',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Color(0xFFC9D4C5),
                              fontSize: 13,
                              height: 1.3,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                SizedBox(height: largeText ? 13 : 18),
                Text.rich(
                  TextSpan(
                    children: [
                      const TextSpan(text: 'เติบโตไปด้วยกัน\n'),
                      TextSpan(
                        text: 'เริ่มต้นที่นี่',
                        style: const TextStyle(
                          color: LoginColors.accentGreen,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  style: TextStyle(
                    color: LoginColors.white,
                    fontSize: largeText ? 28 : 32,
                    height: 1.15,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.6,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 10),
                const Text(
                  'เข้าสู่ระบบเพื่อบันทึกการตรวจสุขภาพพืชและติดตามประวัติของคุณ',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: Color(0xFFDCE4D9),
                    fontSize: 14,
                    height: 1.42,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BotanicalLeafPainter extends CustomPainter {
  const _BotanicalLeafPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final stem = Paint()
      ..color = LoginColors.accentGreen.withValues(alpha: 0.24)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.1
      ..strokeCap = StrokeCap.round;
    final leaf = Paint()
      ..color = LoginColors.accentGreen.withValues(alpha: 0.13)
      ..style = PaintingStyle.fill;
    final vein = Paint()
      ..color = LoginColors.accentGreen.withValues(alpha: 0.18)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final origin = Offset(size.width * 0.87, size.height * 1.04);
    final tip = Offset(size.width * 0.69, size.height * 0.06);
    final stemPath = Path()
      ..moveTo(origin.dx, origin.dy)
      ..quadraticBezierTo(
        size.width * 0.82,
        size.height * 0.54,
        tip.dx,
        tip.dy,
      );
    canvas.drawPath(stemPath, stem);

    _drawLeaf(
      canvas,
      center: Offset(size.width * 0.78, size.height * 0.34),
      width: size.width * 0.25,
      height: size.height * 0.22,
      rotation: -0.55,
      fill: leaf,
      vein: vein,
    );
    _drawLeaf(
      canvas,
      center: Offset(size.width * 0.85, size.height * 0.54),
      width: size.width * 0.27,
      height: size.height * 0.23,
      rotation: 0.53,
      fill: leaf,
      vein: vein,
    );
    _drawLeaf(
      canvas,
      center: Offset(size.width * 0.72, size.height * 0.72),
      width: size.width * 0.25,
      height: size.height * 0.2,
      rotation: -0.38,
      fill: leaf,
      vein: vein,
    );

    canvas.drawCircle(
      Offset(size.width * 0.92, size.height * 0.18),
      5,
      Paint()..color = LoginColors.orangeHighlight.withValues(alpha: 0.65),
    );
  }

  void _drawLeaf(
    Canvas canvas, {
    required Offset center,
    required double width,
    required double height,
    required double rotation,
    required Paint fill,
    required Paint vein,
  }) {
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(rotation);
    final path = Path()
      ..moveTo(-width / 2, 0)
      ..quadraticBezierTo(0, -height / 2, width / 2, 0)
      ..quadraticBezierTo(0, height / 2, -width / 2, 0)
      ..close();
    canvas.drawPath(path, fill);
    canvas.drawLine(Offset(-width / 2, 0), Offset(width / 2, 0), vein);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _BotanicalLeafPainter oldDelegate) => false;
}
