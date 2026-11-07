import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../models/image_result.dart';
import '../theme/scan_design_tokens.dart';

enum _DetailTab { result, symptoms, care, prevention }

class DiseaseDetailScreen extends StatefulWidget {
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
  State<DiseaseDetailScreen> createState() => _DiseaseDetailScreenState();
}

class _DiseaseDetailScreenState extends State<DiseaseDetailScreen> {
  _DetailTab _selectedTab = _DetailTab.result;
  bool _imageExpanded = false;
  late final Future<Uint8List> _imageBytes;

  ImageResult get result => widget.result;

  bool get _isHealthy {
    final value =
        '${result.disease.code} ${result.disease.nameTh} '
                '${result.disease.nameEn}'
            .toLowerCase();
    return value.contains('healthy') || value.contains('สุขภาพดี');
  }

  bool get _isUnavailable {
    final value = '${result.disease.code} ${result.disease.nameEn}'
        .toLowerCase();
    return value.trim().isEmpty ||
        value.contains('unavailable') ||
        value.contains('not_available');
  }

  bool get _isUncertain =>
      !_isUnavailable &&
      result.disease.confidence < PredictionLabel.mediumConfidenceMinimum;

  @override
  void initState() {
    super.initState();
    _imageBytes = widget.image.readAsBytes();
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.dark,
      child: Scaffold(
        key: const ValueKey('disease-detail-screen'),
        backgroundColor: ScanColors.surface,
        body: SafeArea(
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: _DetailHeader(
                  onBack: () => Navigator.of(context).maybePop(),
                  onInfo: _showAiLimitations,
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 36),
                sliver: SliverList.list(
                  children: [
                    Text(
                      'ไฟโตสแกน · ภาพที่ ${(result.index + 1).toString().padLeft(2, '0')}',
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: ScanColors.primary,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'ผลตรวจใบพืช',
                      style: Theme.of(context).textTheme.headlineMedium
                          ?.copyWith(
                            color: ScanColors.text,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _plantNames,
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: ScanColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 20),
                    _ImagePreview(
                      bytes: _imageBytes,
                      imageNumber: result.index + 1,
                      expanded: _imageExpanded,
                      onToggle: () =>
                          setState(() => _imageExpanded = !_imageExpanded),
                    ),
                    const SizedBox(height: 20),
                    _DiagnosisCard(
                      result: result,
                      healthy: _isHealthy,
                      uncertain: _isUncertain,
                      unavailable: _isUnavailable,
                    ),
                    const SizedBox(height: 28),
                    Text(
                      'รายละเอียดและคำแนะนำ',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(
                            color: ScanColors.text,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 13),
                    _DetailSegmentedControl(
                      selected: _selectedTab,
                      onChanged: (value) =>
                          setState(() => _selectedTab = value),
                    ),
                    const SizedBox(height: 14),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 180),
                      child: KeyedSubtree(
                        key: ValueKey(_selectedTab),
                        child: _tabContent(context),
                      ),
                    ),
                    const SizedBox(height: 24),
                    const _AiLimitationNote(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String get _plantNames {
    final thai = widget.plant.nameTh.trim();
    return thai.isNotEmpty ? thai : widget.plant.displayName;
  }

  Widget _tabContent(BuildContext context) {
    return switch (_selectedTab) {
      _DetailTab.result => _ResultTab(
        result: result,
        healthy: _isHealthy,
        uncertain: _isUncertain,
        unavailable: _isUnavailable,
      ),
      _DetailTab.symptoms => _MetadataList(
        icon: Icons.monitor_heart_outlined,
        items: result.symptoms,
        emptyMessage: _isHealthy
            ? 'ผลนี้ไม่มีข้อมูลอาการผิดปกติจากระบบ'
            : 'ยังไม่มีข้อมูลอาการสำหรับรายการนี้',
      ),
      _DetailTab.care => _MetadataList(
        icon: Icons.spa_outlined,
        items: result.care,
        emptyMessage: 'ยังไม่มีคำแนะนำสำหรับรายการนี้',
      ),
      _DetailTab.prevention => _MetadataList(
        icon: Icons.shield_outlined,
        items: result.prevention,
        emptyMessage: 'ยังไม่มีข้อมูลการป้องกันสำหรับรายการนี้',
      ),
    };
  }

  void _showAiLimitations() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: ScanColors.surface,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (context) => const SafeArea(
        top: false,
        child: Padding(
          padding: EdgeInsets.fromLTRB(22, 6, 22, 24),
          child: _AiLimitationNote(showTitle: true),
        ),
      ),
    );
  }
}

class _DetailHeader extends StatelessWidget {
  const _DetailHeader({required this.onBack, required this.onInfo});

  final VoidCallback onBack;
  final VoidCallback onInfo;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 5, 12, 5),
      child: SizedBox(
        height: 52,
        child: Row(
          children: [
            SizedBox(
              width: 44,
              height: 44,
              child: IconButton(
                tooltip: 'ย้อนกลับ',
                onPressed: onBack,
                style: IconButton.styleFrom(
                  foregroundColor: ScanColors.primary,
                  backgroundColor: ScanColors.instruction,
                ),
                icon: const Icon(Icons.arrow_back_rounded, size: 21),
              ),
            ),
            Expanded(
              child: Text(
                'รายละเอียดผลตรวจ',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: ScanColors.text,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            SizedBox(
              width: 44,
              height: 44,
              child: IconButton(
                tooltip: 'ข้อมูลเกี่ยวกับผลจากระบบ',
                onPressed: onInfo,
                style: IconButton.styleFrom(
                  foregroundColor: ScanColors.primary,
                  backgroundColor: ScanColors.instruction,
                ),
                icon: const Icon(Icons.info_outline_rounded, size: 21),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ImagePreview extends StatelessWidget {
  const _ImagePreview({
    required this.bytes,
    required this.imageNumber,
    required this.expanded,
    required this.onToggle,
  });

  final Future<Uint8List> bytes;
  final int imageNumber;
  final bool expanded;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOut,
      height: expanded ? 430 : 250,
      width: double.infinity,
      decoration: BoxDecoration(
        color: ScanColors.uploadSurface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ScanColors.track),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        fit: StackFit.expand,
        children: [
          FutureBuilder<Uint8List>(
            future: bytes,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return const Center(
                  child: Icon(
                    Icons.broken_image_outlined,
                    color: ScanColors.textSecondary,
                    size: 38,
                  ),
                );
              }
              if (!snapshot.hasData) {
                return const Center(
                  child: CircularProgressIndicator(color: ScanColors.primary),
                );
              }
              return GestureDetector(
                onTap: onToggle,
                child: Image.memory(
                  snapshot.data!,
                  fit: expanded ? BoxFit.contain : BoxFit.cover,
                ),
              );
            },
          ),
          Positioned(
            left: 12,
            bottom: 12,
            child: _ImageBadge(label: imageNumber.toString().padLeft(2, '0')),
          ),
          Positioned(
            right: 12,
            bottom: 12,
            child: FilledButton.tonalIcon(
              onPressed: onToggle,
              style: FilledButton.styleFrom(
                minimumSize: const Size(0, 38),
                padding: const EdgeInsets.symmetric(horizontal: 12),
                backgroundColor: ScanColors.white.withValues(alpha: 0.92),
                foregroundColor: ScanColors.primary,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(13),
                ),
              ),
              icon: Icon(
                expanded
                    ? Icons.close_fullscreen_rounded
                    : Icons.open_in_full_rounded,
                size: 16,
              ),
              label: Text(expanded ? 'ย่อภาพ' : 'ขยายภาพ'),
            ),
          ),
        ],
      ),
    );
  }
}

class _ImageBadge extends StatelessWidget {
  const _ImageBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: ScanColors.primary.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: ScanColors.white,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _DiagnosisCard extends StatelessWidget {
  const _DiagnosisCard({
    required this.result,
    required this.healthy,
    required this.uncertain,
    required this.unavailable,
  });

  final ImageResult result;
  final bool healthy;
  final bool uncertain;
  final bool unavailable;

  @override
  Widget build(BuildContext context) {
    final accent = unavailable
        ? ScanColors.textSecondary
        : uncertain
        ? ScanColors.orange
        : ScanColors.primary;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: ScanColors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ScanColors.track),
        boxShadow: [
          BoxShadow(
            color: ScanColors.primary.withValues(alpha: 0.05),
            blurRadius: 18,
            offset: const Offset(0, 7),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.11),
                  shape: BoxShape.circle,
                ),
                child: Icon(_statusIcon, color: accent, size: 21),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ผลการวินิจฉัยเบื้องต้นจากภาพถ่าย',
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: ScanColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _statusLabel,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: accent,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            result.disease.displayName,
            maxLines: 4,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: ScanColors.text,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (!unavailable) ...[
            const SizedBox(height: 12),
            Text(
              'ควรพิจารณาผลร่วมกับลักษณะจริงของใบพืช และขอคำแนะนำจากผู้เชี่ยวชาญเมื่ออาการรุนแรง',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: ScanColors.textSecondary,
                fontSize: 12,
              ),
            ),
          ],
        ],
      ),
    );
  }

  IconData get _statusIcon {
    if (unavailable) return Icons.cloud_off_outlined;
    if (uncertain) return Icons.help_outline_rounded;
    if (healthy) return Icons.check_circle_outline_rounded;
    return Icons.biotech_outlined;
  }

  String get _statusLabel {
    if (unavailable) return 'ยังไม่มีโมเดลโรคที่พร้อมใช้งาน';
    if (uncertain) return 'ผลควรได้รับการตรวจสอบเพิ่มเติม';
    if (healthy) return 'ภาพมีลักษณะสอดคล้องกับใบสุขภาพดี';
    return 'พบลักษณะที่อาจสอดคล้องกับโรค';
  }
}

class _DetailSegmentedControl extends StatelessWidget {
  const _DetailSegmentedControl({
    required this.selected,
    required this.onChanged,
  });

