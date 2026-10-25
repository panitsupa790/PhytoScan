import 'package:flutter/material.dart';

import '../models/plant.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/plant_card.dart';
import 'analyze_screen.dart';

class PlantSelectionScreen extends StatefulWidget {
  const PlantSelectionScreen({super.key, required this.api, this.plants});

  final PhytoScanApi api;
  final Future<List<Plant>>? plants;

  @override
  State<PlantSelectionScreen> createState() => _PlantSelectionScreenState();
}

class _PlantSelectionScreenState extends State<PlantSelectionScreen> {
  late Future<List<Plant>> _plants;

  @override
  void initState() {
    super.initState();
    _plants = widget.plants ?? widget.api.fetchPlants();
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
    return Scaffold(
      appBar: AppBar(title: const Text('เลือกพืช')),
      body: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 14, 22, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'คุณกำลังตรวจพืชอะไร?',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 7),
              Text(
                'เลือกให้ตรงกับภาพ เพื่อใช้โมเดลวิเคราะห์ที่เหมาะสม',
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 28),
              Text('พืชทั้งหมด', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 14),
              Expanded(
                child: FutureBuilder<List<Plant>>(
                  future: _plants,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return Center(
                        child: TextButton.icon(
                          onPressed: () => setState(
                            () => _plants = widget.api.fetchPlants(),
                          ),
                          icon: const Icon(Icons.refresh_rounded),
                          label: const Text('โหลดไม่สำเร็จ ลองอีกครั้ง'),
                        ),
                      );
                    }
                    final plants = snapshot.data ?? const <Plant>[];
                    return ListView.separated(
                      itemCount: plants.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 12),
                      itemBuilder: (context, index) => PlantCard(
                        plant: plants[index],
                        compact: true,
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
    );
  }
}
