import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/models/analysis_result.dart';

class ResultScreen extends StatefulWidget {
  final List<XFile> images;
  final AnalysisResult result;

  const ResultScreen({super.key, required this.images, required this.result});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  String _selectedTab = 'ผลวิเคราะห์';

  AnalysisResult get result => widget.result;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: const Color(0xFFF4F8F1),
      drawer: _buildDrawer(context),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        automaticallyImplyLeading: false,
        leading: Padding(
          padding: const EdgeInsets.all(8),
          child: Container(
            decoration: const BoxDecoration(
              color: Color(0xFF3F7F2B),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.eco, color: Colors.white, size: 18),
          ),
        ),
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'PhytoScan',
              style: TextStyle(
                color: Color(0xFF214D18),
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
            Text(
              'ระบบวินิจฉัยโรคพืชด้วย AI',
              style: TextStyle(color: Color(0xFF55734E), fontSize: 10),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'เปิดเมนู',
            icon: const Icon(Icons.menu, color: Color(0xFF2F6B1F)),
            onPressed: () => _scaffoldKey.currentState?.openDrawer(),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _buildSummaryCard(),
                  const SizedBox(height: 16),
                  _buildTabs(),
                  const SizedBox(height: 16),
                  _buildDetailCard(),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.of(context).popUntil((route) => route.isFirst);
                },
                icon: const Icon(Icons.refresh, color: Colors.white, size: 20),
                label: const Text(
                  'เริ่มวิเคราะห์ใหม่',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF3F7F2B),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15),
                  ),
                  elevation: 0,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCard() {
    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (widget.images.isNotEmpty) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.file(
                  File(widget.images.first.path),
                  height: 180,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => Container(
                    height: 180,
                    color: const Color(0xFFE5E7EB),
                    child: const Center(
                      child: Icon(Icons.broken_image_outlined, size: 42),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'วิเคราะห์จาก ${result.imageCount} ภาพ',
                style: const TextStyle(color: Color(0xFF55734E), fontSize: 12),
              ),
              const SizedBox(height: 12),
            ],
            Text(
              '${result.plant.nameTh} (${result.plant.nameEn})',
              style: const TextStyle(
                color: Color(0xFF55734E),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: const BoxDecoration(
                    color: Color(0xFFE6F4DF),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.eco_outlined,
                    color: Color(0xFF3F7F2B),
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    '${result.disease.nameTh} (${result.disease.nameEn})',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF214D18),
                    ),
                  ),
                ),
                const Icon(
                  Icons.check_circle,
                  color: Color(0xFF3F7F2B),
                  size: 20,
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.only(left: 44, top: 4),
              child: Text(
                'ความมั่นใจในการวิเคราะห์: ${_percentage(result.disease.confidence)}',
                style: const TextStyle(
                  color: Color(0xFF3F7F2B),
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTabs() {
    const tabs = ['ผลวิเคราะห์', 'อาการ', 'การดูแล', 'การป้องกัน'];
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(children: tabs.map(_buildTabButton).toList()),
    );
  }

  Widget _buildDetailCard() {
    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSelectedTabContent(),
            const SizedBox(height: 16),
            _buildNotice(),
          ],
        ),
      ),
    );
  }

  Widget _buildSelectedTabContent() {
    return switch (_selectedTab) {
      'อาการ' => _buildListSection(
        title: 'อาการของโรค',
        items: result.symptoms,
      ),
      'การดูแล' => _buildListSection(
        title: 'คำแนะนำการดูแล',
        items: result.care,
      ),
      'การป้องกัน' => _buildListSection(
        title: 'แนวทางป้องกัน',
        items: result.prevention,
      ),
      _ => _buildResultsLayout(),
    };
  }

  Widget _buildResultsLayout() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.info_outline, color: Color(0xFF3F7F2B), size: 20),
            SizedBox(width: 8),
            Text(
              'ผลการวินิจฉัย',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Color(0xFF214D18),
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _buildConfidenceRow(
          label: 'ความมั่นใจชนิดพืช',
          confidence: result.plant.confidence,
        ),
        const SizedBox(height: 18),
        _buildConfidenceRow(
          label: 'ความมั่นใจโรค',
          confidence: result.disease.confidence,
        ),
        const SizedBox(height: 24),
        const Text(
          'สรุป',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: Color(0xFF214D18),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'ระบบตรวจพบ ${result.disease.nameTh} ใน ${result.plant.nameTh}',
          style: const TextStyle(
            fontSize: 13,
            color: Color(0xFF4F6847),
            height: 1.5,
          ),
        ),
      ],
    );
  }

  Widget _buildConfidenceRow({
    required String label,
    required double confidence,
  }) {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
            ),
            Text(
              _percentage(confidence),
              style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF3F7F2B),
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: LinearProgressIndicator(
            value: confidence,
            minHeight: 8,
            backgroundColor: const Color(0xFFDDE8D6),
            valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF3F7F2B)),
          ),
        ),
      ],
    );
  }

  Widget _buildListSection({
    required String title,
    required List<String> items,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.info_outline, color: Color(0xFF3F7F2B), size: 20),
            const SizedBox(width: 8),
            Text(
              title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Color(0xFF214D18),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (items.isEmpty)
          const Text(
            'ยังไม่มีข้อมูลจากระบบวิเคราะห์',
            style: TextStyle(color: Color(0xFF6B7280)),
          )
        else
          for (final (index, item) in items.indexed)
            _buildListItem('${index + 1}', item),
      ],
    );
  }

  Widget _buildListItem(String number, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xFFE6F4DF),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 12,
              backgroundColor: const Color(0xFF3F7F2B),
              child: Text(
                number,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                text,
                style: const TextStyle(
                  fontSize: 13,
                  color: Color(0xFF214D18),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNotice() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFEEF5FF),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFD0E3FF)),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, color: Color(0xFF2F80ED), size: 20),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'ผลการวินิจฉัยนี้เป็นเพียงการประเมินเบื้องต้น หากมีข้อสงสัยควรปรึกษาผู้เชี่ยวชาญด้านพืชศาสตร์',
              style: TextStyle(
                fontSize: 12,
                color: Color(0xFF2F80ED),
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabButton(String tabName) {
    final isSelected = _selectedTab == tabName;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        selected: isSelected,
        label: Text(tabName),
        onSelected: (_) => setState(() => _selectedTab = tabName),
        selectedColor: const Color(0xFF3F7F2B),
        labelStyle: TextStyle(
          color: isSelected ? Colors.white : const Color(0xFF4F6847),
          fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        side: BorderSide(
          color: isSelected ? const Color(0xFF3F7F2B) : const Color(0xFFD3E5C8),
        ),
      ),
    );
  }

  Widget _buildDrawer(BuildContext context) {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          const DrawerHeader(
            decoration: BoxDecoration(color: Color(0xFF3F7F2B)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.eco, color: Colors.white, size: 40),
                SizedBox(height: 10),
                Text(
                  'PhytoScan Menu',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'ระบบวินิจฉัยโรคพืชด้วย AI',
                  style: TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ],
            ),
          ),
          ListTile(
            leading: const Icon(Icons.home_outlined, color: Color(0xFF3F7F2B)),
            title: const Text('หน้าหลัก'),
            onTap: () {
              Navigator.pop(context);
              Navigator.of(context).popUntil((route) => route.isFirst);
            },
          ),
          ListTile(
            leading: const Icon(
              Icons.history_outlined,
              color: Color(0xFF3F7F2B),
            ),
            title: const Text('ประวัติการสแกน'),
            onTap: () => Navigator.pop(context),
          ),
          ListTile(
            leading: const Icon(
              Icons.settings_outlined,
              color: Color(0xFF3F7F2B),
            ),
            title: const Text('ตั้งค่าระบบ'),
            onTap: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  String _percentage(double confidence) => '${(confidence * 100).round()}%';
}
