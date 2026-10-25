import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class ImagePickerCard extends StatelessWidget {
  const ImagePickerCard.add({super.key, required this.onTap})
    : image = null,
      onRemove = null,
      order = null;

  const ImagePickerCard.preview({
    super.key,
    required this.image,
    required this.onRemove,
    this.order,
  }) : onTap = null;

  final XFile? image;
  final VoidCallback? onTap;
  final VoidCallback? onRemove;
  final int? order;

  @override
  Widget build(BuildContext context) {
    final selected = image;
    if (selected == null) {
      return Material(
        color: Theme.of(
          context,
        ).colorScheme.primaryContainer.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(20),
          child: const AspectRatio(
            aspectRatio: 1,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.add_photo_alternate_outlined, size: 34),
                SizedBox(height: 8),
                Text('เพิ่มรูป'),
              ],
            ),
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: AspectRatio(
        aspectRatio: 1,
        child: Stack(
          fit: StackFit.expand,
          children: [
            FutureBuilder(
              future: selected.readAsBytes(),
              builder: (context, snapshot) {
                if (!snapshot.hasData) {
                  return const ColoredBox(
                    color: Color(0xFFE6EFE8),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return Image.memory(snapshot.data!, fit: BoxFit.cover);
              },
            ),
            if (onRemove != null)
              Positioned(
                top: 6,
                right: 6,
                child: IconButton.filledTonal(
                  onPressed: onRemove,
                  icon: const Icon(Icons.close_rounded),
                  tooltip: 'ลบรูป',
                ),
              ),
            if (order != null)
              Positioned(
                left: 7,
                bottom: 7,
                child: Container(
                  width: 27,
                  height: 27,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.66),
                    shape: BoxShape.circle,
                  ),
                  child: Text(
                    '$order',
                    style: const TextStyle(
                      color: Colors.white,
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
