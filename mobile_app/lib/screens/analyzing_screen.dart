import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_app/screens/result_screen.dart';
import 'package:mobile_app/services/analysis_api_service.dart';

class AnalyzingScreen extends StatefulWidget {
  final List<XFile> images;
  final AnalysisService? analysisService;

  const AnalyzingScreen({
    super.key,
    required this.images,
    this.analysisService,
  });

  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen> {
  late final AnalysisService _analysisService;
  bool _isLoading = true;
  AnalysisApiException? _error;

  @override
  void initState() {
    super.initState();
    _analysisService = widget.analysisService ?? const AnalysisApiService();
    WidgetsBinding.instance.addPostFrameCallback((_) => _analyze());
  }

  Future<void> _analyze() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final result = await _analysisService.analyze(widget.images);
      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) =>
              ResultScreen(images: widget.images, result: result),
        ),
      );
    } on AnalysisApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = error;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = const AnalysisApiException(
          errorCode: 'UNKNOWN_ERROR',
          userMessage: 'เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง',
        );
      });
    }
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
            _isLoading ? _buildLoadingCard() : _buildErrorCard(),
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
            ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Image.file(
                File(widget.images.first.path),
                height: 220,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => Container(
                  height: 220,
                  width: double.infinity,
                  color: const Color(0xFFE5E7EB),
                  child: const Icon(Icons.broken_image_outlined, size: 50),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'กำลังวิเคราะห์ ${widget.images.length} ภาพ',
              style: const TextStyle(color: Color(0xFF55734E)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingCard() {
    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const CircularProgressIndicator(color: Color(0xFF3F7F2B)),
            const SizedBox(height: 20),
            const Text(
              'กำลังวิเคราะห์ภาพ',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF214D18),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'กำลังส่งภาพและรอผลจากเซิร์ฟเวอร์',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF55734E), height: 1.5),
            ),
            const SizedBox(height: 20),
            TextButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.arrow_back),
              label: const Text('กลับไปเลือกภาพใหม่'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorCard() {
    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Icon(Icons.error_outline, color: Color(0xFFB42318), size: 48),
            const SizedBox(height: 16),
            const Text(
              'วิเคราะห์ภาพไม่สำเร็จ',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF214D18),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _error?.userMessage ?? 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF55734E), height: 1.5),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _analyze,
                icon: const Icon(Icons.refresh),
                label: const Text('ลองวิเคราะห์อีกครั้ง'),
              ),
            ),
            TextButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.arrow_back),
              label: const Text('กลับไปเลือกภาพใหม่'),
            ),
          ],
        ),
      ),
    );
  }
}
