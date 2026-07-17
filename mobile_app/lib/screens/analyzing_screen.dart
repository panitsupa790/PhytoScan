import 'package:flutter/material.dart';
import 'dart:io';
import 'result_screen.dart'; // อย่าลืมตรวจสอบว่าอิมพอร์ตหน้า ResultScreen ถูกต้องนะครับ

class AnalyzingScreen extends StatefulWidget {
  final File? imageFile;       // รับไฟล์รูปภาพจริงมาจากหน้า Home
  final VoidCallback onCancel; // ฟังก์ชันเวลากดปุ่มลบ (X)

  const AnalyzingScreen({
    Key? key, 
    required this.imageFile, 
    required this.onCancel,
  }) : super(key: key);

  @override
  State<AnalyzingScreen> createState() => _AnalyzingScreenState();
}

class _AnalyzingScreenState extends State<AnalyzingScreen> {
  
  @override
  void initState() {
    super.initState();
    // จำลองเวลา 3 วินาทีในการวิเคราะห์ข้อมูล จากนั้นจะเด้งไปหน้าแสดงผลลัพธ์อัตโนมัติ
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => ResultScreen(imageFile: widget.imageFile),
          ),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xfff8f9fa),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
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
              style: TextStyle(
                color: Colors.black, 
                fontWeight: FontWeight.bold, 
                fontSize: 18,
              ),
            ),
            Text(
              'ระบบวินิจฉัยโรคพืชด้วย AI',
              style: TextStyle(color: Colors.grey, fontSize: 10),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.menu, color: Colors.black54),
            onPressed: () {},
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1.0),
          child: Container(color: Colors.grey.withOpacity(0.2), height: 1.0),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
        child: Column(
          children: [
            // --- การ์ดบน: แสดงรูปพืชที่อัปโหลด ---
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(24.0),
              ),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Stack(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(20.0),
                          child: widget.imageFile != null
                              ? Image.file(
                                  widget.imageFile!,
                                  height: 220,
                                  width: double.infinity,
                                  fit: BoxFit.cover,
                                )
                              : Container(
                                  height: 220,
                                  color: Colors.grey[300],
                                  child: const Icon(Icons.image, size: 50),
                                ),
                        ),
                        Positioned(
                          top: 12,
                          right: 12,
                          child: GestureDetector(
                            onTap: widget.onCancel,
                            child: const CircleAvatar(
                              radius: 16,
                              backgroundColor: Color(0xffe91e63),
                              child: Icon(Icons.close, size: 18, color: Colors.white),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Image uploaded successfully',
                      style: TextStyle(color: Colors.grey, fontSize: 13),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            // --- การ์ดล่าง: แสดงสถานะการวิเคราะห์ด้วย AI ---
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(24.0),
              ),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 32.0, horizontal: 24.0),
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: const BoxDecoration(
                        color: Color(0xffe8f7f5),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.spa_outlined,
                        size: 36,
                        color: Color(0xff009688),
                      ),
                    ),
                    const SizedBox(height: 20),
                    const Text(
                      'Analyzing with AI...',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Color(0xff00796b),
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Please wait...',
                      style: TextStyle(fontSize: 13, color: Colors.grey),
                    ),
                    const SizedBox(height: 24),
                    
                    // แถบความคืบหน้า (ปรับให้โหลดเต็มสวย ๆ ระหว่างรอเด้งหน้า)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _buildProgressBarSegment(isActive: true),
                        const SizedBox(width: 6),
                        _buildProgressBarSegment(isActive: true),
                        const SizedBox(width: 6),
                        _buildProgressBarSegment(isActive: true),
                        const SizedBox(width: 6),
                        _buildProgressBarSegment(isActive: true),
                      ],
                    ),
                    const SizedBox(height: 24),

                    // รายการเช็กลิสต์สถานะ
                    Column(
                      children: [
                        _buildStatusLine('✓ Upload', isDone: true),
                        _buildStatusLine('✓ Process', isDone: true),
                        _buildStatusLine('✓ Analyze', isDone: true),
                        _buildStatusLine('Complete', isDone: true, isCurrent: true),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressBarSegment({required bool isActive}) {
    return Container(
      width: 45,
      height: 6,
      decoration: BoxDecoration(
        color: isActive ? const Color(0xff009688) : const Color(0xffe0e0e0),
        borderRadius: BorderRadius.circular(10),
      ),
    );
  }

  Widget _buildStatusLine(String text, {required bool isDone, bool isCurrent = false}) {
    Color textColor = Colors.grey;
    if (isDone || isCurrent) {
      textColor = const Color(0xff009688);
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 13,
          fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
          color: textColor,
        ),
      ),
    );
  }
}