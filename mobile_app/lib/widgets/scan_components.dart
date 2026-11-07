import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../theme/scan_design_tokens.dart';

class ScanHero extends StatelessWidget {
  const ScanHero({super.key, required this.onBack, required this.contextLabel});

  final VoidCallback onBack;
  final String contextLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [ScanColors.heroTop, ScanColors.heroBottom],
        ),
      ),
      child: Stack(
        children: [
          const Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(painter: _ScanBotanicalPainter()),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 8, 20, 52),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: ScanColors.white.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: BackButton(
                    key: const ValueKey('scan-back-button'),
                    onPressed: onBack,
                    color: ScanColors.white,
                    style: IconButton.styleFrom(
                      padding: EdgeInsets.zero,
                      iconSize: 21,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'ตรวจสุขภาพต้นไม้',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: ScanColors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'ถ่ายหรือเลือกรูปใบพืช เพื่อให้ PhytoScan วิเคราะห์',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: ScanColors.white.withValues(alpha: 0.76),
                  ),
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    const _HeroBadge(
                      icon: Icons.photo_library_outlined,
                      label: 'สูงสุด 3 ภาพ',
                      accent: true,
                    ),
                    _HeroBadge(
                      icon: Icons.auto_awesome_outlined,
                      label: contextLabel,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroBadge extends StatelessWidget {
  const _HeroBadge({
    required this.icon,
    required this.label,
    this.accent = false,
  });

  final IconData icon;
  final String label;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final foreground = accent ? ScanColors.primary : ScanColors.white;
    return ConstrainedBox(
      constraints: BoxConstraints(
        maxWidth: MediaQuery.sizeOf(context).width - 40,
      ),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
          color: accent
              ? ScanColors.accent
              : ScanColors.white.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(14),
          border: accent
              ? null
              : Border.all(color: ScanColors.white.withValues(alpha: 0.14)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 15, color: foreground),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: foreground,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ScanInstructionCard extends StatelessWidget {
  const ScanInstructionCard({super.key, this.plantName});

  final String? plantName;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ScanColors.instruction,
        borderRadius: BorderRadius.circular(ScanRadii.card),
        border: Border.all(color: ScanColors.track),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: ScanColors.white.withValues(alpha: 0.74),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: const Icon(
                  Icons.tips_and_updates_outlined,
                  color: ScanColors.primary,
                  size: 21,
                ),
              ),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ภาพที่เหมาะกับการวิเคราะห์',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: ScanColors.text,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (plantName != null)
                      Text(
                        'กำลังตรวจ: $plantName',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: ScanColors.textSecondary,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 13),
          const _InstructionBullet(text: 'ใช้พื้นหลังเรียบและแสงสม่ำเสมอ'),
          const _InstructionBullet(text: 'ให้ใบไม้ชัดและอยู่กลางภาพ'),
          const _InstructionBullet(text: 'ใช้พืชชนิดเดียวกันในชุดภาพ'),
        ],
      ),
    );
  }
}

class _InstructionBullet extends StatelessWidget {
  const _InstructionBullet({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Row(
        children: [
          const Icon(
            Icons.check_circle_rounded,
            size: 17,
            color: ScanColors.primary,
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              text,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: ScanColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }
}

class ScanUploadFrame extends StatelessWidget {
  const ScanUploadFrame({super.key, required this.image});

  final XFile? image;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1.26,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(ScanRadii.card),
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (image == null)
              ColoredBox(
                key: const ValueKey('scan-empty-upload'),
                color: ScanColors.uploadSurface,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 62,
                      height: 62,
                      decoration: const BoxDecoration(
                        color: ScanColors.white,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.document_scanner_outlined,
                        size: 31,
                        color: ScanColors.primary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'เพิ่มภาพใบไม้เพื่อเริ่มตรวจ',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: ScanColors.text,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'ถ่ายภาพใหม่หรือเลือกจากคลังรูป',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: ScanColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              )
            else
              FutureBuilder<Uint8List>(
                future: image!.readAsBytes(),
                builder: (context, snapshot) {
                  if (!snapshot.hasData) {
                    return const ColoredBox(
                      color: ScanColors.uploadSurface,
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  return Image.memory(
                    snapshot.data!,
                    key: const ValueKey('scan-main-preview'),
                    fit: BoxFit.cover,
                  );
                },
              ),
            const Positioned.fill(
              child: IgnorePointer(
                child: CustomPaint(painter: _ScanCornerPainter()),
              ),
            ),
            if (image != null)
              Positioned(
                left: 14,
                bottom: 14,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: ScanColors.primary.withValues(alpha: 0.86),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text(
                    'ภาพหลัก',
                    style: TextStyle(
                      color: ScanColors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
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

class ScanActionButtons extends StatelessWidget {
  const ScanActionButtons({
    super.key,
    required this.onCamera,
    required this.onGallery,
    required this.enabled,
  });

  final VoidCallback onCamera;
  final VoidCallback onGallery;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: FilledButton.icon(
            key: const ValueKey('scan-camera-button'),
            onPressed: enabled ? onCamera : null,
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(50),
              backgroundColor: ScanColors.primary,
              foregroundColor: ScanColors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(ScanRadii.control),
              ),
            ),
            icon: const Icon(Icons.photo_camera_outlined, size: 20),
            label: const Text('กล้อง'),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: OutlinedButton.icon(
            key: const ValueKey('scan-gallery-button'),
            onPressed: enabled ? onGallery : null,
            style: OutlinedButton.styleFrom(
              minimumSize: const Size.fromHeight(50),
              backgroundColor: ScanColors.white,
              foregroundColor: ScanColors.primary,
              side: const BorderSide(color: ScanColors.border),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(ScanRadii.control),
              ),
            ),
            icon: const Icon(Icons.photo_library_outlined, size: 20),
            label: const Text('คลังรูป'),
          ),
        ),
      ],
    );
  }
}

class ScanSelectedImages extends StatelessWidget {
  const ScanSelectedImages({
    super.key,
    required this.images,
    required this.onRemove,
    required this.enabled,
  });

  final List<XFile> images;
  final ValueChanged<int> onRemove;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'ภาพที่เลือก',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: ScanColors.text,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Container(
              key: const ValueKey('selected-image-count'),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: ScanColors.track,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${images.length}/3 ภาพ',
                style: const TextStyle(
                  color: ScanColors.primary,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (images.isEmpty)
          Container(
            key: const ValueKey('scan-empty-selected-images'),
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
            decoration: BoxDecoration(
              color: ScanColors.uploadSurface,
              borderRadius: BorderRadius.circular(ScanRadii.control),
              border: Border.all(color: ScanColors.track),
            ),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.photo_outlined,
                  size: 20,
                  color: ScanColors.textSecondary,
                ),
                SizedBox(width: 9),
                Flexible(
                  child: Text(
                    'ยังไม่มีภาพที่เลือก',
                    style: TextStyle(color: ScanColors.textSecondary),
                  ),
                ),
              ],
            ),
          )
        else
          SizedBox(
            height: 92,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: images.length,
              separatorBuilder: (_, _) => const SizedBox(width: 10),
              itemBuilder: (context, index) => _SelectedThumbnail(
                image: images[index],
                index: index,
                enabled: enabled,
                onRemove: () => onRemove(index),
              ),
            ),
          ),
      ],
    );
  }
}

