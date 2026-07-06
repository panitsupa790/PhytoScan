import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  void _showComingSoon(BuildContext context) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text('ฟีเจอร์นี้กำลังพัฒนา')));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFDFF1D8), Color(0xFFF4F8F1)],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 12),
                Container(
                  width: 88,
                  height: 88,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE6F4DF),
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: const Icon(
                    Icons.eco_rounded,
                    size: 44,
                    color: Color(0xFF2F6B1F),
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  'PhytoScan',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: const Color(0xFF214D18),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'วิเคราะห์โรคพืชจากภาพ',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: const Color(0xFF3D6B35),
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'อัปโหลดภาพใบพืชเพื่อให้ระบบตรวจชนิดพืชและประเมินโรคให้อัตโนมัติ',
                  style: theme.textTheme.bodyLarge?.copyWith(
                    height: 1.5,
                    color: const Color(0xFF55734E),
                  ),
                ),
                const SizedBox(height: 28),
                FilledButton.icon(
                  onPressed: () => _showComingSoon(context),
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF3F7F2B),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: const Text(
                    'ถ่ายภาพ',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                ),
                const SizedBox(height: 14),
                OutlinedButton.icon(
                  onPressed: () => _showComingSoon(context),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF2F6B1F),
                    side: const BorderSide(color: Color(0xFF8DBA7A)),
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text(
                    'เลือกจากแกลเลอรี',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.82),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: const Color(0xFFD3E5C8)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.tips_and_updates_outlined,
                            color: Color(0xFF4F8A39),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            'คำแนะนำการถ่ายภาพ',
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: const Color(0xFF2D5B24),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'ถ่ายภาพใบพืชให้ชัด แสงเพียงพอ และมีพืชชนิดเดียวในภาพ',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          height: 1.5,
                          color: const Color(0xFF4F6847),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
