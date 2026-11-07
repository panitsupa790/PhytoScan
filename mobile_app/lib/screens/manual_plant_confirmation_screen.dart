import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/analyze_outcome.dart';
import '../models/image_result.dart';
import '../models/plant.dart';
import '../services/api_service.dart';
import '../theme/login_design_tokens.dart';
import 'plant_selection_screen.dart';

class ManualPlantConfirmationScreen extends StatelessWidget {
  const ManualPlantConfirmationScreen({
    super.key,
    required this.outcome,
    required this.api,
  });

  final ManualConfirmationOutcome outcome;
  final PhytoScanApi api;

  Future<void> _choosePlant(BuildContext context) async {
    final plant = await Navigator.of(context).push<Plant>(
      MaterialPageRoute(
        builder: (_) => PlantSelectionScreen(api: api, returnSelection: true),
      ),
    );
    if (plant != null && context.mounted) {
      Navigator.of(context).pop(plant.code);
    }
  }

  @override
  Widget build(BuildContext context) {
    final inconsistent = outcome.hasInconsistentPlants;
    final suggestion = outcome.suggestedPlant;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        key: const ValueKey('manual-confirmation-screen'),
        backgroundColor: LoginColors.heroTop,
        body: SafeArea(
          bottom: false,
          child: Column(
            children: [
              _ConfirmationHero(
                inconsistent: inconsistent,
                imageCount: outcome.imagePredictions.length,
                onBack: () => Navigator.of(context).pop(),
              ),
              Expanded(
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    Positioned.fill(
                      top: -30,
                      child: Container(
                        width: double.infinity,
                        decoration: const BoxDecoration(
                          color: LoginColors.sheetSurface,
                          borderRadius: BorderRadius.vertical(
                            top: Radius.circular(34),
                          ),
                        ),
                        child: Column(
                          children: [
                            Expanded(
                              child: ListView(
                                padding: const EdgeInsets.fromLTRB(
                                  20,
                                  24,
                                  20,
                                  22,
                                ),
                                children: [
                                  _Notice(
                                    inconsistent: inconsistent,
                                    message: outcome.message,
                                  ),
                                  const SizedBox(height: 24),
                                  _SectionHeading(
                                    title: 'ผลจำแนกแต่ละภาพ',
                                    trailing:
                                        '${outcome.imagePredictions.length} ภาพ',
                                  ),
                                  const SizedBox(height: 12),
                                  for (
                                    var index = 0;
                                    index < outcome.imagePredictions.length;
                                    index++
                                  ) ...[
                                    _PredictionCard(
                                      prediction:
                                          outcome.imagePredictions[index],
                                    ),
                                    if (index <
                                        outcome.imagePredictions.length - 1)
                                      const SizedBox(height: 10),
                                  ],
                                  if (!inconsistent && suggestion != null) ...[
                                    const SizedBox(height: 24),
                                    const _SectionHeading(
                                      title: 'ชนิดพืชที่ระบบแนะนำ',
                                      trailing: 'การระบุชนิดพืช',
                                    ),
                                    const SizedBox(height: 12),
                                    _SuggestedPlantCard(suggestion: suggestion),
                                  ],
                                  const SizedBox(height: 18),
                                  _SafetyNote(inconsistent: inconsistent),
                                ],
                              ),
                            ),
                            _BottomActions(
                              inconsistent: inconsistent,
                              suggestion: suggestion,
                              onChoosePlant: () => _choosePlant(context),
                              onConfirm: suggestion == null
                                  ? null
                                  : () => Navigator.of(
                                      context,
                                    ).pop(suggestion.code),
                              onEditImages: () => Navigator.of(context).pop(),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ConfirmationHero extends StatelessWidget {
  const _ConfirmationHero({
    required this.inconsistent,
    required this.imageCount,
    required this.onBack,
  });

  final bool inconsistent;
  final int imageCount;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 220,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [LoginColors.heroTop, LoginColors.heroBottom],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -22,
            top: 4,
            child: Icon(
              Icons.spa_outlined,
              size: 170,
              color: LoginColors.white.withValues(alpha: 0.06),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 8, 20, 65),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Material(
                      color: LoginColors.white.withValues(alpha: 0.13),
                      shape: const CircleBorder(),
                      child: InkWell(
                        onTap: onBack,
                        customBorder: const CircleBorder(),
                        child: const SizedBox(
                          width: 44,
                          height: 44,
                          child: Icon(
                            Icons.arrow_back_rounded,
                            color: LoginColors.white,
                          ),
                        ),
                      ),
                    ),
                    const Expanded(
                      child: Text(
                        'ยืนยันชนิดพืช',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: LoginColors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 44),
                  ],
                ),
                const Spacer(),
                Text(
                  inconsistent
                      ? 'ภาพชุดนี้อาจเป็นพืชต่างชนิด'
                      : 'ช่วยยืนยันก่อนวิเคราะห์โรค',
                  style: const TextStyle(
                    color: LoginColors.white,
                    fontSize: 24,
                    height: 1.2,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _HeroBadge(
                      icon: Icons.photo_library_outlined,
                      label: '$imageCount ภาพ',
                    ),
                    const SizedBox(width: 8),
                    _HeroBadge(
                      icon: inconsistent
                          ? Icons.warning_amber_rounded
                          : Icons.touch_app_outlined,
                      label: inconsistent ? 'ต้องแยกชุดภาพ' : 'รอการยืนยัน',
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroBadge extends StatelessWidget {
  const _HeroBadge({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
      decoration: BoxDecoration(
        color: LoginColors.white.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: LoginColors.white.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: LoginColors.white, size: 15),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              color: LoginColors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.inconsistent, required this.message});

  final bool inconsistent;
  final String message;

  @override
  Widget build(BuildContext context) {
    final accent = inconsistent
        ? LoginColors.orangeHighlight
        : LoginColors.accentGreen;
    final hasThaiMessage = RegExp(r'[\u0E00-\u0E7F]').hasMatch(message);
    final localizedMessage = hasThaiMessage
        ? message
        : inconsistent
        ? 'กรุณาแยกภาพต่างชนิดออกก่อนเริ่มวิเคราะห์อีกครั้ง'
        : 'โปรดตรวจสอบชนิดพืชด้วยตนเองก่อนส่งต่อไปยังโมเดลโรค';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: inconsistent ? const Color(0xFFFFF0E7) : const Color(0xFFEAF2E6),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: accent.withValues(alpha: 0.35)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: LoginColors.white,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              inconsistent
                  ? Icons.warning_amber_rounded
                  : Icons.fact_check_outlined,
              color: inconsistent
                  ? LoginColors.orangeHighlight
                  : LoginColors.primaryGreen,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  inconsistent
                      ? 'ภาพอาจเป็นพืชต่างชนิดกัน'
                      : 'ต้องยืนยันชนิดพืชก่อน',
                  style: const TextStyle(
                    color: LoginColors.primaryText,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  localizedMessage,
                  style: const TextStyle(
                    color: LoginColors.secondaryText,
                    fontSize: 13,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, required this.trailing});

  final String title;
  final String trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              color: LoginColors.primaryText,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Text(
          trailing,
          style: const TextStyle(
            color: LoginColors.secondaryText,
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.4,
          ),
        ),
      ],
    );
  }
}

class _PredictionCard extends StatelessWidget {
  const _PredictionCard({required this.prediction});

  final ImagePlantPrediction prediction;

  String _reasonLabel(String reason) => switch (reason) {
    'low_confidence' => 'ระบบยังระบุชนิดพืชไม่ได้ชัดเจน',
    'low_margin' => 'ผลการระบุชนิดพืชใกล้เคียงกัน',
    'inconsistent_plant' => 'ชนิดพืชไม่ตรงกัน',
    _ => reason,
  };

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: LoginColors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: LoginColors.fieldBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: LoginColors.segmentTrack,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: Center(
                  child: Text(
                    '${prediction.index + 1}'.padLeft(2, '0'),
                    style: const TextStyle(
                      color: LoginColors.primaryGreen,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      prediction.plant.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: LoginColors.primaryText,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      prediction.filename,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: LoginColors.secondaryText,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.help_outline_rounded,
                color: LoginColors.orangeHighlight,
                size: 22,
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'ผลการระบุชนิดพืชจากภาพถ่าย กรุณาตรวจสอบก่อนวิเคราะห์โรค',
            style: TextStyle(
              color: LoginColors.secondaryText,
              fontSize: 12,
              height: 1.4,
            ),
          ),
          if (prediction.reasons.isNotEmpty) ...[
            const SizedBox(height: 9),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final reason in prediction.reasons)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 9,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF0E7),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      _reasonLabel(reason),
                      style: const TextStyle(
                        color: Color(0xFF9B4B23),
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _SuggestedPlantCard extends StatelessWidget {
  const _SuggestedPlantCard({required this.suggestion});

  final PredictionLabel suggestion;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: const Color(0xFFEAF2E6),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: LoginColors.fieldBorder),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: LoginColors.white,
              borderRadius: BorderRadius.circular(15),
            ),
            child: const Icon(
              Icons.eco_outlined,
              color: LoginColors.primaryGreen,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  suggestion.displayName,
                  style: const TextStyle(
                    color: LoginColors.primaryText,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
            decoration: BoxDecoration(
              color: LoginColors.accentGreen.withValues(alpha: 0.28),
              borderRadius: BorderRadius.circular(999),
            ),
            child: const Text(
              'ระบบแนะนำ',
              style: TextStyle(
                color: LoginColors.primaryGreen,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SafetyNote extends StatelessWidget {
  const _SafetyNote({required this.inconsistent});

  final bool inconsistent;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(top: 2),
          child: Icon(
            Icons.info_outline_rounded,
            size: 15,
            color: LoginColors.secondaryText,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            inconsistent
                ? 'ระบบจะไม่รวมภาพต่างชนิดเป็นผลโรคเดียวกัน กรุณาแยกชุดภาพก่อนดำเนินการต่อ'
                : 'ชนิดพืชจะถูกบันทึกว่าได้รับการยืนยันโดยผู้ใช้ ไม่ใช่ผลยืนยันจากระบบอัตโนมัติ',
            style: const TextStyle(
              color: LoginColors.secondaryText,
              fontSize: 11,
              height: 1.45,
            ),
          ),
        ),
      ],
    );
  }
}

class _BottomActions extends StatelessWidget {
  const _BottomActions({
    required this.inconsistent,
    required this.suggestion,
    required this.onChoosePlant,
    required this.onConfirm,
    required this.onEditImages,
  });

  final bool inconsistent;
  final PredictionLabel? suggestion;
  final VoidCallback onChoosePlant;
  final VoidCallback? onConfirm;
  final VoidCallback onEditImages;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        20,
        12,
        20,
        MediaQuery.paddingOf(context).bottom + 12,
      ),
      decoration: const BoxDecoration(
        color: LoginColors.white,
        border: Border(top: BorderSide(color: LoginColors.fieldBorder)),
      ),
      child: inconsistent || suggestion == null
          ? _PrimaryAction(
              key: const ValueKey('edit-inconsistent-images'),
              label: 'กลับไปแก้ไขชุดภาพ',
              icon: Icons.photo_library_outlined,
              onTap: onEditImages,
            )
          : Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _PrimaryAction(
                  key: const ValueKey('confirm-suggested-plant'),
                  label: 'ยืนยันว่าเป็น${suggestion!.displayName}',
                  icon: Icons.check_rounded,
                  onTap: onConfirm!,
                ),
                const SizedBox(height: 7),
                TextButton(
                  onPressed: onChoosePlant,
                  child: const Text('เลือกชนิดพืชอื่น'),
                ),
              ],
            ),
    );
  }
}

class _PrimaryAction extends StatelessWidget {
  const _PrimaryAction({
    super.key,
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 54,
      child: FilledButton.icon(
        onPressed: onTap,
        icon: Icon(icon, size: 20),
        label: Text(label),
        style: FilledButton.styleFrom(
          backgroundColor: LoginColors.primaryGreen,
          foregroundColor: LoginColors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
    );
  }
}
