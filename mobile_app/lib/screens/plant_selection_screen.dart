import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/plant.dart';
import '../services/api_service.dart';
import '../services/scan_history_store.dart';
import '../theme/login_design_tokens.dart';
import 'analyze_screen.dart';

class PlantSelectionScreen extends StatefulWidget {
  const PlantSelectionScreen({
    super.key,
    required this.api,
    this.plants,
    this.returnSelection = false,
    this.historyStore = const ScanHistoryStore(),
  });

  final PhytoScanApi api;
  final Future<List<Plant>>? plants;
  final bool returnSelection;
  final ScanHistoryRepository historyStore;

  @override
  State<PlantSelectionScreen> createState() => _PlantSelectionScreenState();
}

class _PlantSelectionScreenState extends State<PlantSelectionScreen> {
  late Future<List<Plant>> _plants;
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void initState() {
    super.initState();
    _plants = widget.plants ?? widget.api.fetchPlants();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _openPlant(Plant plant) {
    if (widget.returnSelection) {
      Navigator.of(context).pop(plant);
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AnalyzeScreen(
          plant: plant,
          api: widget.api,
          historyStore: widget.historyStore,
        ),
      ),
    );
  }

  void _retry() => setState(() => _plants = widget.api.fetchPlants());

  List<Plant> _filtered(List<Plant> plants) {
    final query = _query.trim().toLowerCase();
    if (query.isEmpty) return plants;
    return plants
        .where((plant) {
          return plant.nameTh.toLowerCase().contains(query) ||
              plant.nameEn.toLowerCase().contains(query) ||
              plant.code.toLowerCase().contains(query);
        })
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: LoginColors.heroTop,
        body: Stack(
          children: [
            const Positioned.fill(child: _SelectionBackground()),
            SafeArea(
              bottom: false,
              child: Column(
                children: [
                  _SelectionHero(
                    returnSelection: widget.returnSelection,
                    onBack: () => Navigator.of(context).pop(),
                  ),
                  Expanded(
                    child: Container(
                      width: double.infinity,
                      decoration: const BoxDecoration(
                        color: LoginColors.sheetSurface,
                        borderRadius: BorderRadius.vertical(
                          top: Radius.circular(34),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.fromLTRB(20, 24, 20, 14),
                            child: _SearchField(
                              controller: _searchController,
                              onChanged: (value) =>
                                  setState(() => _query = value),
                              onClear: () {
                                _searchController.clear();
                                setState(() => _query = '');
                              },
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 22),
                            child: Row(
                              children: [
                                const Expanded(
                                  child: Text(
                                    'พืชที่รองรับ',
                                    style: TextStyle(
                                      color: LoginColors.primaryText,
                                      fontSize: 18,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                                FutureBuilder<List<Plant>>(
                                  future: _plants,
                                  builder: (context, snapshot) => Text(
                                    '${snapshot.data?.length ?? 0} ชนิด',
                                    style: const TextStyle(
                                      color: LoginColors.secondaryText,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                          Expanded(
                            child: FutureBuilder<List<Plant>>(
                              future: _plants,
                              builder: (context, snapshot) {
                                if (snapshot.connectionState ==
                                    ConnectionState.waiting) {
                                  return const _LoadingState();
                                }
                                if (snapshot.hasError) {
                                  return _ErrorState(onRetry: _retry);
                                }
                                final plants = _filtered(
                                  snapshot.data ?? const <Plant>[],
                                );
                                if (plants.isEmpty) {
                                  return const _EmptyState();
                                }
                                return ListView.separated(
                                  keyboardDismissBehavior:
                                      ScrollViewKeyboardDismissBehavior.onDrag,
                                  padding: const EdgeInsets.fromLTRB(
                                    20,
                                    0,
                                    20,
                                    28,
                                  ),
                                  itemCount: plants.length,
                                  separatorBuilder: (_, _) =>
                                      const SizedBox(height: 10),
                                  itemBuilder: (context, index) =>
                                      _PlantChoiceCard(
                                        plant: plants[index],
                                        onTap: () => _openPlant(plants[index]),
                                      ),
                                );
                              },
                            ),
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
    );
  }
}

class _SelectionBackground extends StatelessWidget {
  const _SelectionBackground();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
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
            right: -26,
            top: 24,
            child: Icon(
              Icons.eco_outlined,
              color: LoginColors.white.withValues(alpha: 0.07),
              size: 180,
            ),
          ),
        ],
      ),
    );
  }
}

class _SelectionHero extends StatelessWidget {
  const _SelectionHero({required this.returnSelection, required this.onBack});

  final bool returnSelection;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 192,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 8, 22, 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _CircleButton(icon: Icons.arrow_back_rounded, onTap: onBack),
                const Expanded(
                  child: Text(
                    'เลือกชนิดพืช',
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
              returnSelection
                  ? 'ยืนยันต้นไม้ให้ตรงกับภาพ'
                  : 'คุณกำลังตรวจพืชอะไร?',
              style: const TextStyle(
                color: LoginColors.white,
                fontSize: 26,
                height: 1.2,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              returnSelection
                  ? 'เลือกชนิดที่ถูกต้องก่อนส่งภาพเดิมกลับไปวิเคราะห์'
                  : 'เลือกให้ตรงกับภาพ เพื่อใช้โมเดลวิเคราะห์ที่เหมาะสม',
              style: TextStyle(
                color: LoginColors.white.withValues(alpha: 0.74),
                fontSize: 14,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CircleButton extends StatelessWidget {
  const _CircleButton({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: LoginColors.white.withValues(alpha: 0.13),
      shape: const CircleBorder(),
      child: InkWell(
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: SizedBox(
          width: 44,
          height: 44,
          child: Icon(icon, color: LoginColors.white, size: 22),
        ),
      ),
    );
  }
}

class _SearchField extends StatelessWidget {
  const _SearchField({
    required this.controller,
    required this.onChanged,
    required this.onClear,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      textInputAction: TextInputAction.search,
      decoration: InputDecoration(
        hintText: 'ค้นหาชื่อพืช',
        prefixIcon: const Icon(Icons.search_rounded, size: 21),
        suffixIcon: controller.text.isEmpty
            ? null
            : IconButton(
                onPressed: onClear,
                icon: const Icon(Icons.close_rounded, size: 20),
              ),
        filled: true,
        fillColor: LoginColors.white,
        contentPadding: const EdgeInsets.symmetric(vertical: 15),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: LoginColors.fieldBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: LoginColors.fieldBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(
            color: LoginColors.accentGreen,
            width: 1.4,
          ),
        ),
      ),
    );
  }
}

class _PlantChoiceCard extends StatelessWidget {
  const _PlantChoiceCard({required this.plant, required this.onTap});

  final Plant plant;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: LoginColors.white,
      borderRadius: BorderRadius.circular(22),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: LoginColors.fieldBorder),
          ),
          child: Row(
            children: [
              Container(
                width: 62,
                height: 62,
                decoration: BoxDecoration(
                  color: LoginColors.segmentTrack,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: const Icon(
                  Icons.eco_outlined,
                  color: LoginColors.primaryGreen,
                  size: 30,
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
                      style: const TextStyle(
                        color: LoginColors.primaryText,
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    const SizedBox(height: 5),
                    Text(
                      'รองรับ ${plant.diseaseCount} อาการ',
                      style: const TextStyle(
                        color: LoginColors.heroBottom,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                width: 36,
                height: 36,
                decoration: const BoxDecoration(
                  color: LoginColors.accentGreen,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.arrow_forward_rounded,
                  color: LoginColors.primaryGreen,
                  size: 19,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: CircularProgressIndicator(color: LoginColors.primaryGreen),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_outlined,
              color: LoginColors.secondaryText,
              size: 42,
            ),
            const SizedBox(height: 12),
            const Text('โหลดรายชื่อพืชไม่สำเร็จ'),
            const SizedBox(height: 10),
            TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('ลองอีกครั้ง'),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search_off_rounded,
              color: LoginColors.secondaryText,
              size: 40,
            ),
            SizedBox(height: 10),
            Text('ไม่พบพืชที่ค้นหา'),
          ],
        ),
      ),
    );
  }
}
