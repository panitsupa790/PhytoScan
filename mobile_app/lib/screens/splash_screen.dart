import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/api_service.dart';
import '../services/scan_history_store.dart';
import '../theme/login_design_tokens.dart';
import 'login_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({
    super.key,
    required this.api,
    this.historyStore = const ScanHistoryStore(),
  });

  final PhytoScanApi api;
  final ScanHistoryRepository historyStore;

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer(const Duration(milliseconds: 950), _continue);
  }

  void _continue() {
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder<void>(
        transitionDuration: const Duration(milliseconds: 320),
        pageBuilder: (_, _, _) =>
            LoginScreen(api: widget.api, historyStore: widget.historyStore),
        transitionsBuilder: (_, animation, _, child) =>
            FadeTransition(opacity: animation, child: child),
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: LoginColors.heroTop,
        body: Stack(
          fit: StackFit.expand,
          children: [
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [LoginColors.heroTop, LoginColors.heroBottom],
                ),
              ),
            ),
            const _BotanicalBackdrop(),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(28, 36, 28, 26),
                child: Column(
                  children: [
                    const Spacer(flex: 3),
                    TweenAnimationBuilder<double>(
                      tween: Tween(begin: 0.82, end: 1),
                      duration: const Duration(milliseconds: 650),
                      curve: Curves.easeOutBack,
                      builder: (context, scale, child) =>
                          Transform.scale(scale: scale, child: child),
                      child: const _BrandMark(),
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'PhytoScan',
                      style: TextStyle(
                        color: LoginColors.white,
                        fontSize: 34,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.8,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'รู้ทันอาการ ดูแลได้เร็วขึ้น',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: LoginColors.white.withValues(alpha: 0.76),
                        fontSize: 15,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 18),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 7,
                      ),
                      decoration: BoxDecoration(
                        color: LoginColors.white.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: LoginColors.white.withValues(alpha: 0.14),
                        ),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.auto_awesome_rounded,
                            color: LoginColors.accentGreen,
                            size: 15,
                          ),
                          SizedBox(width: 7),
                          Text(
                            'ผู้ช่วยดูแลพืชอัจฉริยะ',
                            style: TextStyle(
                              color: LoginColors.white,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.1,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Spacer(flex: 4),
                    const _LoadingIndicator(),
                    const SizedBox(height: 12),
                    Text(
                      'กำลังเตรียมระบบวิเคราะห์',
                      style: TextStyle(
                        color: LoginColors.white.withValues(alpha: 0.6),
                        fontSize: 11,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 94,
      height: 94,
      decoration: BoxDecoration(
        color: LoginColors.white,
        borderRadius: BorderRadius.circular(30),
        boxShadow: const [
          BoxShadow(
            color: Color(0x42000000),
            blurRadius: 30,
            offset: Offset(0, 14),
          ),
        ],
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: 62,
            height: 62,
            decoration: const BoxDecoration(
              color: LoginColors.segmentTrack,
              shape: BoxShape.circle,
            ),
          ),
          const Icon(
            Icons.eco_rounded,
            color: LoginColors.primaryGreen,
            size: 48,
          ),
          const Positioned(
            right: 19,
            top: 18,
            child: Icon(
              Icons.auto_awesome_rounded,
              color: LoginColors.orangeHighlight,
              size: 16,
            ),
          ),
        ],
      ),
    );
  }
}

class _BotanicalBackdrop extends StatelessWidget {
  const _BotanicalBackdrop();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Stack(
        children: [
          Positioned(
            right: -78,
            top: 42,
            child: Icon(
              Icons.eco_outlined,
              color: LoginColors.white.withValues(alpha: 0.07),
              size: 280,
            ),
          ),
          Positioned(
            left: -92,
            bottom: 48,
            child: Transform.rotate(
              angle: 0.55,
              child: Icon(
                Icons.spa_outlined,
                color: LoginColors.accentGreen.withValues(alpha: 0.08),
                size: 250,
              ),
            ),
          ),
          Positioned(
            left: 38,
            top: 90,
            child: Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(
                color: LoginColors.accentGreen.withValues(alpha: 0.65),
                shape: BoxShape.circle,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LoadingIndicator extends StatelessWidget {
  const _LoadingIndicator();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 120,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(99),
        child: const LinearProgressIndicator(
          minHeight: 3,
          backgroundColor: Color(0x2EFFFFFF),
          color: LoginColors.accentGreen,
        ),
      ),
    );
  }
}
