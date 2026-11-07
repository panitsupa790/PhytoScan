import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../models/analyze_result.dart';
import '../theme/scan_design_tokens.dart';
import '../widgets/diagnosis_result_card.dart';
import 'disease_detail_screen.dart';

enum PlantIdentificationSource { automatic, manuallyConfirmed }

class ResultScreen extends StatelessWidget {
  const ResultScreen({
    super.key,
    required this.result,
    required this.images,
    this.identificationSource = PlantIdentificationSource.automatic,
  });

  final AnalyzeResult result;
  final List<XFile> images;
  final PlantIdentificationSource identificationSource;

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

  List<String> _careItems(List<ImageResult> rows) {
    final source = result.care.isNotEmpty
        ? result.care
        : rows.expand((row) => row.care);
    return source.toSet().toList(growable: false);
  }

  String _summaryText(List<ImageResult> rows) {
    if (rows.isEmpty) return 'ยังไม่มีผลรายภาพสำหรับแสดงผล';
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
    if (images.isEmpty) return;
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
    final rows = images.isEmpty ? <ImageResult>[] : _imageResults;
    final careItems = _careItems(rows);
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        key: const ValueKey('result-screen'),
        backgroundColor: ScanColors.heroTop,
        body: SafeArea(
          bottom: false,
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: ColoredBox(
                  color: ScanColors.surface,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _ResultHero(
                        imageCount: rows.length,
                        plantName: result.plant.displayName,
                        onBack: () => Navigator.of(context).maybePop(),
                      ),
                      Transform.translate(
                        offset: const Offset(0, -36),
                        child: Container(
                          width: double.infinity,
                          clipBehavior: Clip.antiAlias,
                          decoration: const BoxDecoration(
                            color: ScanColors.surface,
                            borderRadius: BorderRadius.vertical(
                              top: Radius.circular(ScanRadii.sheet),
                            ),
                          ),
                          padding: const EdgeInsets.fromLTRB(20, 28, 20, 150),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _SectionHeading(
                                title: 'ผลการตรวจพบ',
                                trailing: rows.isEmpty
                                    ? 'ไม่มีภาพ'
                                    : 'ภาพที่ 01 / ${rows.length.toString().padLeft(2, '0')}',
                              ),
                              const SizedBox(height: 14),
                              if (rows.isEmpty)
                                const _EmptyResultCard()
                              else
                                for (
                                  var index = 0;
                                  index < rows.length;
                                  index++
                                ) ...[
                                  DiagnosisResultCard(
                                    image:
                                        images[rows[index].index < images.length
                                            ? rows[index].index
                                            : images.length - 1],
                                    result: rows[index],
                                    onTap: () =>
                                        _openDetail(context, rows[index]),
                                  ),
                                  if (index < rows.length - 1)
                                    const SizedBox(height: 14),
                                ],
                              const SizedBox(height: 26),
                              const _SectionHeading(
                                title: 'ชนิดพืชที่ตรวจพบ',
                                trailing: 'การระบุชนิดพืช',
                              ),
                              const SizedBox(height: 12),
                              _PlantIdentificationCard(
                                plant: result.plant,
                                source: identificationSource,
                              ),
                              const SizedBox(height: 26),
                              const _SectionHeading(
                                title: 'ขั้นตอนถัดไป',
                                trailing: 'คำแนะนำการดูแล',
                              ),
                              const SizedBox(height: 14),
                              _CareGuidanceCard(items: careItems),
                              const SizedBox(height: 24),
                              _SummaryCard(text: _summaryText(rows)),
                              const SizedBox(height: 16),
                              Text(
                                'ผลนี้เป็นการจำแนกจากภาพเบื้องต้น ไม่ใช่การยืนยันทางห้องปฏิบัติการ',
                                style: Theme.of(context).textTheme.bodyMedium
                                    ?.copyWith(color: ScanColors.textSecondary),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        bottomNavigationBar: _ResultBottomAction(
          onHome: () =>
              Navigator.of(context).popUntil((route) => route.isFirst),
          onAnalyzeAgain: () => Navigator.of(context).pop(),
        ),
      ),
    );
  }
}

class _ResultHero extends StatelessWidget {
  const _ResultHero({
    required this.imageCount,
    required this.plantName,
    required this.onBack,
  });

  final int imageCount;
  final String plantName;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [ScanColors.heroTop, ScanColors.heroBottom],
        ),
      ),
      child: Stack(
        children: [
          const Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(painter: _ResultBotanicalPainter()),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 10, 20, 58),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _HeroBackButton(onPressed: onBack),
                    const Expanded(
                      child: Text(
                        'ผลการวิเคราะห์',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: ScanColors.white,
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
                const SizedBox(height: 22),
                Text(
                  'ผลตรวจสุขภาพใบพืชของคุณ',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: ScanColors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 7),
                Text(
                  'PhytoScan วิเคราะห์ภาพเรียบร้อยแล้ว',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: ScanColors.white.withValues(alpha: 0.76),
                  ),
                ),
                const SizedBox(height: 17),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    const _HeroStatusChip(
                      icon: Icons.check_circle_outline_rounded,
                      label: 'วิเคราะห์เสร็จแล้ว',
                      accent: true,
                    ),
                    _HeroStatusChip(
                      icon: Icons.photo_library_outlined,
                      label: '$imageCount ภาพ',
                    ),
                    _HeroStatusChip(icon: Icons.eco_outlined, label: plantName),
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

class _HeroBackButton extends StatelessWidget {
  const _HeroBackButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 48,
      height: 48,
      child: IconButton(
        tooltip: 'ย้อนกลับ',
        onPressed: onPressed,
        style: IconButton.styleFrom(
          backgroundColor: ScanColors.white.withValues(alpha: 0.12),
          foregroundColor: ScanColors.white,
        ),
        icon: const Icon(Icons.arrow_back_rounded, size: 22),
      ),
    );
  }
}

class _HeroStatusChip extends StatelessWidget {
  const _HeroStatusChip({
    required this.icon,
    required this.label,
    this.accent = false,
  });

  final IconData icon;
  final String label;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
      decoration: BoxDecoration(
        color: accent
            ? ScanColors.accent
            : ScanColors.white.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: accent
            ? null
            : Border.all(color: ScanColors.white.withValues(alpha: 0.16)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 16,
            color: accent ? ScanColors.primary : ScanColors.white,
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: accent ? ScanColors.primary : ScanColors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlantIdentificationCard extends StatelessWidget {
  const _PlantIdentificationCard({required this.plant, required this.source});

  final PredictionLabel plant;
  final PlantIdentificationSource source;

  @override
  Widget build(BuildContext context) {
    final manuallyConfirmed =
        source == PlantIdentificationSource.manuallyConfirmed;
    return Container(
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: ScanColors.instruction,
        borderRadius: BorderRadius.circular(ScanRadii.card),
        border: Border.all(color: ScanColors.track),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              color: ScanColors.white,
              shape: BoxShape.circle,
            ),
            child: Icon(
              manuallyConfirmed
                  ? Icons.person_outline_rounded
                  : Icons.eco_outlined,
              color: ScanColors.primary,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  plant.nameTh.trim().isNotEmpty ? plant.nameTh : plant.nameEn,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: ScanColors.text,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  manuallyConfirmed
                      ? 'ชนิดพืชนี้ได้รับการยืนยันโดยผู้ใช้'
                      : 'ระบุชนิดพืชจากภาพถ่ายโดยระบบ',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: ScanColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
            decoration: BoxDecoration(
              color: manuallyConfirmed
                  ? ScanColors.white
                  : ScanColors.accent.withValues(alpha: 0.55),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              manuallyConfirmed
                  ? Icons.person_outline_rounded
                  : Icons.auto_awesome_outlined,
              size: 16,
              color: ScanColors.primary,
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
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Expanded(
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: ScanColors.text,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          trailing,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: ScanColors.textSecondary,
            fontSize: 10,
            letterSpacing: 0.2,
          ),
        ),
      ],
    );
  }
}

class _CareGuidanceCard extends StatelessWidget {
  const _CareGuidanceCard({required this.items});

  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: ScanColors.uploadSurface,
        borderRadius: BorderRadius.circular(ScanRadii.card),
        border: Border.all(color: ScanColors.track),
      ),
      child: items.isEmpty
          ? Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.info_outline_rounded,
                  color: ScanColors.textSecondary,
                  size: 21,
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Text(
                    'ยังไม่มีข้อมูลคำแนะนำสำหรับผลการวิเคราะห์นี้',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: ScanColors.textSecondary,
                    ),
                  ),
                ),
              ],
            )
          : Column(
              children: [
                for (var index = 0; index < items.length; index++) ...[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: ScanColors.accent.withValues(alpha: 0.45),
                          shape: BoxShape.circle,
                        ),
                        child: Text(
                          '${index + 1}',
                          style: const TextStyle(
                            color: ScanColors.primary,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 11),
                      Expanded(
                        child: Text(
                          items[index],
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(color: ScanColors.text),
                        ),
                      ),
                    ],
                  ),
                  if (index < items.length - 1) const SizedBox(height: 12),
                ],
              ],
            ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: ScanColors.primary,
        borderRadius: BorderRadius.circular(ScanRadii.card),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.analytics_outlined,
            color: ScanColors.accent,
            size: 22,
          ),
          const SizedBox(width: 11),
          Expanded(
            child: Text(
              text,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: ScanColors.white,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyResultCard extends StatelessWidget {
  const _EmptyResultCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ScanColors.uploadSurface,
        borderRadius: BorderRadius.circular(ScanRadii.card),
        border: Border.all(color: ScanColors.track),
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.image_not_supported_outlined,
            color: ScanColors.textSecondary,
          ),
          SizedBox(width: 9),
          Text(
            'ไม่มีผลรายภาพสำหรับแสดงผล',
            style: TextStyle(color: ScanColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _ResultBottomAction extends StatelessWidget {
  const _ResultBottomAction({
    required this.onHome,
    required this.onAnalyzeAgain,
  });

  final VoidCallback onHome;
  final VoidCallback onAnalyzeAgain;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 14),
      decoration: BoxDecoration(
        color: ScanColors.surface,
        border: const Border(top: BorderSide(color: ScanColors.track)),
        boxShadow: [
          BoxShadow(
            color: ScanColors.primary.withValues(alpha: 0.08),
            blurRadius: 18,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              flex: 4,
              child: OutlinedButton.icon(
                key: const ValueKey('result-home-button'),
                onPressed: onHome,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(56),
                  foregroundColor: ScanColors.primary,
                  side: const BorderSide(color: ScanColors.primary),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                  ),
                ),
                icon: const Icon(Icons.home_rounded, size: 20),
                label: const Text('หน้าหลัก'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              flex: 6,
              child: FilledButton.icon(
                key: const ValueKey('analyze-again-button'),
                onPressed: onAnalyzeAgain,
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(56),
                  backgroundColor: ScanColors.primary,
                  foregroundColor: ScanColors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                  ),
                ),
                icon: const Icon(Icons.refresh_rounded, size: 20),
                label: const Text('วิเคราะห์ใหม่'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResultBotanicalPainter extends CustomPainter {
  const _ResultBotanicalPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final leaf = Paint()..color = ScanColors.accent.withValues(alpha: 0.07);
    final stem = Paint()
      ..color = ScanColors.accent.withValues(alpha: 0.12)
      ..strokeWidth = 2;
    final origin = Offset(size.width * 0.78, size.height * 0.12);
    final end = Offset(size.width * 0.93, size.height * 0.9);
    canvas.drawLine(origin, end, stem);
    for (var index = 0; index < 4; index++) {
      final y = size.height * (0.18 + index * 0.18);
      final x = size.width * (0.76 + index * 0.035);
      canvas.save();
      canvas.translate(x, y);
      canvas.rotate(index.isEven ? -0.35 : 0.35);
      canvas.drawOval(const Rect.fromLTWH(0, 0, 105, 42), leaf);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
