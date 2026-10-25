import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class ResultSection extends StatelessWidget {
  const ResultSection({super.key, required this.title, required this.items});

  final String title;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        if (items.isEmpty)
          Text(
            'รายละเอียดสำหรับรายการนี้ยังไม่พร้อมใช้งาน',
            style: Theme.of(context).textTheme.bodyMedium,
          )
        else
          for (final item in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.only(top: 9),
                    decoration: const BoxDecoration(
                      color: AppColors.primary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Text(item)),
                ],
              ),
            ),
      ],
    );
  }
}
