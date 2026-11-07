import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/plant.dart';
import '../models/plant_library.dart';
import '../services/api_service.dart';
import '../services/scan_history_store.dart';
import '../theme/app_theme.dart';
import '../theme/home_design_tokens.dart';
import '../widgets/plant_visual.dart';
import 'analyze_screen.dart';
import 'history_screen.dart';
import 'plant_selection_screen.dart';
import 'plant_detail_screen.dart';
import 'plant_library_screen.dart';
import 'profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.api,
    this.historyStore = const ScanHistoryStore(),
  });

  final PhytoScanApi api;
  final ScanHistoryRepository historyStore;

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

  void _retry() => setState(() => _plants = widget.api.fetchPlants());

  void _openScan() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) =>
            AnalyzeScreen(api: widget.api, historyStore: widget.historyStore),
      ),
    );
  }

  void _openPlantSelection() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PlantSelectionScreen(
          api: widget.api,
          plants: _plants,
          historyStore: widget.historyStore,
        ),
      ),
    );
  }

  void _openPlant(Plant plant) {
    final libraryApi = _libraryApi;
    if (libraryApi == null) {
      _openScanForPlant(plant);
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PlantDetailScreen(
          api: libraryApi,
          plantCode: plant.code,
          onScan: (_) => _openScanForPlant(plant),
        ),
      ),
    );
  }

  PlantLibraryApi? get _libraryApi =>
      widget.api is PlantLibraryApi ? widget.api as PlantLibraryApi : null;

  void _openScanForPlant(Plant plant) {
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

  void _openLibraryPlant(PlantLibrarySummary plant) {
    final libraryApi = _libraryApi;
    if (libraryApi == null) return;
    final scanPlant = Plant(
      code: plant.plantCode,
      nameTh: plant.nameTh,
      nameEn: plant.nameEn,
      diseaseCount: plant.supportedDiseaseCount,
    );
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PlantDetailScreen(
          api: libraryApi,
          plantCode: plant.plantCode,
          onScan: (_) => _openScanForPlant(scanPlant),
        ),
      ),
    );
  }

  void _selectTab(int index) {
    if (index == 2) {
      _openScan();
      return;
    }
    setState(() => _selectedIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    final usesDarkHero =
        _selectedIndex == 0 || _selectedIndex == 1 || _selectedIndex == 3;
    final libraryApi = _libraryApi;
    final pages = <Widget>[
      _Dashboard(
        plants: _plants,
        onRetry: _retry,
        onIdentify: _openScan,
        onDiagnose: _openPlantSelection,
        onPlant: _openPlant,
        onProfile: () => _selectTab(4),
      ),
      if (libraryApi != null)
        PlantLibraryScreen(api: libraryApi, onOpenPlant: _openLibraryPlant)
      else
        const _PlantLibraryUnavailable(),
      const SizedBox.shrink(),
      HistoryScreen(store: widget.historyStore),
      const ProfileScreen(),
    ];

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: usesDarkHero
          ? SystemUiOverlayStyle.light
          : SystemUiOverlayStyle.dark,
      child: Scaffold(
        backgroundColor: usesDarkHero
            ? HomeColors.heroTop
            : AppColors.background,
        body: SafeArea(child: pages[_selectedIndex]),
        bottomNavigationBar: _BottomBar(
          selectedIndex: _selectedIndex,
          onSelected: _selectTab,
        ),
      ),
    );
  }
}

class _Dashboard extends StatefulWidget {
  const _Dashboard({
    required this.plants,
    required this.onRetry,
    required this.onIdentify,
    required this.onDiagnose,
    required this.onPlant,
    required this.onProfile,
  });

  final Future<List<Plant>> plants;
  final VoidCallback onRetry;
  final VoidCallback onIdentify;
  final VoidCallback onDiagnose;
  final ValueChanged<Plant> onPlant;
  final VoidCallback onProfile;

