import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/image_result.dart';
import '../theme/app_theme.dart';
import '../widgets/image_picker_card.dart';
import '../widgets/result_section.dart';

class DiseaseDetailScreen extends StatelessWidget {
  const DiseaseDetailScreen({
    super.key,
    required this.plant,
    required this.result,
    required this.image,
  });

  final PredictionLabel plant;
  final ImageResult result;
  final XFile image;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('รายละเอียดผลตรวจ')),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(22, 10, 22, 34),
          children: [
            AspectRatio(
              aspectRatio: 1.25,
              child: ImagePickerCard.preview(
                image: image,
                onRemove: null,
                order: result.index + 1,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              plant.displayName,
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 4),
            Text(
              result.disease.displayName,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            if (result.disease.nameTh.trim().isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                result.disease.nameEn,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ความมั่นใจในการจำแนก',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 3),
                      Text(
                        result.disease.confidenceLabel,
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(color: AppColors.primary),
                      ),
                    ],
                  ),
                ),
                Text(
                  '${(result.disease.confidence * 100).toStringAsFixed(1)}%',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
              ],
            ),
            const SizedBox(height: 26),
            const Divider(),
            const SizedBox(height: 24),
            if (!result.hasDetails)
              Container(
                padding: const EdgeInsets.all(17),
                decoration: BoxDecoration(
                  color: AppColors.paleGreen,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: const Text(
                  'รายละเอียดสำหรับรายการนี้ยังไม่พร้อมใช้งาน',
                  style: TextStyle(color: AppColors.darkGreen),
                ),
              )
            else ...[
              ResultSection(title: 'อาการ', items: result.symptoms),
              const SizedBox(height: 22),
              const Divider(),
              const SizedBox(height: 22),
              ResultSection(title: 'การดูแล', items: result.care),
              const SizedBox(height: 22),
              const Divider(),
              const SizedBox(height: 22),
              ResultSection(title: 'การป้องกัน', items: result.prevention),
            ],
          ],
        ),
      ),
    );
  }
}
