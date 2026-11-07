import 'package:flutter/material.dart';

import '../models/scan_history_entry.dart';
import '../services/scan_history_store.dart';
import '../theme/login_design_tokens.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, required this.store});

  final ScanHistoryRepository store;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late Future<List<ScanHistoryEntry>> _entries;

  @override
  void initState() {
    super.initState();
    _entries = widget.store.load();
  }

  Future<void> _reload() async {
    final future = widget.store.load();
    setState(() => _entries = future);
    await future;
  }

  Future<void> _delete(String id) async {
    await widget.store.delete(id);
    if (mounted) await _reload();
  }

  Future<void> _clear() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('ล้างประวัติทั้งหมด?'),
        content: const Text(
          'รายการผลสแกนที่บันทึกไว้ในเครื่องจะถูกลบและไม่สามารถกู้คืนได้',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('ยกเลิก'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('ล้างประวัติ'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await widget.store.clear();
    if (mounted) await _reload();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ScanHistoryEntry>>(
      future: _entries,
      builder: (context, snapshot) {
        final entries = snapshot.data ?? const <ScanHistoryEntry>[];
        return ColoredBox(
          color: LoginColors.sheetSurface,
          child: RefreshIndicator(
            onRefresh: _reload,
            color: LoginColors.primaryGreen,
            child: ListView(
              key: const ValueKey('scan-history-list'),
              physics: const AlwaysScrollableScrollPhysics(),
              padding: EdgeInsets.zero,
              children: [
                _HistoryHero(
                  count: entries.length,
                  canClear: entries.isNotEmpty,
                  onClear: _clear,
                ),
                Transform.translate(
                  offset: const Offset(0, -30),
                  child: Container(
                    constraints: BoxConstraints(
                      minHeight: MediaQuery.sizeOf(context).height * 0.58,
                    ),
                    padding: const EdgeInsets.fromLTRB(20, 24, 20, 10),
                    decoration: const BoxDecoration(
                      color: LoginColors.sheetSurface,
                      borderRadius: BorderRadius.vertical(
                        top: Radius.circular(32),
                      ),
                    ),
                    child: _HistoryContent(
                      state: snapshot.connectionState,
                      error: snapshot.error,
                      entries: entries,
                      onRetry: _reload,
                      onDelete: _delete,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _HistoryHero extends StatelessWidget {
  const _HistoryHero({
    required this.count,
    required this.canClear,
    required this.onClear,
  });

  final int count;
  final bool canClear;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 210,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [LoginColors.heroTop, LoginColors.heroBottom],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -30,
            top: -18,
            child: Icon(
              Icons.history_rounded,
              size: 190,
              color: LoginColors.white.withValues(alpha: 0.06),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 26, 18, 46),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.auto_awesome_rounded,
                      color: LoginColors.accentGreen,
                      size: 18,
                    ),
                    const SizedBox(width: 7),
                    const Expanded(
                      child: Text(
                        'ประวัติการตรวจของอุปกรณ์นี้',
                        style: TextStyle(
                          color: LoginColors.accentGreen,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (canClear)
                      IconButton(
                        tooltip: 'ล้างประวัติทั้งหมด',
                        onPressed: onClear,
                        style: IconButton.styleFrom(
                          foregroundColor: LoginColors.white,
                          backgroundColor: LoginColors.white.withValues(
                            alpha: 0.12,
                          ),
                        ),
                        icon: const Icon(Icons.delete_sweep_outlined, size: 21),
                      ),
                  ],
                ),
                const Spacer(),
                const Text(
                  'ประวัติการสแกน',
                  style: TextStyle(
                    color: LoginColors.white,
                    fontSize: 29,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  count == 0
                      ? 'ผลวิเคราะห์ครั้งใหม่จะแสดงที่นี่'
                      : 'บันทึกผลวิเคราะห์แล้ว $count รายการ',
                  style: TextStyle(
                    color: LoginColors.white.withValues(alpha: 0.74),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryContent extends StatelessWidget {
  const _HistoryContent({
    required this.state,
    required this.error,
    required this.entries,
    required this.onRetry,
    required this.onDelete,
  });

  final ConnectionState state;
  final Object? error;
  final List<ScanHistoryEntry> entries;
  final Future<void> Function() onRetry;
  final ValueChanged<String> onDelete;

  @override
  Widget build(BuildContext context) {
    if (state == ConnectionState.waiting && entries.isEmpty) {
      return const Padding(
        padding: EdgeInsets.only(top: 80),
        child: Center(
          child: CircularProgressIndicator(color: LoginColors.primaryGreen),
        ),
      );
    }
    if (error != null) {
      return _HistoryMessage(
        icon: Icons.error_outline_rounded,
        title: 'เปิดประวัติไม่สำเร็จ',
        message: 'กรุณาลองโหลดข้อมูลอีกครั้ง',
        action: TextButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh_rounded),
          label: const Text('ลองอีกครั้ง'),
        ),
      );
    }
    if (entries.isEmpty) {
      return const _HistoryMessage(
        icon: Icons.document_scanner_outlined,
        title: 'ยังไม่มีประวัติการสแกน',
        message: 'เมื่อวิเคราะห์ภาพสำเร็จ ระบบจะบันทึกผลสรุปไว้ในหน้านี้',
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                'ผลสแกนล่าสุด',
                style: TextStyle(
                  color: LoginColors.primaryText,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Text(
              '${entries.length} รายการ',
              style: const TextStyle(
                color: LoginColors.secondaryText,
                fontSize: 12,
              ),
            ),
          ],
        ),
        const SizedBox(height: 13),
        for (var index = 0; index < entries.length; index++) ...[
          _HistoryCard(
            entry: entries[index],
            onDelete: () => onDelete(entries[index].id),
          ),
          if (index < entries.length - 1) const SizedBox(height: 11),
        ],
        const SizedBox(height: 12),
        const _LocalStorageNote(),
      ],
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.entry, required this.onDelete});

  final ScanHistoryEntry entry;
  final VoidCallback onDelete;

  bool get _isHealthy {
    final value = '${entry.diseaseCode} ${entry.diseaseName}'.toLowerCase();
    return value.contains('healthy') || value.contains('สุขภาพดี');
  }

  @override
  Widget build(BuildContext context) {
    final differentResults = entry.diseaseNames.length > 1;
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: LoginColors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: LoginColors.fieldBorder),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0D17321E),
            blurRadius: 16,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: _isHealthy
                      ? const Color(0xFFEAF2E6)
                      : const Color(0xFFFFEEE4),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(
                  _isHealthy
                      ? Icons.eco_outlined
                      : Icons.health_and_safety_outlined,
                  color: _isHealthy
                      ? LoginColors.primaryGreen
                      : LoginColors.orangeHighlight,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.plantName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: LoginColors.primaryText,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      differentResults
                          ? 'ผลแต่ละภาพแตกต่างกัน ${entry.diseaseNames.length} รายการ'
                          : entry.diseaseName,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: LoginColors.secondaryText,
                        fontSize: 13,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                tooltip: 'ลบรายการนี้',
                onPressed: onDelete,
                visualDensity: VisualDensity.compact,
                icon: const Icon(
                  Icons.close_rounded,
                  color: LoginColors.secondaryText,
                  size: 19,
                ),
              ),
            ],
          ),
          const SizedBox(height: 13),
          Wrap(
            spacing: 7,
            runSpacing: 7,
            children: [
              _HistoryChip(
                icon: Icons.schedule_rounded,
                label: _thaiDateTime(entry.analyzedAt),
              ),
              _HistoryChip(
                icon: Icons.photo_library_outlined,
                label: '${entry.imageCount} ภาพ',
              ),
              _HistoryChip(
                icon: entry.manuallyConfirmed
                    ? Icons.person_outline_rounded
                    : Icons.auto_awesome_outlined,
                label: entry.manuallyConfirmed
                    ? 'ผู้ใช้ยืนยันชนิดพืช'
                    : 'ระบบระบุชนิดพืช',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HistoryChip extends StatelessWidget {
  const _HistoryChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: LoginColors.sheetSurface,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: LoginColors.fieldBorder),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: LoginColors.primaryGreen),
          const SizedBox(width: 5),
          Text(
            label,
            style: const TextStyle(
              color: LoginColors.secondaryText,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryMessage extends StatelessWidget {
  const _HistoryMessage({
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 64, 20, 24),
      child: Column(
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: const BoxDecoration(
              color: LoginColors.segmentTrack,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: LoginColors.primaryGreen, size: 32),
          ),
          const SizedBox(height: 18),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: LoginColors.primaryText,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: LoginColors.secondaryText,
              fontSize: 13,
              height: 1.45,
            ),
          ),
          if (action != null) ...[const SizedBox(height: 12), action!],
        ],
      ),
    );
  }
}

class _LocalStorageNote extends StatelessWidget {
  const _LocalStorageNote();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 6, vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.lock_outline_rounded,
            color: LoginColors.secondaryText,
            size: 15,
          ),
          SizedBox(width: 7),
          Expanded(
            child: Text(
              'ซิงก์เฉพาะข้อมูลสรุปผลและไม่จัดเก็บไฟล์ภาพต้นฉบับในฐานข้อมูล',
              style: TextStyle(
                color: LoginColors.secondaryText,
                fontSize: 11,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

String _thaiDateTime(DateTime value) {
  const months = [
    'ม.ค.',
    'ก.พ.',
    'มี.ค.',
    'เม.ย.',
    'พ.ค.',
    'มิ.ย.',
    'ก.ค.',
    'ส.ค.',
    'ก.ย.',
    'ต.ค.',
    'พ.ย.',
    'ธ.ค.',
  ];
  final local = value.toLocal();
  final minute = local.minute.toString().padLeft(2, '0');
  return '${local.day} ${months[local.month - 1]} ${local.year + 543} · ${local.hour}:$minute น.';
}
