import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/plant_library.dart';
import '../services/api_service.dart';
import '../theme/home_design_tokens.dart';
import '../widgets/plant_visual.dart';

class PlantDetailScreen extends StatefulWidget {
  const PlantDetailScreen({
    super.key,
    required this.api,
    required this.plantCode,
    required this.onScan,
  });

  final PlantLibraryApi api;
  final String plantCode;
  final ValueChanged<PlantLibraryDetail> onScan;

  @override
  State<PlantDetailScreen> createState() => _PlantDetailScreenState();
}

class _PlantDetailScreenState extends State<PlantDetailScreen> {
  late Future<PlantLibraryDetail> _detail;

  @override
  void initState() {
    super.initState();
    _detail = widget.api.fetchPlantLibraryDetail(widget.plantCode);
  }

  void _retry() => setState(
    () => _detail = widget.api.fetchPlantLibraryDetail(widget.plantCode),
  );

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: HomeColors.background,
        body: FutureBuilder<PlantLibraryDetail>(
          future: _detail,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const ColoredBox(
                color: HomeColors.heroTop,
                child: Center(
                  child: CircularProgressIndicator(color: HomeColors.accent),
                ),
              );
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return SafeArea(
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.all(28),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.cloud_off_outlined,
                          size: 50,
                          color: HomeColors.primary,
                        ),
                        const SizedBox(height: 14),
                        Text(
                          'โหลดรายละเอียดพืชไม่สำเร็จ',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 18),
                        FilledButton.tonal(
                          onPressed: _retry,
                          child: const Text('ลองอีกครั้ง'),
                        ),
                        TextButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('ย้อนกลับ'),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }
            final plant = snapshot.data!;
            return _PlantDetailContent(
              plant: plant,
              onScan: () => widget.onScan(plant),
            );
          },
        ),
      ),
    );
  }
}

class _PlantDetailContent extends StatelessWidget {
  const _PlantDetailContent({required this.plant, required this.onScan});

