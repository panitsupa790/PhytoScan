import 'dart:async';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/plant.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/image_picker_card.dart';
import '../widgets/primary_button.dart';
import 'result_screen.dart';

class AnalyzeScreen extends StatefulWidget {
  const AnalyzeScreen({super.key, required this.plant, required this.api});

  final Plant plant;
  final PhytoScanApi api;

  @override
  State<AnalyzeScreen> createState() => _AnalyzeScreenState();
}

class _AnalyzeScreenState extends State<AnalyzeScreen> {
  static const _loadingMessages = [
    'กำลังเตรียมภาพ',
    'กำลังวิเคราะห์ลักษณะ',
    'กำลังสรุปผล',
  ];

  final ImagePicker _picker = ImagePicker();
  final List<XFile> _images = [];
  Timer? _loadingTimer;
  bool _loading = false;
  int _loadingStep = 0;
  String? _error;

  Future<void> _pickFromGallery() async {
    final remaining = 3 - _images.length;
    if (remaining == 0) return;
    try {
      final picked = await _picker.pickMultiImage(imageQuality: 92);
      if (!mounted || picked.isEmpty) return;
      setState(() {
        _images.addAll(picked.take(remaining));
        _error = null;
      });
      if (picked.length > remaining) _showLimitMessage();
    } catch (_) {
      _setPickerError('ไม่สามารถเปิดคลังรูปภาพได้');
    }
  }