class _SelectedThumbnail extends StatelessWidget {
  const _SelectedThumbnail({
    required this.image,
    required this.index,
    required this.enabled,
    required this.onRemove,
  });

  final XFile image;
  final int index;
  final bool enabled;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 92,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(17),
        child: Stack(
          fit: StackFit.expand,
          children: [
            FutureBuilder<Uint8List>(
              future: image.readAsBytes(),
              builder: (context, snapshot) {
                if (!snapshot.hasData) {
                  return const ColoredBox(color: ScanColors.uploadSurface);
                }
                return Image.memory(
                  snapshot.data!,
                  key: ValueKey('scan-thumbnail-$index'),
                  fit: BoxFit.cover,
                );
              },
            ),
            Positioned(
              top: 5,
              right: 5,
              child: IconButton(
                key: ValueKey('remove-image-$index'),
                tooltip: 'ลบรูป',
                onPressed: enabled ? onRemove : null,
                style: IconButton.styleFrom(
                  minimumSize: const Size(30, 30),
                  maximumSize: const Size(30, 30),
                  padding: EdgeInsets.zero,
                  backgroundColor: ScanColors.primary.withValues(alpha: 0.82),
                  foregroundColor: ScanColors.white,
                ),
                icon: const Icon(Icons.close_rounded, size: 17),
              ),
            ),
            Positioned(
              left: 6,
              bottom: 6,
              child: Container(
                width: 24,
                height: 24,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: ScanColors.primary.withValues(alpha: 0.84),
                  shape: BoxShape.circle,
                ),
                child: Text(
                  '${index + 1}',
                  style: const TextStyle(
                    color: ScanColors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
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

class ScanBottomCta extends StatelessWidget {
  const ScanBottomCta({
    super.key,
    required this.hasImages,
    required this.busy,
    required this.onPressed,
    this.errorMessage,
  });

  final bool hasImages;
  final bool busy;
  final VoidCallback onPressed;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 14),
      decoration: BoxDecoration(
        color: ScanColors.surface,
        border: const Border(top: BorderSide(color: ScanColors.track)),
        boxShadow: [
          BoxShadow(
            color: ScanColors.primary.withValues(alpha: 0.08),
            blurRadius: 18,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (errorMessage != null) ...[
              Container(
                key: const ValueKey('analyze-error'),
                width: double.infinity,
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(
                  color: ScanColors.error.withValues(alpha: 0.09),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.error_outline_rounded,
                      color: ScanColors.error,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        errorMessage!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: ScanColors.error,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 9),
            ],
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                key: const ValueKey('analyze-submit'),
                onPressed: hasImages && !busy ? onPressed : null,
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(54),
                  backgroundColor: ScanColors.primary,
                  foregroundColor: ScanColors.white,
                  disabledBackgroundColor: ScanColors.track,
                  disabledForegroundColor: ScanColors.textSecondary,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                  ),
                ),
                icon: Icon(
                  hasImages
                      ? Icons.auto_awesome_outlined
                      : Icons.add_photo_alternate_outlined,
                  size: 20,
                ),
                label: Text(
                  hasImages
                      ? 'วิเคราะห์ด้วย PhytoScan'
                      : 'เลือกภาพก่อนเริ่มวิเคราะห์',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ScanCornerPainter extends CustomPainter {
  const _ScanCornerPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = ScanColors.accent
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    const inset = 18.0;
    const length = 30.0;
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

class _ScanBotanicalPainter extends CustomPainter {
  const _ScanBotanicalPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = ScanColors.white.withValues(alpha: 0.035);
    canvas.save();
    canvas.translate(size.width * 0.77, -8);
    canvas.rotate(-0.26);
    for (var index = 0; index < 5; index++) {
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(index * 15, index * 43),
          width: 82,
          height: 34,
        ),
        paint,
      );
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
