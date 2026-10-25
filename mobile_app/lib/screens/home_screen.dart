import 'package:flutter/material.dart';

import '../models/plant.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/plant_card.dart';
import '../widgets/plant_visual.dart';
import '../widgets/section_header.dart';
import 'analyze_screen.dart';
import 'plant_selection_screen.dart';
import 'profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.api});

  final PhytoScanApi api;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<Plant>> _plants;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _plants = widget.api.fetchPlants();
  }

  void _retry() {
    setState(() => _plants = widget.api.fetchPlants());
  }

  void _openScan() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PlantSelectionScreen(api: widget.api, plants: _plants),
      ),
    );
  }

  void _openPlant(Plant plant) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AnalyzeScreen(plant: plant, api: widget.api),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      _Dashboard(
        plants: _plants,
        onRetry: _retry,
        onScan: _openScan,
        onPlant: _openPlant,
      ),
      const SizedBox.shrink(),
      const _FutureFeature(
        icon: Icons.spa_outlined,
        title: 'ต้นไม้ของฉัน',
        message: 'เพิ่มต้นไม้และติดตามสุขภาพย้อนหลังได้ในเวอร์ชันถัดไป',
      ),
      const ProfileScreen(),
    ];

    return Scaffold(
      body: SafeArea(child: pages[_selectedIndex]),
      bottomNavigationBar: _BottomBar(
        selectedIndex: _selectedIndex,
        onSelected: (index) {
          if (index == 1) {
            _openScan();
            return;
          }
          setState(() => _selectedIndex = index);
        },
      ),
    );
  }
}

class _Dashboard extends StatelessWidget {
  const _Dashboard({
    required this.plants,
    required this.onRetry,
    required this.onScan,
    required this.onPlant,
  });

  final Future<List<Plant>> plants;
  final VoidCallback onRetry;
  final VoidCallback onScan;
  final ValueChanged<Plant> onPlant;

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: [
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(22, 24, 22, 30),
          sliver: SliverList.list(
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'สวัสดี 👋',
                          style: Theme.of(context).textTheme.bodyLarge
                              ?.copyWith(color: AppColors.textSecondary),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'วันนี้ต้นไม้ของคุณ\nเป็นอย่างไรบ้าง?',
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 46,
                    height: 46,
                    decoration: const BoxDecoration(
                      color: AppColors.surface,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.eco_rounded,
                      color: AppColors.primary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 28),
              _ScanHero(onTap: onScan),
              const SizedBox(height: 32),
              SectionHeader(
                title: 'พืชที่รองรับ',
                subtitle: 'เลือกพืชเพื่อเริ่มตรวจอาการ',
                action: TextButton(
                  onPressed: onScan,
                  child: const Text('ดูทั้งหมด'),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                height: 252,
                child: FutureBuilder<List<Plant>>(
                  future: plants,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return _InlineError(onRetry: onRetry);
                    }
                    final rows = snapshot.data ?? const <Plant>[];
                    if (rows.isEmpty) {
                      return const Center(child: Text('ยังไม่มีพืชที่รองรับ'));
                    }
                    return ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: rows.length,
                      separatorBuilder: (_, _) => const SizedBox(width: 14),
                      itemBuilder: (context, index) => SizedBox(
                        width: 176,
                        child: PlantCard(
                          plant: rows[index],
                          onTap: () => onPlant(rows[index]),
                        ),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 34),
              const SectionHeader(title: 'สุขภาพล่าสุด'),
              const SizedBox(height: 14),
              const _EmptyHistory(),
            ],
          ),
        ),
      ],
    );
  }
}

class _ScanHero extends StatelessWidget {
  const _ScanHero({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.darkGreen,
        borderRadius: BorderRadius.circular(26),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ตรวจสุขภาพต้นไม้',
                  style: Theme.of(
                    context,
                  ).textTheme.headlineSmall?.copyWith(color: Colors.white),
                ),
                const SizedBox(height: 7),
                Text(
                  'ถ่ายภาพเพื่อวิเคราะห์\nอาการเบื้องต้น',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white.withValues(alpha: 0.76),
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: onTap,
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(0, 44),
                    backgroundColor: Colors.white,
                    foregroundColor: AppColors.darkGreen,
                    padding: const EdgeInsets.symmetric(horizontal: 17),
                  ),
                  icon: const Icon(Icons.document_scanner_outlined, size: 19),
                  label: const Text('เริ่ม Scan'),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          const SizedBox(
            width: 112,
            height: 154,
            child: PlantVisual(iconSize: 54, borderRadius: 22),
          ),
        ],
      ),
    );
  }
}

class _EmptyHistory extends StatelessWidget {
  const _EmptyHistory();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppColors.divider, width: 0.6),
      ),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: const BoxDecoration(
              color: AppColors.paleGreen,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.history_rounded, color: AppColors.primary),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ยังไม่มีผลล่าสุด',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 3),
                Text(
                  'ผลการตรวจจะปรากฏที่นี่เมื่อเปิดใช้งานประวัติ',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('โหลดรายการพืชไม่สำเร็จ'),
          TextButton(onPressed: onRetry, child: const Text('ลองอีกครั้ง')),
        ],
      ),
    );
  }
}

class _FutureFeature extends StatelessWidget {
  const _FutureFeature({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 78,
            height: 78,
            decoration: const BoxDecoration(
              color: AppColors.paleGreen,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 38, color: AppColors.primary),
          ),
          const SizedBox(height: 20),
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _BottomBar extends StatelessWidget {
  const _BottomBar({required this.selectedIndex, required this.onSelected});

  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    const items = [
      (Icons.home_rounded, 'หน้าหลัก'),
      (Icons.document_scanner_outlined, 'Scan'),
      (Icons.spa_outlined, 'ต้นไม้'),
      (Icons.person_outline_rounded, 'โปรไฟล์'),
    ];
    return SafeArea(
      top: false,
      child: Container(
        height: 72,
        decoration: const BoxDecoration(
          color: AppColors.surface,
          border: Border(top: BorderSide(color: AppColors.divider, width: 0.6)),
        ),
        child: Row(
          children: [
            for (var index = 0; index < items.length; index++)
              Expanded(
                child: _NavItem(
                  icon: items[index].$1,
                  label: items[index].$2,
                  active: index == selectedIndex,
                  emphasized: index == 1,
                  onTap: () => onSelected(index),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.active,
    required this.emphasized,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool active;
  final bool emphasized;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = active ? AppColors.primary : AppColors.textSecondary;
    return InkResponse(
      onTap: onTap,
      radius: 32,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: EdgeInsets.all(emphasized ? 8 : 3),
            decoration: emphasized
                ? const BoxDecoration(
                    color: AppColors.softGreen,
                    shape: BoxShape.circle,
                  )
                : null,
            child: Icon(icon, size: emphasized ? 23 : 22, color: color),
          ),
          const SizedBox(height: 3),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: color,
              fontWeight: active ? FontWeight.w600 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
