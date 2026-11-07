import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/image_result.dart';
import '../theme/scan_design_tokens.dart';
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

  bool get _isHealthy {
    final value =
        '${result.disease.code} ${result.disease.nameEn} '
                '${result.disease.nameTh}'
            .toLowerCase();
    return value.contains('healthy') || value.contains('สุขภาพดี');
  }

  bool get _isUnavailable {
    final value = '${result.disease.code} ${result.disease.nameEn}'
        .toLowerCase()
        .trim();
    return value.isEmpty ||
        value.contains('unavailable') ||
        value.contains('not_available') ||
        value.contains('unknown');
  }

  Color get _statusColor => _isUnavailable
      ? ScanColors.textSecondary
      : _isHealthy
      ? ScanColors.primary
      : ScanColors.orange;

  IconData get _statusIcon => _isUnavailable
      ? Icons.help_outline_rounded
      : _isHealthy
      ? Icons.check_circle_outline_rounded
      : Icons.auto_awesome_rounded;

  String get _statusText => _isUnavailable
      ? 'ยังไม่มีผลวินิจฉัยพร้อมแสดง'
      : _isHealthy
      ? 'ภาพมีลักษณะสอดคล้องกับใบสุขภาพดี'
      : 'พบลักษณะที่อาจผิดปกติ';

  String get _displayName => result.disease.displayName.trim().isEmpty
      ? 'ไม่พบข้อมูลผลวินิจฉัย'
      : result.disease.displayName;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: ScanColors.white,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(ScanRadii.card),
        side: const BorderSide(color: ScanColors.track),
      ),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 96,
                    height: 116,
                    child: ImagePickerCard.preview(
                      image: image,
                      onRemove: null,
                      order: result.index + 1,
                    ),
                  ),
                  const SizedBox(width: 13),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          alignment: Alignment.centerLeft,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 5,
                            ),
                            decoration: BoxDecoration(
                              color: _statusColor.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  _statusIcon,
                                  size: 13,
                                  color: _statusColor,
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  _statusText,
                                  style: TextStyle(
                                    color: _statusColor,
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 7),
                        Text(
                          _displayName,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(
                                color: ScanColors.text,
                                fontWeight: FontWeight.w700,
                              ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'ผลการวินิจฉัยเบื้องต้นจากภาพถ่าย',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(
                                color: ScanColors.textSecondary,
                                fontSize: 11,
                              ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(height: 1, color: ScanColors.track),
              const SizedBox(height: 11),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'ดูรายละเอียดอาการและคำแนะนำ',
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: ScanColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const Icon(
                    Icons.arrow_outward_rounded,
                    size: 17,
                    color: ScanColors.primary,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
