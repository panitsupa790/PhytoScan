import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../models/analyze_outcome.dart';
import '../models/analyze_result.dart';
import '../models/plant.dart';
import '../models/scan_history_entry.dart';
import '../services/api_service.dart';
import '../services/scan_history_store.dart';
import '../theme/app_theme.dart';
import '../theme/scan_design_tokens.dart';
import '../widgets/scan_components.dart';
import 'manual_plant_confirmation_screen.dart';
import 'result_screen.dart';

class AnalyzeScreen extends StatefulWidget {
  const AnalyzeScreen({
    super.key,
    required this.api,
    this.plant,
    this.initialImages = const [],
    this.historyStore = const ScanHistoryStore(),
  });

  final Plant? plant;
  final PhytoScanApi api;
  final List<XFile> initialImages;
  final ScanHistoryRepository historyStore;

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

  @override
  void initState() {
    super.initState();
    _images.addAll(widget.initialImages.take(3));
  }

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

  Future<void> _analyze({String? confirmedPlantCode}) async {
    if (_images.isEmpty || _loading) return;
    final plantCode = confirmedPlantCode ?? widget.plant?.code;
    final submittedImages = List<XFile>.unmodifiable(_images);
    _startLoading();
    try {
      final outcome = await widget.api.analyze(
        plantCode: plantCode,
        images: submittedImages,
      );
      if (!mounted) return;
      _stopLoading();
      switch (outcome) {
        case CompletedAnalyzeOutcome(:final result, :final scanId):
          await _saveHistory(
            result,
            manuallyConfirmed: plantCode != null,
            scanId: scanId,
          );
          if (!mounted) return;
          await Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => ResultScreen(
                result: result,
                images: submittedImages,
                identificationSource: plantCode == null
                    ? PlantIdentificationSource.automatic
                    : PlantIdentificationSource.manuallyConfirmed,
              ),
            ),
          );
        case ManualConfirmationOutcome():
          final selectedPlantCode = await Navigator.of(context).push<String>(
            MaterialPageRoute(
              builder: (_) => ManualPlantConfirmationScreen(
                outcome: outcome,
                api: widget.api,
              ),
            ),
          );
          if (selectedPlantCode != null && mounted) {
            await _analyze(confirmedPlantCode: selectedPlantCode);
          }
      }
    } on ApiException catch (error) {
      _stopLoading(error: _errorMessage(error));
    } catch (_) {
      _stopLoading(error: 'เกิดข้อผิดพลาด กรุณาลองอีกครั้ง');
    }
  }

  Future<void> _saveHistory(
    AnalyzeResult result, {
    required bool manuallyConfirmed,
    String? scanId,
  }) async {
    try {
      await widget.historyStore.add(
        ScanHistoryEntry.fromResult(
          result: result,
          manuallyConfirmed: manuallyConfirmed,
          id: scanId,
        ),
      );
    } catch (_) {
      // A local storage failure must not block the completed analysis result.
    }
  }

  String _errorMessage(ApiException error) => switch (error.errorCode) {
    'MODEL_UNAVAILABLE' =>
      'ระบบวิเคราะห์ยังไม่พร้อมใช้งาน กรุณาลองอีกครั้งภายหลัง',
    'INFERENCE_FAILED' =>
      'วิเคราะห์ภาพไม่สำเร็จ กรุณาลองใช้ภาพอื่นหรือลองอีกครั้ง',
    'NETWORK_TIMEOUT' => 'การเชื่อมต่อใช้เวลานานเกินไป กรุณาลองอีกครั้ง',
    'NETWORK_ERROR' => 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ต',
    _ => error.message,
  };

  @override
  void dispose() {
    _loadingTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hasImages = _images.isNotEmpty;
    final canAddImages = !_loading && _images.length < 3;
    final contextLabel = widget.plant?.nameTh ?? 'จำแนกชนิดพืชอัตโนมัติ';

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        key: const ValueKey('analyze-screen'),
        backgroundColor: ScanColors.heroTop,
        body: Stack(
          children: [
            SafeArea(
              bottom: false,
              child: CustomScrollView(
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                slivers: [
                  SliverToBoxAdapter(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        ScanHero(
                          onBack: () => Navigator.of(context).maybePop(),
                          contextLabel: contextLabel,
                        ),
                        Transform.translate(
                          offset: const Offset(0, -26),
                          child: Container(
                            clipBehavior: Clip.antiAlias,
                            decoration: const BoxDecoration(
                              color: ScanColors.surface,
                              borderRadius: BorderRadius.vertical(
                                top: Radius.circular(ScanRadii.sheet),
                              ),
                            ),
                            padding: EdgeInsets.fromLTRB(
                              20,
                              30,
                              20,
                              _error == null ? 150 : 220,
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                ScanInstructionCard(
                                  plantName: widget.plant?.nameTh,
                                ),
                                const SizedBox(height: 24),
                                Text(
                                  'เพิ่มรูปภาพ',
                                  style: Theme.of(context).textTheme.titleLarge
                                      ?.copyWith(
                                        color: ScanColors.text,
                                        fontWeight: FontWeight.w700,
                                      ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'ภาพแรกจะใช้เป็นภาพหลักในการแสดงตัวอย่าง',
                                  style: Theme.of(context).textTheme.bodyMedium
                                      ?.copyWith(
                                        color: ScanColors.textSecondary,
                                      ),
                                ),
                                const SizedBox(height: 13),
                                ScanUploadFrame(
                                  image: hasImages ? _images.first : null,
                                ),
                                const SizedBox(height: 14),
                                ScanActionButtons(
                                  onCamera: _takePhoto,
                                  onGallery: _pickFromGallery,
                                  enabled: canAddImages,
                                ),
                                const SizedBox(height: 26),
                                ScanSelectedImages(
                                  images: List<XFile>.unmodifiable(_images),
                                  enabled: !_loading,
                                  onRemove: (index) => setState(() {
                                    _images.removeAt(index);
                                    _error = null;
                                  }),
                                ),
                                if (hasImages) ...[
                                  const SizedBox(height: 22),
                                  _ReviewSection(
                                    plant: widget.plant,
                                    imageCount: _images.length,
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Align(
              alignment: Alignment.bottomCenter,
              child: ScanBottomCta(
                hasImages: hasImages,
                busy: _loading,
                errorMessage: _error,
                onPressed: _analyze,
              ),
            ),
            if (_loading)
              Positioned.fill(
                child: ColoredBox(
                  color: ScanColors.primary.withValues(alpha: 0.94),
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(34),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 72,
                            height: 72,
                            decoration: BoxDecoration(
                              color: ScanColors.white.withValues(alpha: 0.12),
                              shape: BoxShape.circle,
                            ),
                            child: const Padding(
                              padding: EdgeInsets.all(22),
                              child: CircularProgressIndicator(
                                strokeWidth: 2.5,
                                color: ScanColors.accent,
                              ),
                            ),
                          ),
                          const SizedBox(height: 22),
                          AnimatedSwitcher(
                            duration: const Duration(milliseconds: 220),
                            child: Text(
                              _loadingMessages[_loadingStep],
                              key: ValueKey(_loadingStep),
                              style: Theme.of(context).textTheme.titleLarge
                                  ?.copyWith(color: ScanColors.white),
                            ),
                          ),
                          const SizedBox(height: 7),
                          Text(
                            'PhytoScan กำลังตรวจภาพของคุณ',
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(
                                  color: ScanColors.white.withValues(
                                    alpha: 0.72,
                                  ),
                                ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ReviewSection extends StatelessWidget {
  const _ReviewSection({required this.plant, required this.imageCount});

  final Plant? plant;
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
                  plant == null
                      ? 'โปรดใช้ภาพของพืชชนิดเดียวกัน ระบบจะจำแนกชนิดพืชก่อนวิเคราะห์โรค'
                      : 'โปรดตรวจสอบว่าภาพทั้งหมดเป็น${plant!.nameTh}ชนิดเดียวกัน',
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