  @override
  State<_Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<_Dashboard> {
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Plant> _filter(List<Plant> plants) {
    final query = _query.trim().toLowerCase();
    if (query.isEmpty) return plants;
    return plants
        .where((plant) {
          return plant.code.toLowerCase().contains(query) ||
              plant.nameTh.toLowerCase().contains(query) ||
              plant.nameEn.toLowerCase().contains(query);
        })
        .toList(growable: false);
  }

  void _clearSearch() {
    _searchController.clear();
    setState(() => _query = '');
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Plant>>(
      future: widget.plants,
      builder: (context, snapshot) {
        final plants = snapshot.data ?? const <Plant>[];
        final filteredPlants = _filter(plants);
        return CustomScrollView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          slivers: [
            SliverToBoxAdapter(
              child: _BotanicalHeader(
                plantCount: plants.length,
                controller: _searchController,
                query: _query,
                onChanged: (value) => setState(() => _query = value),
                onClear: _clearSearch,
                onProfile: widget.onProfile,
              ),
            ),
            SliverToBoxAdapter(
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Container(
                    constraints: const BoxConstraints(minHeight: 520),
                    color: HomeColors.surface,
                    padding: const EdgeInsets.fromLTRB(20, 50, 20, 36),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _ActionCard(
                          icon: Icons.center_focus_strong_rounded,
                          iconBackground: HomeColors.identifySoft,
                          iconColor: HomeColors.orange,
                          title: 'ระบุชนิดพืช',
                          subtitle:
                              'ให้ระบบจำแนกชนิดพืชจากภาพใบไม้โดยอัตโนมัติ',
                          buttonLabel: 'สแกนเพื่อระบุชนิด',
                          buttonKey: const Key('identifyPlantButton'),
                          onPressed: widget.onIdentify,
                        ),
                        const SizedBox(height: 12),
                        _ActionCard(
                          icon: Icons.health_and_safety_outlined,
                          iconBackground: HomeColors.diagnoseSoft,
                          iconColor: const Color(0xFF3F7187),
                          title: 'ตรวจโรคพืช',
                          subtitle:
                              'เลือกชนิดพืชก่อนตรวจอาการและจำแนกโรคจากภาพ',
                          buttonLabel: 'เลือกพืชเพื่อตรวจโรค',
                          buttonKey: const Key('diagnosePlantButton'),
                          onPressed: widget.onDiagnose,
                        ),
                        const SizedBox(height: 20),
                        _PhotographyTipsCard(
                          onTap: () => _showPhotographyTips(context),
                        ),
                        const SizedBox(height: 28),
                        _SectionTitle(
                          title: 'พืชที่รองรับ',
                          subtitle: _query.trim().isEmpty
                              ? 'แตะพืชเพื่อเริ่มตรวจโรคโดยระบุชนิดเอง'
                              : 'ผลการค้นหา “${_query.trim()}”',
                        ),
                        const SizedBox(height: 16),
                        if (snapshot.connectionState == ConnectionState.waiting)
                          const SizedBox(
                            height: 190,
                            child: Center(child: CircularProgressIndicator()),
                          )
                        else if (snapshot.hasError)
                          _InlineError(onRetry: widget.onRetry)
                        else if (plants.isEmpty)
                          const _EmptyPlants()
                        else if (filteredPlants.isEmpty)
                          _SearchEmpty(onClear: _clearSearch)
                        else
                          SizedBox(
                            height: 210,
                            child: ListView.separated(
                              key: const Key('supportedPlantGallery'),
                              scrollDirection: Axis.horizontal,
                              itemCount: filteredPlants.length,
                              separatorBuilder: (_, _) =>
                                  const SizedBox(width: 12),
                              itemBuilder: (context, index) {
                                final plant = filteredPlants[index];
                                return _SupportedPlantCard(
                                  plant: plant,
                                  onTap: () => widget.onPlant(plant),
                                );
                              },
                            ),
                          ),
                      ],
                    ),
                  ),
                  Positioned(
                    top: -5,
                    left: 0,
                    right: 0,
                    child: IgnorePointer(
                      child: Container(
                        height: 35,
                        decoration: BoxDecoration(
                          color: HomeColors.heroBottom,
                          borderRadius: const BorderRadius.vertical(
                            bottom: Radius.circular(25),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: HomeColors.primary.withValues(alpha: 0.12),
                              blurRadius: 10,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _BotanicalHeader extends StatelessWidget {
  const _BotanicalHeader({
    required this.plantCount,
    required this.controller,
    required this.query,
    required this.onChanged,
    required this.onClear,
    required this.onProfile,
  });

  final int plantCount;
  final TextEditingController controller;
  final String query;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;
  final VoidCallback onProfile;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            HomeColors.heroTop,
            HomeColors.heroBottom,
            HomeColors.heroBottom,
          ],
          stops: [0, 0.82, 1],
        ),
      ),
      child: Stack(
        children: [
          const Positioned.fill(
            child: IgnorePointer(child: CustomPaint(painter: _LeafPainter())),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(
                                Icons.eco_outlined,
                                size: 17,
                                color: HomeColors.accent,
                              ),
                              const SizedBox(width: 7),
                              Expanded(
                                child: Text(
                                  'สวัสดี ยินดีต้อนรับกลับ',
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: Theme.of(context).textTheme.bodyMedium
                                      ?.copyWith(
                                        color: HomeColors.white.withValues(
                                          alpha: 0.76,
                                        ),
                                        fontWeight: FontWeight.w500,
                                      ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'เข้าใจใบไม้\nดูแลได้อย่างมั่นใจ',
                            style: Theme.of(context).textTheme.headlineMedium
                                ?.copyWith(
                                  color: HomeColors.white,
                                  height: 1.18,
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'ด้วยการวิเคราะห์ที่เหมาะกับพืชของคุณ',
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(color: HomeColors.accent),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      key: const Key('homeProfileButton'),
                      tooltip: 'เปิดโปรไฟล์',
                      onPressed: onProfile,
                      style: IconButton.styleFrom(
                        backgroundColor: HomeColors.white.withValues(
                          alpha: 0.12,
                        ),
                        foregroundColor: HomeColors.white,
                        side: BorderSide(
                          color: HomeColors.white.withValues(alpha: 0.15),
                        ),
                      ),
                      icon: const Icon(Icons.person_outline_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final search = _PlantSearchField(
                      controller: controller,
                      query: query,
                      onChanged: onChanged,
                      onClear: onClear,
                    );
                    final count = _PlantCountChip(plantCount: plantCount);
                    if (constraints.maxWidth < 340) {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [search, const SizedBox(height: 8), count],
                      );
                    }
                    return Row(
                      children: [
                        Expanded(child: search),
                        const SizedBox(width: 10),
                        count,
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PlantSearchField extends StatelessWidget {
  const _PlantSearchField({
    required this.controller,
    required this.query,
    required this.onChanged,
    required this.onClear,
  });

  final TextEditingController controller;
  final String query;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return TextField(
      key: const Key('plantSearchField'),
      controller: controller,
      onChanged: onChanged,
      textInputAction: TextInputAction.search,
      style: const TextStyle(color: HomeColors.white),
      cursorColor: HomeColors.accent,
      decoration: InputDecoration(
        isDense: true,
        hintText: 'ค้นหาชื่อพืช',
        hintStyle: TextStyle(color: HomeColors.white.withValues(alpha: 0.68)),
        prefixIcon: const Icon(Icons.search_rounded, color: HomeColors.white),
        suffixIcon: query.isEmpty
            ? null
            : IconButton(
                tooltip: 'ล้างการค้นหา',
                onPressed: onClear,
                icon: const Icon(Icons.close_rounded, color: HomeColors.white),
              ),
        filled: true,
        fillColor: HomeColors.searchSurface,
        contentPadding: const EdgeInsets.symmetric(vertical: 14),
        border: _searchBorder(),
        enabledBorder: _searchBorder(),
        focusedBorder: _searchBorder(color: HomeColors.accent, width: 1.3),
      ),
    );
  }

  OutlineInputBorder _searchBorder({
    Color color = HomeColors.searchBorder,
    double width = 1,
  }) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(HomeRadii.control),
      borderSide: BorderSide(color: color, width: width),
    );
  }
}

class _PlantCountChip extends StatelessWidget {
  const _PlantCountChip({required this.plantCount});

  final int plantCount;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'รองรับพืช $plantCount ชนิด',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16.5, vertical: 16.5),
        decoration: BoxDecoration(
          color: HomeColors.accent,
          borderRadius: BorderRadius.circular(HomeRadii.control),
        ),
        child: Text(
          '$plantCount ชนิด',
          style: const TextStyle(
            color: HomeColors.primary,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.icon,
    required this.iconBackground,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.buttonLabel,
    required this.buttonKey,
    required this.onPressed,
  });

  final IconData icon;
  final Color iconBackground;
  final Color iconColor;
  final String title;
  final String subtitle;
  final String buttonLabel;
  final Key buttonKey;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: HomeColors.white,
        borderRadius: BorderRadius.circular(HomeRadii.card),
        border: Border.all(color: HomeColors.subtleBorder),
        boxShadow: [
          BoxShadow(
            color: HomeColors.primary.withValues(alpha: 0.05),
            blurRadius: 22,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: iconBackground,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(icon, color: iconColor),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: HomeColors.text,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: HomeColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              key: buttonKey,
              onPressed: onPressed,
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(48),
                backgroundColor: HomeColors.primary,
                foregroundColor: HomeColors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              icon: const Icon(Icons.arrow_forward_rounded, size: 19),
              label: Text(buttonLabel),
            ),
          ),
        ],
      ),
    );
  }
}

class _PhotographyTipsCard extends StatelessWidget {
  const _PhotographyTipsCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: HomeColors.tipSurface,
        borderRadius: BorderRadius.circular(HomeRadii.card),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.photo_camera_outlined,
                size: 20,
                color: HomeColors.accent,
              ),
              SizedBox(width: 8),
              Text(
                'คำแนะนำการถ่ายภาพ',
                style: TextStyle(
                  color: HomeColors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'ภาพใบไม้บนพื้นหลังเรียบและแสงสม่ำเสมอช่วยให้โมเดลทำงานตามขอบเขตที่ทดสอบไว้',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: HomeColors.white.withValues(alpha: 0.76),
            ),
          ),
          const SizedBox(height: 14),
          FilledButton(
            key: const Key('photographyTipsButton'),
            onPressed: onTap,
            style: FilledButton.styleFrom(
              minimumSize: const Size(0, 44),
              backgroundColor: HomeColors.orange,
              foregroundColor: HomeColors.white,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(15),
              ),
            ),
            child: const Text('ดูวิธีถ่าย'),
          ),
        ],
      ),
    );
  }
}

class _SupportedPlantCard extends StatelessWidget {
  const _SupportedPlantCard({required this.plant, required this.onTap});

  final Plant plant;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      key: ValueKey('supportedPlant-${plant.code}'),
      width: 154,
      child: Material(
        color: HomeColors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(HomeRadii.card),
          side: const BorderSide(color: HomeColors.subtleBorder),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Expanded(
                  child: PlantVisual(borderRadius: 17, iconSize: 42),
                ),
                const SizedBox(height: 9),
                Text(
                  plant.nameTh,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: HomeColors.text,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  'รองรับ ${plant.diseaseCount} อาการ',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: HomeColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: HomeColors.text,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: HomeColors.textSecondary),
        ),
      ],
    );
  }
}