  final PlantLibraryDetail plant;
  final VoidCallback onScan;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        CustomScrollView(
          slivers: [
            SliverAppBar(
              expandedHeight: 310,
              pinned: true,
              backgroundColor: HomeColors.heroTop,
              foregroundColor: HomeColors.white,
              title: Text(plant.nameTh),
              flexibleSpace: FlexibleSpaceBar(
                background: Stack(
                  fit: StackFit.expand,
                  children: [
                    Image.network(
                      plant.media.coverImage,
                      fit: BoxFit.cover,
                      semanticLabel: plant.media.coverAltTextTh,
                      errorBuilder: (_, _, _) =>
                          const PlantVisual(borderRadius: 0, iconSize: 70),
                    ),
                    const DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [Colors.transparent, Color(0xD91D3928)],
                        ),
                      ),
                    ),
                    Positioned(
                      left: 22,
                      right: 22,
                      bottom: 24,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            plant.nameTh,
                            style: Theme.of(context).textTheme.headlineMedium
                                ?.copyWith(
                                  color: HomeColors.white,
                                  fontWeight: FontWeight.w800,
                                ),
                          ),
                          Text(
                            plant.taxonomy.scientificName,
                            style: Theme.of(context).textTheme.bodyLarge
                                ?.copyWith(
                                  color: HomeColors.white.withValues(
                                    alpha: 0.82,
                                  ),
                                  fontStyle: FontStyle.italic,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(18, 20, 18, 116),
              sliver: SliverList.list(
                children: [
                  if (plant.review.status != 'verified') ...[
                    const _ReviewNotice(),
                    const SizedBox(height: 14),
                  ],
                  _SectionCard(
                    icon: Icons.eco_outlined,
                    title: 'รู้จักพืชชนิดนี้',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(plant.overview.summaryTh),
                        const SizedBox(height: 14),
                        _InfoRow(label: 'วงศ์', value: plant.taxonomy.family),
                        _InfoRow(label: 'สกุล', value: plant.taxonomy.genus),
                        _InfoRow(
                          label: 'ถิ่นกำเนิด',
                          value: plant.overview.origin,
                        ),
                        _InfoRow(
                          label: 'ลักษณะการเติบโต',
                          value: plant.overview.growthHabit,
                        ),
                        _InfoRow(
                          label: 'ความสูงโดยประมาณ',
                          value: plant.overview.height.format(suffix: ' ซม.'),
                        ),
                        if (plant.taxonomy.notes.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            plant.taxonomy.notes,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  _SectionCard(
                    icon: Icons.manage_search_rounded,
                    title: 'จุดสังเกตสำคัญ',
                    child: _BulletList(
                      items: plant.identification.distinguishingFeatures,
                    ),
                  ),
                  const SizedBox(height: 14),
                  _SectionCard(
                    icon: Icons.spa_outlined,
                    title: 'วิธีดูแล',
                    child: Column(
                      children: [
                        _CareRow(
                          icon: Icons.wb_sunny_outlined,
                          title: 'แสง',
                          value: plant.care.light.details,
                        ),
                        _CareRow(
                          icon: Icons.water_drop_outlined,
                          title: 'การรดน้ำ',
                          value: plant.care.watering.details,
                        ),
                        _CareRow(
                          icon: Icons.landscape_outlined,
                          title: 'ดิน',
                          value: plant.care.soil.details,
                        ),
                        _CareRow(
                          icon: Icons.thermostat_outlined,
                          title: 'อุณหภูมิ',
                          value:
                              '${plant.care.temperature.range.format(suffix: '°C')} — ${plant.care.temperature.details}',
                        ),
                        _CareRow(
                          icon: Icons.grass_outlined,
                          title: 'ปุ๋ย',
                          value: plant.care.fertilizer.details,
                        ),
                        _CareRow(
                          icon: Icons.content_cut_rounded,
                          title: 'ตัดแต่ง',
                          value: plant.care.pruning,
                          showDivider: false,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  _SectionCard(
                    icon: Icons.camera_alt_outlined,
                    title: 'ถ่ายภาพเพื่อวิเคราะห์',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'ควรถ่าย',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 7),
                        _BulletList(items: plant.scanGuidance.captureTips),
                        const SizedBox(height: 12),
                        Text(
                          'ควรหลีกเลี่ยง',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 7),
                        _BulletList(
                          items: plant.scanGuidance.avoid,
                          color: HomeColors.orange,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  _SectionCard(
                    icon: Icons.health_and_safety_outlined,
                    title: 'ความปลอดภัย',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _InfoRow(
                          label: 'สำหรับคน',
                          value: plant.safety.toxicityHumans,
                        ),
                        _InfoRow(
                          label: 'สำหรับสัตว์เลี้ยง',
                          value: plant.safety.toxicityPets,
                        ),
                        if (plant.safety.handlingNotes.isNotEmpty)
                          _BulletList(items: plant.safety.handlingNotes),
                      ],
                    ),
                  ),
                  if (plant.media.gallery.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    _GalleryCard(images: plant.media.gallery),
                  ],
                  const SizedBox(height: 14),
                  _SectionCard(
                    icon: Icons.menu_book_outlined,
                    title: 'แหล่งข้อมูล',
                    child: Column(
                      children: [
                        for (final source in plant.sources)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.open_in_new_rounded,
                                  size: 16,
                                  color: HomeColors.primary,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    source.title,
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodyMedium,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: HomeColors.surface,
              border: Border(top: BorderSide(color: HomeColors.subtleBorder)),
            ),
            child: SafeArea(
              top: false,
              minimum: const EdgeInsets.fromLTRB(18, 12, 18, 12),
              child: FilledButton.icon(
                onPressed: onScan,
                icon: const Icon(Icons.document_scanner_outlined),
                label: Text('ตรวจสุขภาพ${plant.nameTh}'),
                style: FilledButton.styleFrom(
                  backgroundColor: HomeColors.primary,
                  foregroundColor: HomeColors.white,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ReviewNotice extends StatelessWidget {
  const _ReviewNotice();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF3E9),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFFFD1B8)),
      ),
      child: const Row(
        children: [
          Icon(Icons.info_outline_rounded, color: HomeColors.orange),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'ข้อมูลนี้อยู่ระหว่างการตรวจทานโดยผู้เชี่ยวชาญ ใช้เพื่อการดูแลเบื้องต้นเท่านั้น',
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.icon,
    required this.title,
    required this.child,
  });

  final IconData icon;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: HomeColors.surface,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: HomeColors.subtleBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: HomeColors.accent.withValues(alpha: 0.22),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, size: 20, color: HomeColors.primary),
              ),
              const SizedBox(width: 11),
              Text(
                title,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: HomeColors.text,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          child,
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 112,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: HomeColors.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

class _BulletList extends StatelessWidget {
  const _BulletList({required this.items, this.color = HomeColors.primary});

  final List<String> items;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final item in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 7),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 7),
                  child: Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
                const SizedBox(width: 9),
                Expanded(child: Text(item)),
              ],
            ),
          ),
      ],
    );
  }
}

class _CareRow extends StatelessWidget {
  const _CareRow({
    required this.icon,
    required this.title,
    required this.value,
    this.showDivider = true,
  });

  final IconData icon;
  final String title;
  final String value;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 9),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 21, color: HomeColors.primary),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 3),
                    Text(value, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
            ],
          ),
        ),
        if (showDivider) const Divider(),
      ],
    );
  }
}

class _GalleryCard extends StatelessWidget {
  const _GalleryCard({required this.images});

  final List<PlantGalleryImage> images;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'รูปภาพเพิ่มเติม',
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 180,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: images.length,
            separatorBuilder: (_, _) => const SizedBox(width: 10),
            itemBuilder: (context, index) {
              final image = images[index];
              return ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: SizedBox(
                  width: 230,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Image.network(
                        image.image,
                        fit: BoxFit.cover,
                        semanticLabel: image.altTextTh,
                        errorBuilder: (_, _, _) =>
                            const PlantVisual(borderRadius: 0),
                      ),
                      Align(
                        alignment: Alignment.bottomCenter,
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(10),
                          color: HomeColors.heroTop.withValues(alpha: 0.78),
                          child: Text(
                            '${image.altTextTh} · ${image.attribution}',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: HomeColors.white,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