  Future<void> _takePhoto() async {
    if (_images.length >= 3) {
      _showLimitMessage();
      return;
    }
    try {
      final image = await _picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 92,
      );
      if (!mounted || image == null) return;
      setState(() {
        _images.add(image);
        _error = null;
      });
    } catch (_) {
      _setPickerError('ไม่สามารถเปิดกล้องได้ กรุณาตรวจสอบสิทธิ์การใช้งาน');
    }
  }

  void _setPickerError(String message) {
    if (mounted) setState(() => _error = message);
  }

  void _showLimitMessage() {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('เพิ่มได้สูงสุด 3 ภาพ')));
  }

  void _startLoading() {
    setState(() {
      _loading = true;
      _loadingStep = 0;
      _error = null;
    });
    _loadingTimer?.cancel();
    _loadingTimer = Timer.periodic(const Duration(milliseconds: 900), (_) {
      if (!mounted || !_loading) return;
      setState(() {
        if (_loadingStep < _loadingMessages.length - 1) {
          _loadingStep += 1;
        }
      });
    });
  }

  void _stopLoading({String? error}) {
    _loadingTimer?.cancel();
    if (!mounted) return;
    setState(() {
      _loading = false;
      _error = error;
    });
  }

  Future<void> _analyze() async {
    if (_images.isEmpty || _loading) return;
    _startLoading();
    try {
      final result = await widget.api.analyze(
        plantCode: widget.plant.code,
        images: List.unmodifiable(_images),
      );
      if (!mounted) return;
      _stopLoading();
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) =>
              ResultScreen(result: result, images: List.unmodifiable(_images)),
        ),
      );
    } on ApiException catch (error) {
      _stopLoading(error: error.message);
    } catch (_) {
      _stopLoading(error: 'เกิดข้อผิดพลาด กรุณาลองอีกครั้ง');
    }
  }

  @override
  void dispose() {
    _loadingTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ตรวจสุขภาพต้นไม้')),
      body: Stack(
        children: [
          SafeArea(
            top: false,
            child: Column(
              children: [
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(22, 10, 22, 26),
                    children: [
                      _PlantPill(plant: widget.plant),
                      const SizedBox(height: 20),
                      Text(
                        'จัดใบไม้ให้อยู่ในกรอบ',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'เห็นใบชัด แสงเพียงพอ ไม่เบลอ และไม่ใกล้หรือไกลเกินไป',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      _CaptureFrame(
                        image: _images.isEmpty ? null : _images.first,
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _loading ? null : _takePhoto,
                              icon: const Icon(Icons.photo_camera_outlined),
                              label: const Text('กล้อง'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _loading ? null : _pickFromGallery,
                              icon: const Icon(Icons.photo_library_outlined),
                              label: const Text('คลังรูป'),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 26),
                      Row(
                        children: [
                          Text(
                            'ภาพที่เลือก',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const Spacer(),
                          Text(
                            '${_images.length}/3 ภาพ',
                            style: Theme.of(context).textTheme.labelMedium
                                ?.copyWith(color: AppColors.primary),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'แต่ละภาพอาจให้ผลต่างกัน และจะแสดงผลแยกทีละภาพ',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 13),
                      SizedBox(
                        height: 96,
                        child: ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemCount:
                              _images.length + (_images.length < 3 ? 1 : 0),
                          separatorBuilder: (_, _) => const SizedBox(width: 10),
                          itemBuilder: (context, index) {
                            if (index == _images.length) {
                              return SizedBox(
                                width: 96,
                                child: ImagePickerCard.add(
                                  onTap: _pickFromGallery,
                                ),
                              );
                            }
                            return SizedBox(
                              width: 96,
                              child: ImagePickerCard.preview(
                                image: _images[index],
                                order: index + 1,
                                onRemove: () => setState(() {
                                  _images.removeAt(index);
                                  _error = null;
                                }),
                              ),
                            );
                          },
                        ),
                      ),
                      if (_images.isNotEmpty) ...[
                        const SizedBox(height: 24),
                        _ReviewSection(
                          plant: widget.plant,
                          imageCount: _images.length,
                        ),
                      ],
                      if (_error != null) ...[
                        const SizedBox(height: 16),
                        _ErrorMessage(message: _error!),
                      ],
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.fromLTRB(22, 12, 22, 18),
                  decoration: const BoxDecoration(
                    color: AppColors.background,
                    border: Border(
                      top: BorderSide(color: AppColors.divider, width: 0.6),
                    ),
                  ),
                  child: PrimaryButton(
                    label: 'วิเคราะห์ด้วย PhytoScan',
                    icon: Icons.auto_awesome_outlined,
                    onPressed: _images.isEmpty ? null : _analyze,
                  ),
                ),
              ],
            ),
          ),
          if (_loading)
            Positioned.fill(
              child: ColoredBox(
                color: Colors.white.withValues(alpha: 0.90),
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.all(34),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 70,
                          height: 70,
                          decoration: const BoxDecoration(
                            color: AppColors.paleGreen,
                            shape: BoxShape.circle,
                          ),
                          child: const Padding(
                            padding: EdgeInsets.all(21),
                            child: CircularProgressIndicator(strokeWidth: 2.5),
                          ),
                        ),
                        const SizedBox(height: 22),
                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 220),
                          child: Text(
                            _loadingMessages[_loadingStep],
                            key: ValueKey(_loadingStep),
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                        const SizedBox(height: 7),
                        Text(
                          'PhytoScan กำลังตรวจภาพของคุณ',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _PlantPill extends StatelessWidget {
  const _PlantPill({required this.plant});

  final Plant plant;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: const BoxDecoration(
            color: AppColors.paleGreen,
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.eco_outlined, color: AppColors.primary),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(plant.nameTh, style: Theme.of(context).textTheme.titleMedium),
            Text(plant.nameEn, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ],
    );
  }
}

class _CaptureFrame extends StatelessWidget {
  const _CaptureFrame({required this.image});

  final XFile? image;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1.08,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(26),
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (image == null)
              const ColoredBox(
                color: AppColors.paleGreen,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.eco_outlined,
                      size: 72,
                      color: AppColors.primary,
                    ),
                    SizedBox(height: 12),
                    Text(
                      'เพิ่มภาพใบไม้เพื่อเริ่มตรวจ',
                      style: TextStyle(
                        color: AppColors.darkGreen,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              )
            else
              FutureBuilder(
                future: image!.readAsBytes(),
                builder: (context, snapshot) {
                  if (!snapshot.hasData) {
                    return const ColoredBox(
                      color: AppColors.paleGreen,
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  return Image.memory(snapshot.data!, fit: BoxFit.cover);
                },
              ),
            const CustomPaint(painter: _ScanFramePainter()),
          ],
        ),
      ),
    );
  }
}

class _ScanFramePainter extends CustomPainter {
  const _ScanFramePainter();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.92)
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    const inset = 24.0;
    const length = 34.0;
    final paths = [
      Path()
        ..moveTo(inset, inset + length)
        ..lineTo(inset, inset)
        ..lineTo(inset + length, inset),
      Path()
        ..moveTo(size.width - inset - length, inset)
        ..lineTo(size.width - inset, inset)
        ..lineTo(size.width - inset, inset + length),
      Path()
        ..moveTo(inset, size.height - inset - length)
        ..lineTo(inset, size.height - inset)
        ..lineTo(inset + length, size.height - inset),
      Path()
        ..moveTo(size.width - inset - length, size.height - inset)
        ..lineTo(size.width - inset, size.height - inset)
        ..lineTo(size.width - inset, size.height - inset - length),
    ];
    for (final path in paths) {
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _ReviewSection extends StatelessWidget {
  const _ReviewSection({required this.plant, required this.imageCount});

  final Plant plant;
  final int imageCount;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.divider, width: 0.6),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Text(
                'ตรวจสอบก่อนวิเคราะห์',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const Spacer(),
              Text(
                '$imageCount ภาพ',
                style: Theme.of(context).textTheme.labelMedium,
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.info_outline_rounded,
                size: 20,
                color: AppColors.warning,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'โปรดตรวจสอบว่าภาพทั้งหมดเป็น${plant.nameTh}ชนิดเดียวกัน',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ErrorMessage extends StatelessWidget {
  const _ErrorMessage({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline_rounded, color: AppColors.error),
          const SizedBox(width: 10),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }
}