  final _DetailTab selected;
  final ValueChanged<_DetailTab> onChanged;

  @override
  Widget build(BuildContext context) {
    const labels = {
      _DetailTab.result: 'ผลตรวจ',
      _DetailTab.symptoms: 'อาการ',
      _DetailTab.care: 'การดูแล',
      _DetailTab.prevention: 'การป้องกัน',
    };
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: ScanColors.track,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          for (final tab in _DetailTab.values)
            Expanded(
              child: _SegmentButton(
                label: labels[tab]!,
                selected: selected == tab,
                onTap: () => onChanged(tab),
              ),
            ),
        ],
      ),
    );
  }
}

class _SegmentButton extends StatelessWidget {
  const _SegmentButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected ? ScanColors.white : Colors.transparent,
        borderRadius: BorderRadius.circular(12),
        elevation: selected ? 1 : 0,
        shadowColor: ScanColors.primary.withValues(alpha: 0.12),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 10),
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.fade,
              softWrap: false,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: selected ? ScanColors.primary : ScanColors.textSecondary,
                fontSize: 11,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ResultTab extends StatelessWidget {
  const _ResultTab({
    required this.result,
    required this.healthy,
    required this.uncertain,
    required this.unavailable,
  });

  final ImageResult result;
  final bool healthy;
  final bool uncertain;
  final bool unavailable;

  @override
  Widget build(BuildContext context) {
    final hasMetadata = result.hasDetails;
    return _TabSurface(
      icon: unavailable
          ? Icons.cloud_off_outlined
          : uncertain
          ? Icons.help_outline_rounded
          : healthy
          ? Icons.check_circle_outline_rounded
          : Icons.analytics_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            unavailable
                ? 'ระบบยังไม่มีผลวินิจฉัยโรคที่พร้อมแสดง'
                : healthy
                ? 'ภาพมีลักษณะสอดคล้องกับ ${result.disease.displayName}'
                : 'ภาพมีลักษณะที่อาจสอดคล้องกับ ${result.disease.displayName}',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: ScanColors.text,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (!hasMetadata) ...[
            const SizedBox(height: 8),
            Text(
              'รายละเอียดสำหรับรายการนี้ยังไม่พร้อมใช้งาน',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ],
      ),
    );
  }
}

