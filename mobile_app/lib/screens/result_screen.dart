import 'package:flutter/material.dart';
import 'dart:io';

class ResultScreen extends StatefulWidget {
  final File? imageFile;

  const ResultScreen({Key? key, required this.imageFile}) : super(key: key);

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  String _selectedTab = 'Results';
  
  // 1. เพิ่ม Key สำหรับควบคุมการเปิด-ปิด Drawer (เมนูด้านข้าง)
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey, // ผูก Key เข้ากับ Scaffold
      backgroundColor: const Color(0xfff8f9fa),
      
      // 2. เพิ่มแถบเมนูด้านข้าง (Drawer) เพื่อเวลาสไลด์หรือกดปุ่มแล้วให้มันแสดงผล
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(color: Color(0xff009688)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.spa, color: Colors.white, size: 40),
                  SizedBox(height: 10),
                  Text('PhytoScan Menu', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                  Text('ระบบวินิจฉัยโรคพืชด้วย AI', style: TextStyle(color: Colors.white70, fontSize: 12)),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.home_outlined, color: Color(0xff009688)),
              title: const Text('หน้าหลัก'),
              onTap: () {
                Navigator.pop(context); // ปิดเมนู
                Navigator.of(context).popUntil((route) => route.isFirst); // กลับหน้าแรก
              },
            ),
            ListTile(
              leading: const Icon(Icons.history_outlined, color: Color(0xff009688)),
              title: const Text('ประวัติการสแกน'),
              onTap: () => Navigator.pop(context),
            ),
            ListTile(
              leading: const Icon(Icons.settings_outlined, color: Color(0xff009688)),
              title: const Text('ตั้งค่าระบบ'),
              onTap: () => Navigator.pop(context),
            ),
          ],
        ),
      ),
      
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        automaticallyImplyLeading: false, // ปิดปุ่มย้อนกลับอัตโนมัติ เพื่อให้ Layout สวยงามตามเดิม
        leading: Padding(
          padding: const EdgeInsets.all(8.0),
          child: Container(
            padding: const EdgeInsets.all(4),
            decoration: const BoxDecoration(
              color: Color(0xff009688),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.spa, color: Colors.white, size: 16),
          ),
        ),
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'PhytoScan',
              style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 18),
            ),
            Text(
              'ระบบวินิจฉัยโรคพืชด้วย AI',
              style: TextStyle(color: Colors.grey, fontSize: 10),
            ),
          ],
        ),
        actions: [
          // 3. ปรับปรุงตรงนี้: เมื่อกดปุ่มแฮมเบอร์เกอร์ จะสั่งเปิด Drawer ด้านข้างทันที
          IconButton(
            icon: const Icon(Icons.menu, color: Colors.black54),
            onPressed: () {
              _scaffoldKey.currentState?.openDrawer(); // สั่งเปิดเมนูด้านข้างด้วย Key
            },
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1.0),
          child: Container(color: Colors.grey.withOpacity(0.2), height: 1.0),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (_selectedTab == 'Results') ...[
                    Card(
                      elevation: 1,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                      color: Colors.white,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: const BoxDecoration(
                                    color: Color(0xffe8f7f5),
                                    shape: BoxShape.circle,
                                  ),
                                  child: const Icon(Icons.spa_outlined, color: Color(0xff009688), size: 24),
                                ),
                                const SizedBox(width: 12),
                                const Expanded(
                                  child: Text(
                                    'โรคใบจุด (Leaf Spot)',
                                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.black87),
                                  ),
                                ),
                                const Icon(Icons.check_circle, color: Color(0xff009688), size: 20),
                              ],
                            ),
                            const Padding(
                              padding: EdgeInsets.only(left: 44.0, top: 4),
                              child: Text(
                                'ตรวจพบอัตโนมัติ: สูง',
                                style: TextStyle(color: Color(0xff009688), fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                            const SizedBox(height: 12),
                            const Text(
                              'โรคที่ทำให้เกิดจุดสีน้ำตาลหรือสีดำบนใบพืช ซึ่งอาจขยายและรวมกันเป็นแผลขนาดใหญ่ ส่งผลให้ใบเหลืองและร่วงหล่นได้ มักเกิดจากเชื้อราหลายชนิด',
                              style: TextStyle(fontSize: 13, color: Colors.black54, height: 1.5),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildTabButton('Results'),
                        _buildTabButton('Symptoms'),
                        _buildTabButton('Care'),
                        _buildTabButton('Protection'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  Card(
                    elevation: 1,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    color: Colors.white,
                    child: Padding(
                      padding: const EdgeInsets.all(20.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _selectedTab == 'Symptoms'
                              ? _buildSymptomsLayout() 
                              : _buildResultsLayout(),

                          const SizedBox(height: 16),
                          
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: const Color(0xffeef5ff),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xffd0e3ff)),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(Icons.info_outline, color: Color(0xff2f80ed), size: 20),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'หมายเหตุ',
                                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xff2f80ed)),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        _selectedTab == 'Symptoms'
                                            ? 'ผลการวินิจฉัยนี้เป็นเพียงการประเมินเบื้องต้นเท่านั้น หากมีข้อสงสัยควรปรึกษาผู้เชี่ยวชาญด้านพืชศาสตร์'
                                            : 'ผลการวินิจฉัยนี้เป็นเพียงการประเมินเบื้องต้นเท่านั้น หากมีข้อสงสัยควรปรึกษาผู้เชี่ยวชาญด้านพืชศาสตร์ หรือเกษตรกรที่มีประสบการณ์เพื่อยืนยันผลและให้คำปรึกษาเพิ่มเติม',
                                        style: const TextStyle(fontSize: 12, color: Color(0xff2f80ed), height: 1.5),
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
                  ),
                ],
              ),
            ),
          ),
          
          Padding(
            padding: const EdgeInsets.all(20.0),
            child: SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.of(context).popUntil((route) => route.isFirst);
                },
                icon: const Icon(Icons.refresh, color: Colors.white, size: 20),
                label: const Text('Start New Diagnosis', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xff009688),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                  elevation: 0,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResultsLayout() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.info_outline, color: Color(0xff009688), size: 20),
            SizedBox(width: 8),
            Text('ผลการวินิจฉัย', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.black87)),
          ],
        ),
        const SizedBox(height: 16),
        const Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Confidence Level', style: TextStyle(fontSize: 12, color: Colors.grey)),
            Text('84%', style: TextStyle(fontSize: 12, color: Color(0xff009688), fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: const LinearProgressIndicator(
            value: 0.84,
            minHeight: 8,
            backgroundColor: Color(0xffe0e0e0),
            valueColor: AlwaysStoppedAnimation<Color>(Color(0xff009688)),
          ),
        ),
        const SizedBox(height: 24),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: const Color(0xfff8f9fa), borderRadius: BorderRadius.circular(16)),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('สรุป', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black87)),
              SizedBox(height: 8),
              Text(
                'โรคที่ทำให้เกิดจุดสีน้ำตาลหรือสีดำบนใบพืช ซึ่งอาจขยายและรวมกันเป็นแผลขนาดใหญ่ ส่งผลให้ใบเหลืองและร่วงหล่นได้ มักเกิดจากเชื้อราหลายชนิด',
                style: TextStyle(fontSize: 13, color: Colors.black54, height: 1.5),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSymptomsLayout() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.info_outline, color: Color(0xff009688), size: 20),
            SizedBox(width: 8),
            Text('อาการของโรค', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.black87)),
          ],
        ),
        const SizedBox(height: 16),
        _buildSymptomItem('1', 'ใบมีจุดสีน้ำตาลหรือสีดำที่มีขอบชัดเจน'),
        _buildSymptomItem('2', 'จุดอาจมีวงแหวนหลายวงรอบๆ'),
        _buildSymptomItem('3', 'ใบเหลืองรอบบริเวณที่เป็นโรค'),
        _buildSymptomItem('4', 'ใบเเห้งหล่นก่อนกำหนด'),
        _buildSymptomItem('5', 'จุดอาจรวมตัวกันเป็นแผลใหญ่'),
      ],
    );
  }

  Widget _buildSymptomItem(String number, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10.0),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xffe8f7f5).withOpacity(0.4),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 12,
              backgroundColor: const Color(0xff009688),
              child: Text(number, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                text,
                style: const TextStyle(fontSize: 13, color: Colors.black87, fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTabButton(String tabName) {
    bool isSelected = _selectedTab == tabName;
    return Padding(
      padding: const EdgeInsets.only(right: 8.0),
      child: GestureDetector(
        onTap: () {
          setState(() {
            _selectedTab = tabName;
          });
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xff009688) : Colors.transparent,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: isSelected ? const Color(0xff009688) : Colors.grey.withOpacity(0.3)),
          ),
          child: Text(
            tabName,
            style: TextStyle(
              color: isSelected ? Colors.white : Colors.black54,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }
}