import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/analyze_result.dart';
import '../theme/app_theme.dart';
import '../widgets/diagnosis_result_card.dart';
import '../widgets/primary_button.dart';
import 'disease_detail_screen.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.result, required this.images});

  final AnalyzeResult result;
  final List<XFile> images;

  List<ImageResult> get _imageResults {
    if (result.imageResults.isNotEmpty) return result.imageResults;
    return [
      ImageResult(
        index: 0,
        filename: images.isEmpty ? '' : images.first.name,
        disease: result.disease,
        symptoms: result.symptoms,
        care: result.care,
        prevention: result.prevention,
      ),
    ];
  }

  String _summaryText(List<ImageResult> rows) {
    if (rows.length == 1) {
      return 'พบลักษณะ ${rows.first.disease.displayName} ในภาพที่ส่งมา';
    }
    final firstCode = rows.first.disease.code;
    final matching = rows.where((row) => row.disease.code == firstCode).length;
    if (matching == rows.length) {
      return 'พบลักษณะ ${rows.first.disease.displayName} ใน $matching จาก ${rows.length} ภาพ';
    }
    return 'ผลจากภาพที่ส่งมามีความแตกต่างกัน กรุณาตรวจผลแต่ละภาพ';
  }

  void _openDetail(BuildContext context, ImageResult imageResult) {
    final imageIndex = imageResult.index < images.length
        ? imageResult.index
        : images.length - 1;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => DiseaseDetailScreen(
          plant: result.plant,
          result: imageResult,
          image: images[imageIndex],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final rows = _imageResults.where((row) => images.isNotEmpty).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('ผลการวิเคราะห์')),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(22, 12, 22, 30),
          children: [
            Text(
              'ผลของแต่ละภาพ',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            Text(
              '${result.plant.displayName} • ${rows.length} ภาพ',
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 22),
            for (var index = 0; index < rows.length; index++) ...[
              DiagnosisResultCard(
                image:
                    images[rows[index].index < images.length
                        ? rows[index].index
                        : images.length - 1],
                result: rows[index],
                onTap: () => _openDetail(context, rows[index]),
              ),
              if (index < rows.length - 1) const SizedBox(height: 14),
            ],
            const SizedBox(height: 30),
            Text(
              'สรุปภาพรวม',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppColors.paleGreen,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.analytics_outlined,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _summaryText(rows),
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: AppColors.darkGreen,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'ผลนี้เป็นการจำแนกจากภาพเบื้องต้น ไม่ใช่การยืนยันทางห้องปฏิบัติการ',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 28),
            PrimaryButton(
              label: 'วิเคราะห์ใหม่',
              icon: Icons.refresh_rounded,
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
      ),
    );
  }
}
