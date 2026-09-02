import 'dart:io';

import 'package:flutter/material.dart';
import 'package:mobile_app/screens/result_screen.dart';

class AnalyzingScreen extends StatefulWidget {
  final File? imageFile;
  final VoidCallback onCancel;

  const AnalyzingScreen({
    super.key,
    required this.imageFile,
    required this.onCancel,
  });

  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(seconds: 3), () {
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => ResultScreen(imageFile: widget.imageFile),
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F8F1),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
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
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            _buildImageCard(),
            const SizedBox(height: 20),
            _buildAnalyzingCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildImageCard() {
    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Stack(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: widget.imageFile != null
                      ? Image.file(
                          widget.imageFile!,
                          height: 220,
                          width: double.infinity,
                          fit: BoxFit.cover,
                        )
                      : Container(
                          height: 220,
                          width: double.infinity,
                          color: const Color(0xFFE5E7EB),
                          child: const Icon(Icons.image, size: 50),
                        ),
                ),
                Positioned(
                  top: 12,
                  right: 12,
                  child: InkWell(
                    onTap: widget.onCancel,
                    borderRadius: BorderRadius.circular(999),
                    child: const CircleAvatar(
                      radius: 16,
                      backgroundColor: Colors.redAccent,
                      child: Icon(Icons.close, size: 18, color: Colors.white),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const Text(
              'อัปโหลดรูปภาพสำเร็จ',
              style: TextStyle(color: Color(0xFF6B7280), fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnalyzingCard() {
    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: const BoxDecoration(
                color: Color(0xFFE6F4DF),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.eco_outlined,
                size: 36,
                color: Color(0xFF3F7F2B),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'กำลังวิเคราะห์ด้วย AI...',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF214D18),
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'กรุณารอสักครู่',
              style: TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
            ),
            const SizedBox(height: 24),
            const LinearProgressIndicator(
              minHeight: 8,
              color: Color(0xFF3F7F2B),
              backgroundColor: Color(0xFFDDE8D6),
            ),
            const SizedBox(height: 24),
            const Text(
              'ระบบกำลังตรวจสอบลักษณะใบและประเมินโรคเบื้องต้น',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF55734E), height: 1.5),
            ),
          ],
        ),
      ),
    );
  }
}
