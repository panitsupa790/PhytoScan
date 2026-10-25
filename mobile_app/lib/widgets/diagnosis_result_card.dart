import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/image_result.dart';
import '../theme/app_theme.dart';
import 'image_picker_card.dart';

class DiagnosisResultCard extends StatelessWidget {
  const DiagnosisResultCard({
    super.key,
    required this.image,
    required this.result,
    required this.onTap,
  });

  final XFile image;
  final ImageResult result;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 112,
                height: 132,
                child: ImagePickerCard.preview(
                  image: image,
                  onRemove: null,
                  order: result.index + 1,
                ),
              ),
              const SizedBox(width: 15),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        result.disease.displayName,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      if (result.disease.nameTh.trim().isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          result.disease.nameEn,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                      const SizedBox(height: 12),
                      Text(
                        result.disease.confidenceLabel,
                        style: Theme.of(context).textTheme.labelMedium
                            ?.copyWith(
                              color: _confidenceColor(
                                result.disease.confidence,
                              ),
                            ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        '${(result.disease.confidence * 100).toStringAsFixed(1)}%',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 7),
                      Row(
                        children: [
                          Text(
                            'ดูรายละเอียด',
                            style: Theme.of(context).textTheme.labelMedium
                                ?.copyWith(color: AppColors.primary),
                          ),
                          const SizedBox(width: 2),
                          const Icon(
                            Icons.chevron_right_rounded,
                            size: 18,
                            color: AppColors.primary,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _confidenceColor(double confidence) {
    if (confidence >= PredictionLabel.highConfidenceMinimum) {
      return AppColors.primary;
    }
    if (confidence >= PredictionLabel.mediumConfidenceMinimum) {
      return AppColors.warning;
    }
    return AppColors.error;
  }
}