class _MetadataList extends StatelessWidget {
  const _MetadataList({
    required this.icon,
    required this.items,
    required this.emptyMessage,
  });

  final IconData icon;
  final List<String> items;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    return _TabSurface(
      icon: icon,
      child: items.isEmpty
          ? Text(
              emptyMessage,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: ScanColors.textSecondary),
            )
          : Column(
              children: [
                for (var index = 0; index < items.length; index++) ...[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 22,
                        height: 22,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: ScanColors.accent.withValues(alpha: 0.3),
                          shape: BoxShape.circle,
                        ),
                        child: Text(
                          '${index + 1}',
                          style: const TextStyle(
                            color: ScanColors.primary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
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

class _TabSurface extends StatelessWidget {
  const _TabSurface({required this.icon, required this.child});

  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: ScanColors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ScanColors.track),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: ScanColors.instruction,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: ScanColors.primary, size: 19),
          ),
          const SizedBox(width: 12),
          Expanded(child: child),
        ],
      ),
    );
  }
}

class _AiLimitationNote extends StatelessWidget {
  const _AiLimitationNote({this.showTitle = false});

  final bool showTitle;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: ScanColors.instruction,
        borderRadius: BorderRadius.circular(17),
        border: Border.all(color: ScanColors.track),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (showTitle) ...[
            Text(
              'ข้อจำกัดของผลจากระบบ',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: ScanColors.text,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
          ],
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.info_outline_rounded,
                size: 19,
                color: ScanColors.primary,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'ผลนี้เป็นการประเมินเบื้องต้นจากภาพด้วยระบบปัญญาประดิษฐ์ ไม่ใช่การตรวจวินิจฉัยหรือการยืนยันทางห้องปฏิบัติการ',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: ScanColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
