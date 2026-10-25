import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class PlantVisual extends StatelessWidget {
  const PlantVisual({
    super.key,
    this.height,
    this.iconSize = 54,
    this.borderRadius = 20,
  });

  final double? height;
  final double iconSize;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: AppColors.paleGreen,
        borderRadius: BorderRadius.circular(borderRadius),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: [
          Positioned(
            right: -22,
            top: -25,
            child: Container(
              width: 110,
              height: 110,
              decoration: const BoxDecoration(
                color: AppColors.softGreen,
                shape: BoxShape.circle,
              ),
            ),
          ),
          Positioned(
            left: -20,
            bottom: -30,
            child: Container(
              width: 92,
              height: 92,
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.07),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Center(
            child: Icon(
              Icons.eco_outlined,
              size: iconSize,
              color: AppColors.primary,
            ),
          ),
        ],
      ),
    );
  }
}
