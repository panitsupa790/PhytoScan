import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/screens/analyzing_screen.dart';
import 'package:mobile_app/screens/login_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final ImagePicker _picker = ImagePicker();
  final List<XFile> _selectedImages = [];

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('isLoggedIn');

    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (context) => const LoginScreen()),
      (route) => false,
    );
  }

  Future<void> _pickImage(ImageSource source) async {
    if (_selectedImages.length >= 3) {
      _showSnackBar('คุณสามารถอัปโหลดรูปภาพได้สูงสุด 3 ภาพเท่านั้น');
      return;
    }

    try {
      final image = await _picker.pickImage(source: source, imageQuality: 80);
      if (image == null) return;

      setState(() => _selectedImages.add(image));
    } catch (error) {
      debugPrint('Error picking image: $error');
      _showSnackBar('ไม่สามารถเลือกรูปภาพได้ กรุณาลองอีกครั้ง');
    }
  }

  void _removeImage(int index) {
    setState(() => _selectedImages.removeAt(index));
  }

  Future<void> _analyzeSelectedImages() async {
    if (_selectedImages.isEmpty) {
      _showSnackBar('กรุณาเลือกภาพอย่างน้อย 1 ภาพ');
      return;
    }

    final images = List<XFile>.of(_selectedImages);
    setState(_selectedImages.clear);

    await Navigator.push<void>(
      context,
      MaterialPageRoute(builder: (context) => AnalyzingScreen(images: images)),
    );
  }

  void _showLogoutDialog() {
    showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          title: const Text(
            'ออกจากระบบ',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          content: const Text('คุณต้องการออกจากระบบใช่หรือไม่?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('ยกเลิก'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _logout();
              },
              child: const Text(
                'ยืนยัน',
                style: TextStyle(
                  color: Colors.redAccent,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      key: _scaffoldKey,
      endDrawer: _buildDrawer(),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFDFF1D8), Color(0xFFF4F8F1)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _buildHero(theme),
                      const SizedBox(height: 20),
                      _buildDiagnosisPanel(theme),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 12, 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFF3F7F2B),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.eco_rounded, color: Colors.white),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'PhytoScan',
                  style: TextStyle(
                    color: Color(0xFF214D18),
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  'ระบบวินิจฉัยโรคพืชด้วย AI',
                  style: TextStyle(color: Color(0xFF55734E), fontSize: 12),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.menu_rounded, color: Color(0xFF2F6B1F)),
            onPressed: () => _scaffoldKey.currentState?.openEndDrawer(),
          ),
        ],
      ),
    );
  }

  Widget _buildHero(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 88,
          height: 88,
          decoration: BoxDecoration(
            color: const Color(0xFFE6F4DF),
            borderRadius: BorderRadius.circular(28),
          ),
          child: const Icon(
            Icons.eco_rounded,
            size: 44,
            color: Color(0xFF2F6B1F),
          ),
        ),
        const SizedBox(height: 24),
        Text(
          'วิเคราะห์โรคพืชจากภาพ',
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.w800,
            color: const Color(0xFF214D18),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          'ถ่ายภาพหรืออัปโหลดภาพใบพืช เพื่อให้ระบบช่วยประเมินโรคเบื้องต้นและแสดงคำแนะนำการดูแล',
          style: theme.textTheme.bodyLarge?.copyWith(
            height: 1.5,
            color: const Color(0xFF55734E),
          ),
        ),
      ],
    );
  }

  Widget _buildDiagnosisPanel(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFD3E5C8)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Auto Diagnosis',
            style: theme.textTheme.titleLarge?.copyWith(
              color: const Color(0xFF214D18),
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'ถ่ายภาพใบพืชให้ชัด แสงเพียงพอ และมีพืชชนิดเดียวในภาพ',
            style: TextStyle(height: 1.5, color: Color(0xFF4F6847)),
          ),
          if (_selectedImages.isNotEmpty) ...[
            const SizedBox(height: 18),
            _buildSelectedImages(),
          ],
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: () => _pickImage(ImageSource.camera),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF3F7F2B),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 18),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(18),
              ),
            ),
            icon: const Icon(Icons.photo_camera_outlined),
            label: const Text(
              'ถ่ายภาพ',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => _pickImage(ImageSource.gallery),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF2F6B1F),
              side: const BorderSide(color: Color(0xFF8DBA7A)),
              padding: const EdgeInsets.symmetric(vertical: 18),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(18),
              ),
            ),
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text(
              'เลือกจากแกลเลอรี',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            'เพิ่มรูปภาพ (${_selectedImages.length}/3)',
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFF6D8367), fontSize: 12),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _selectedImages.isEmpty ? null : _analyzeSelectedImages,
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF214D18),
              foregroundColor: Colors.white,
              disabledBackgroundColor: const Color(0xFFDDE8D6),
              disabledForegroundColor: const Color(0xFF71816B),
              padding: const EdgeInsets.symmetric(vertical: 18),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(18),
              ),
            ),
            icon: const Icon(Icons.analytics_outlined),
            label: const Text(
              'วิเคราะห์ภาพ',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSelectedImages() {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _selectedImages.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
      ),
      itemBuilder: (context, index) {
        return Stack(
          children: [
            Positioned.fill(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(
                  File(_selectedImages[index].path),
                  fit: BoxFit.cover,
                ),
              ),
            ),
            Positioned(
              top: 4,
              right: 4,
              child: InkWell(
                onTap: () => _removeImage(index),
                borderRadius: BorderRadius.circular(999),
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: const BoxDecoration(
                    color: Colors.black54,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.close, size: 14, color: Colors.white),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildDrawer() {
    return Drawer(
      child: Column(
        children: [
          UserAccountsDrawerHeader(
            decoration: const BoxDecoration(color: Color(0xFF3F7F2B)),
            currentAccountPicture: const CircleAvatar(
              backgroundColor: Colors.white,
              child: Icon(Icons.person, size: 40, color: Color(0xFF3F7F2B)),
            ),
            accountName: const Text(
              'ผู้ใช้งาน PhytoScan',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            accountEmail: const Text('user@phytoscan.com'),
          ),
          ListTile(
            leading: const Icon(Icons.settings_outlined),
            title: const Text('ตั้งค่าระบบ'),
            onTap: () {},
          ),
          ListTile(
            leading: const Icon(Icons.help_outline),
            title: const Text('ความช่วยเหลือ'),
            onTap: () {},
          ),
          const Spacer(),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.redAccent),
            title: const Text(
              'ออกจากระบบ',
              style: TextStyle(
                color: Colors.redAccent,
                fontWeight: FontWeight.bold,
              ),
            ),
            onTap: () {
              Navigator.of(context).pop();
              _showLogoutDialog();
            },
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}
