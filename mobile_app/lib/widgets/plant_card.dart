import 'package:flutter/material.dart';

import '../models/plant.dart';
import '../theme/app_theme.dart';
import 'plant_visual.dart';

class PlantCard extends StatelessWidget {
  const PlantCard({
    super.key,
    required this.plant,
    required this.onTap,
    this.compact = false,
  });

  final Plant plant;
  final VoidCallback onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: compact ? _compact(context) : _regular(context),
      ),
    );
  }

  Widget _regular(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Expanded(
          child: Padding(
            padding: EdgeInsets.all(8),
            child: PlantVisual(borderRadius: 17),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(plant.nameTh, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 6),
              Text(
                'รองรับ ${plant.diseaseCount} อาการ',
                style: Theme.of(
                  context,
                ).textTheme.labelMedium?.copyWith(color: AppColors.primary),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _compact(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(10),
      child: Row(
        children: [
          const SizedBox(
            width: 78,
            height: 78,
            child: PlantVisual(borderRadius: 16),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  plant.nameTh,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 5),
                Text(
                  'รองรับ ${plant.diseaseCount} อาการ',
                  style: Theme.of(
                    context,
                  ).textTheme.labelMedium?.copyWith(color: AppColors.primary),
                ),
              ],
            ),
          ),
          const Icon(
            Icons.chevron_right_rounded,
            color: AppColors.textSecondary,
          ),
        ],
      ),
    );
  }
}
