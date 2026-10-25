import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const rows = [
      (Icons.history_rounded, 'ประวัติการตรวจ', 'กำลังพัฒนา'),
      (Icons.notifications_none_rounded, 'การแจ้งเตือน', 'กำลังพัฒนา'),
      (Icons.memory_outlined, 'โมเดลที่รองรับ', 'Rose และ Sunflower'),
      (Icons.info_outline_rounded, 'เกี่ยวกับ PhytoScan', 'เวอร์ชัน 1.0.0'),
    ];
    return ListView(
      padding: const EdgeInsets.fromLTRB(22, 28, 22, 32),
      children: [
        Text('โปรไฟล์', style: Theme.of(context).textTheme.displaySmall),
        const SizedBox(height: 24),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: AppColors.divider, width: 0.6),
          ),
          child: Row(
            children: [
              Container(
                width: 54,
                height: 54,
                decoration: const BoxDecoration(
                  color: AppColors.paleGreen,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.person_outline_rounded,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(width: 14),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Guest', style: Theme.of(context).textTheme.titleLarge),
                  Text(
                    'ใช้งานโดยไม่เข้าสู่ระบบ',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        for (var index = 0; index < rows.length; index++) ...[
          ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 4),
            leading: Icon(rows[index].$1, color: AppColors.primary),
            title: Text(rows[index].$2),
            subtitle: Text(rows[index].$3),
          ),
          if (index < rows.length - 1) const Divider(indent: 48),
        ],
      ],
    );
  }
}
