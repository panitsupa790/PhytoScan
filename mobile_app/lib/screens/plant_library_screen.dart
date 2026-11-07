import 'package:flutter/material.dart';

import '../models/plant_library.dart';
import '../services/api_service.dart';
import '../theme/home_design_tokens.dart';
import '../widgets/plant_visual.dart';

class PlantLibraryScreen extends StatefulWidget {
  const PlantLibraryScreen({
    super.key,
    required this.api,
    required this.onOpenPlant,
  });

  final PlantLibraryApi api;
  final ValueChanged<PlantLibrarySummary> onOpenPlant;

  @override
  State<PlantLibraryScreen> createState() => _PlantLibraryScreenState();
}

class _PlantLibraryScreenState extends State<PlantLibraryScreen> {
  late Future<List<PlantLibrarySummary>> _plants;
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void initState() {
    super.initState();
    _plants = widget.api.fetchPlantLibrary();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _retry() => setState(() => _plants = widget.api.fetchPlantLibrary());

  List<PlantLibrarySummary> _filter(List<PlantLibrarySummary> plants) {
    final query = _query.trim().toLowerCase();
    if (query.isEmpty) return plants;
    return plants
        .where(
          (plant) =>
              plant.nameTh.toLowerCase().contains(query) ||
              plant.nameEn.toLowerCase().contains(query) ||
              plant.scientificName.toLowerCase().contains(query),
        )
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [HomeColors.heroTop, HomeColors.heroBottom],
        ),
      ),
      child: Stack(
        children: [
          const Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(painter: _PlantLibraryBotanicalPainter()),
            ),
          ),
          Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            color: HomeColors.white.withValues(alpha: 0.12),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.local_florist_outlined,
                            color: HomeColors.white,
                          ),
                        ),
                        const SizedBox(width: 13),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'คลังพืช',
                                style: Theme.of(context).textTheme.headlineSmall
                                    ?.copyWith(
                                      color: HomeColors.white,
                                      fontWeight: FontWeight.w800,
                                    ),
                              ),
                              Text(
                                'ข้อมูลพืชและวิธีดูแลเบื้องต้น',
                                style: Theme.of(context).textTheme.bodyMedium
                                    ?.copyWith(
                                      color: HomeColors.white.withValues(
                                        alpha: 0.72,
                                      ),
                                    ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    TextField(
                      key: const Key('plantLibrarySearch'),
                      controller: _searchController,
                      onChanged: (value) => setState(() => _query = value),
                      style: const TextStyle(color: HomeColors.white),
                      decoration: InputDecoration(
                        hintText: 'ค้นหาชื่อไทย อังกฤษ หรือชื่อวิทยาศาสตร์',
                        hintStyle: TextStyle(
                          color: HomeColors.white.withValues(alpha: 0.62),
                        ),
                        prefixIcon: const Icon(
                          Icons.search_rounded,
                          color: HomeColors.white,
                        ),
                        suffixIcon: _query.isEmpty
                            ? null
                            : IconButton(
                                onPressed: () {
                                  _searchController.clear();
                                  setState(() => _query = '');
                                },
                                icon: const Icon(
                                  Icons.close_rounded,
                                  color: HomeColors.white,
                                ),
                              ),
                        filled: true,
                        fillColor: HomeColors.searchSurface,
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18),
                          borderSide: const BorderSide(
                            color: HomeColors.searchBorder,
                          ),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18),
                          borderSide: const BorderSide(
                            color: HomeColors.accent,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Container(
                  width: double.infinity,
                  decoration: const BoxDecoration(
                    color: HomeColors.background,
                    borderRadius: BorderRadius.vertical(
                      top: Radius.circular(30),
                    ),
                  ),
                  child: FutureBuilder<List<PlantLibrarySummary>>(
                    future: _plants,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (snapshot.hasError) {
                        return _LibraryMessage(
                          icon: Icons.cloud_off_outlined,
                          title: 'เปิดคลังพืชไม่สำเร็จ',
                          message: 'ตรวจสอบการเชื่อมต่อแล้วลองอีกครั้ง',
                          action: FilledButton.tonal(
                            onPressed: _retry,
                            child: const Text('ลองอีกครั้ง'),
                          ),
                        );
                      }
                      final filtered = _filter(snapshot.data ?? const []);
                      if (filtered.isEmpty) {
                        return const _LibraryMessage(
                          icon: Icons.search_off_rounded,
                          title: 'ไม่พบพืชที่ค้นหา',
                          message: 'ลองค้นหาด้วยชื่ออื่น',
                        );
                      }
                      return ListView.separated(
                        key: const Key('plantLibraryList'),
                        padding: const EdgeInsets.fromLTRB(18, 24, 18, 28),
                        itemCount: filtered.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final plant = filtered[index];
                          return _PlantLibraryCard(
                            plant: plant,
                            onTap: () => widget.onOpenPlant(plant),
                          );
                        },
                      );
                    },
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

class _PlantLibraryCard extends StatelessWidget {
  const _PlantLibraryCard({required this.plant, required this.onTap});

  final PlantLibrarySummary plant;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      key: ValueKey('plantLibrary-${plant.plantCode}'),
      color: HomeColors.surface,
      borderRadius: BorderRadius.circular(22),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            border: Border.all(color: HomeColors.subtleBorder),
            borderRadius: BorderRadius.circular(22),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(17),
                child: SizedBox(
                  width: 96,
                  height: 112,
                  child: Image.network(
                    plant.coverImage,
                    fit: BoxFit.cover,
                    semanticLabel: plant.coverAltTextTh,
                    errorBuilder: (_, _, _) =>
                        const PlantVisual(borderRadius: 0, iconSize: 38),
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      plant.nameTh,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: HomeColors.text,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      plant.scientificName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontStyle: FontStyle.italic,
                        color: HomeColors.primary,
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      plant.summaryTh,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(
                          Icons.health_and_safety_outlined,
                          size: 15,
                          color: HomeColors.primary,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          'ข้อมูลอาการ ${plant.supportedDiseaseCount} รายการ',
                          style: Theme.of(context).textTheme.labelMedium
                              ?.copyWith(color: HomeColors.primary),
                        ),
                        const Spacer(),
                        const Icon(
                          Icons.chevron_right_rounded,
                          color: HomeColors.primary,
                        ),
                      ],
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

class _LibraryMessage extends StatelessWidget {
  const _LibraryMessage({
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 46, color: HomeColors.primary),
            const SizedBox(height: 14),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 5),
            Text(message, textAlign: TextAlign.center),
            if (action != null) ...[const SizedBox(height: 18), action!],
          ],
        ),
      ),
    );
  }
}

class _PlantLibraryBotanicalPainter extends CustomPainter {
  const _PlantLibraryBotanicalPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final leafPaint = Paint()..color = HomeColors.white.withValues(alpha: 0.04);
    final stemPaint = Paint()
      ..color = HomeColors.accent.withValues(alpha: 0.16)
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;

    canvas.save();
    canvas.translate(size.width * 0.76, -20);
    canvas.rotate(-0.3);
    canvas.drawLine(const Offset(12, 0), const Offset(12, 285), stemPaint);
    for (var index = 0; index < 6; index++) {
      final y = 26.0 + (index * 43);
      final isLeft = index.isEven;
      final center = Offset(isLeft ? -20 : 44, y);
      canvas.drawOval(
        Rect.fromCenter(center: center, width: 86, height: 36),
        leafPaint,
      );
      canvas.drawLine(Offset(12, y), center, stemPaint);
    }
    canvas.restore();

    final glowPaint = Paint()
      ..color = HomeColors.accent.withValues(alpha: 0.045);
    canvas.drawCircle(Offset(size.width * 0.08, 34), 74, glowPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