class _SearchEmpty extends StatelessWidget {
  const _SearchEmpty({required this.onClear});

  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return _EmptyPanel(
      icon: Icons.search_off_rounded,
      title: 'ไม่พบพืชที่ค้นหา',
      message: 'ลองค้นหาด้วยชื่อพืชหรือรหัสพืช',
      action: TextButton(onPressed: onClear, child: const Text('ล้างการค้นหา')),
    );
  }
}

class _EmptyPlants extends StatelessWidget {
  const _EmptyPlants();

  @override
  Widget build(BuildContext context) {
    return const _EmptyPanel(
      icon: Icons.eco_outlined,
      title: 'ยังไม่มีรายการพืชที่รองรับ',
      message: 'รายการจะปรากฏเมื่อเชื่อมต่อกับเซิร์ฟเวอร์สำเร็จ',
    );
  }
}

class _EmptyPanel extends StatelessWidget {
  const _EmptyPanel({
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
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: HomeColors.background,
        borderRadius: BorderRadius.circular(HomeRadii.card),
      ),
      child: Column(
        children: [
          Icon(icon, color: HomeColors.primary, size: 32),
          const SizedBox(height: 10),
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (action != null) ...[const SizedBox(height: 6), action!],
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
    return _EmptyPanel(
      icon: Icons.cloud_off_outlined,
      title: 'โหลดรายการพืชไม่สำเร็จ',
      message: 'ตรวจสอบการเชื่อมต่อแล้วลองอีกครั้ง',
      action: TextButton(onPressed: onRetry, child: const Text('ลองอีกครั้ง')),
    );
  }
}

void _showPhotographyTips(BuildContext context) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: HomeColors.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(HomeRadii.sheet),
      ),
    ),
    builder: (context) => SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          24,
          12,
          24,
          24 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: HomeColors.subtleBorder,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'ถ่ายภาพให้พร้อมวิเคราะห์',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: HomeColors.text,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'โมเดลจำแนกชนิดพืชผ่านการประเมินภายใต้ภาพใบพืชที่มีพื้นหลังเรียบและควบคุมได้',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            const _TipRow(
              icon: Icons.filter_1_rounded,
              title: 'หนึ่งชนิดต่อหนึ่งชุดภาพ',
              message: 'อย่ารวมใบจากพืชต่างชนิดไว้ในการวิเคราะห์ครั้งเดียว',
            ),
            const _TipRow(
              icon: Icons.crop_free_rounded,
              title: 'ให้ใบไม้ชัดและอยู่กลางภาพ',
              message: 'วางใบให้เห็นรูปทรงและอาการสำคัญโดยไม่ถูกบัง',
            ),
            const _TipRow(
              icon: Icons.wallpaper_rounded,
              title: 'ใช้พื้นหลังเรียบ',
              message: 'หลีกเลี่ยงฉากธรรมชาติที่มีใบไม้หรือวัตถุอื่นปะปน',
            ),
            const _TipRow(
              icon: Icons.light_mode_outlined,
              title: 'ใช้แสงสม่ำเสมอ',
              message: 'หลีกเลี่ยงเงาเข้ม ภาพเบลอ และแสงสะท้อนบนใบ',
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                style: FilledButton.styleFrom(
                  backgroundColor: HomeColors.primary,
                  foregroundColor: HomeColors.white,
                ),
                child: const Text('เข้าใจแล้ว'),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class _TipRow extends StatelessWidget {
  const _TipRow({
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
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: HomeColors.identifySoft,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: HomeColors.orange, size: 21),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 2),
                Text(message, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LeafPainter extends CustomPainter {
  const _LeafPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = HomeColors.white.withValues(alpha: 0.035);
    canvas.save();
    canvas.translate(size.width * 0.79, -12);
    canvas.rotate(-0.28);
    for (var index = 0; index < 5; index++) {
      final offset = Offset(index * 16, index * 48);
      canvas.drawOval(
        Rect.fromCenter(center: offset, width: 86, height: 38),
        paint,
      );
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _PlantLibraryUnavailable extends StatelessWidget {
  const _PlantLibraryUnavailable();

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: HomeColors.background,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.menu_book_outlined,
                size: 48,
                color: HomeColors.primary,
              ),
              const SizedBox(height: 14),
              Text(
                'คลังพืชยังไม่พร้อมใช้งาน',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 5),
              const Text(
                'กรุณาเชื่อมต่อกับบริการข้อมูลคลังพืช',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
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
      (Icons.local_florist_outlined, 'คลังพืช'),
      (Icons.history_rounded, 'ประวัติ'),
      (Icons.person_outline_rounded, 'โปรไฟล์'),
    ];
    return ColoredBox(
      color: HomeColors.surface,
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 72,
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: Container(
                  key: const Key('bottomNavigationSurface'),
                  height: 50,
                  decoration: const BoxDecoration(
                    color: HomeColors.surface,
                    border: Border(
                      top: BorderSide(
                        color: HomeColors.subtleBorder,
                        width: 0.7,
                      ),
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: _NavItem(
                          icon: items[0].$1,
                          label: items[0].$2,
                          active: selectedIndex == 0,
                          onTap: () => onSelected(0),
                        ),
                      ),
                      Expanded(
                        child: _NavItem(
                          icon: items[1].$1,
                          label: items[1].$2,
                          active: selectedIndex == 1,
                          onTap: () => onSelected(1),
                        ),
                      ),
                      const Expanded(child: SizedBox.expand()),
                      Expanded(
                        child: _NavItem(
                          icon: items[2].$1,
                          label: items[2].$2,
                          active: selectedIndex == 3,
                          onTap: () => onSelected(3),
                        ),
                      ),
                      Expanded(
                        child: _NavItem(
                          icon: items[3].$1,
                          label: items[3].$2,
                          active: selectedIndex == 4,
                          onTap: () => onSelected(4),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Align(
                alignment: Alignment.topCenter,
                child: Semantics(
                  button: true,
                  label: 'สแกน',
                  child: Material(
                    key: const Key('floatingScanButton'),
                    color: HomeColors.surface,
                    shape: const CircleBorder(),
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: () => onSelected(2),
                      customBorder: const CircleBorder(),
                      child: Padding(
                        padding: const EdgeInsets.all(4),
                        child: DecoratedBox(
                          decoration: const BoxDecoration(
                            color: HomeColors.primary,
                            shape: BoxShape.circle,
                          ),
                          child: const SizedBox(
                            key: Key('floatingScanButtonFace'),
                            width: 44,
                            height: 44,
                            child: Icon(
                              Icons.document_scanner_outlined,
                              size: 22,
                              color: HomeColors.white,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
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
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = active ? HomeColors.primary : HomeColors.navInactive;
    return Semantics(
      selected: active,
      button: true,
      label: label,
      child: InkResponse(
        key: ValueKey('bottomNav-$label'),
        onTap: onTap,
        radius: 28,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 20, color: color),
            const SizedBox(height: 1),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.fade,
              softWrap: false,
              style: TextStyle(
                fontSize: 10,
                color: color,
                fontWeight: active ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            const SizedBox(height: 1),
            AnimatedOpacity(
              key: ValueKey('bottomNavIndicator-$label'),
              duration: const Duration(milliseconds: 160),
              opacity: active ? 1 : 0,
              child: Container(
                width: 3,
                height: 3,
                decoration: const BoxDecoration(
                  color: HomeColors.primary,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
