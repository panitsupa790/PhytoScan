import 'package:flutter/material.dart';

import '../theme/login_design_tokens.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const rows = [
      _ProfileItem(Icons.history_rounded, 'ประวัติการตรวจ', 'กำลังพัฒนา'),
      _ProfileItem(
        Icons.notifications_none_rounded,
        'การแจ้งเตือน',
        'กำลังพัฒนา',
      ),
      _ProfileItem(Icons.memory_outlined, 'โมเดลที่รองรับ', 'รองรับพืช 6 ชนิด'),
      _ProfileItem(
        Icons.info_outline_rounded,
        'เกี่ยวกับ PhytoScan',
        'เวอร์ชัน 1.0.0',
      ),
    ];

    return ColoredBox(
      color: LoginColors.sheetSurface,
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          const _ProfileHero(),
          Transform.translate(
            offset: const Offset(0, -30),
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 6),
              decoration: const BoxDecoration(
                color: LoginColors.sheetSurface,
                borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _GuestCard(),
                  const SizedBox(height: 24),
                  const _SectionLabel(
                    title: 'บัญชีและแอปพลิเคชัน',
                    caption: 'การตั้งค่า',
                  ),
                  const SizedBox(height: 12),
                  Container(
                    decoration: BoxDecoration(
                      color: LoginColors.white,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: LoginColors.fieldBorder),
                    ),
                    child: Column(
                      children: [
                        for (var index = 0; index < rows.length; index++) ...[
                          _ProfileRow(item: rows[index]),
                          if (index < rows.length - 1)
                            const Divider(
                              height: 1,
                              indent: 66,
                              endIndent: 16,
                              color: LoginColors.fieldBorder,
                            ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  const _ModelScopeCard(),
                  const SizedBox(height: 26),
                  const Center(
                    child: Text(
                      'PhytoScan · ผู้ช่วยดูแลพืชอัจฉริยะ',
                      style: TextStyle(
                        color: LoginColors.secondaryText,
                        fontSize: 11,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileHero extends StatelessWidget {
  const _ProfileHero();

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
            right: -24,
            top: -20,
            child: Icon(
              Icons.eco_outlined,
              size: 190,
              color: LoginColors.white.withValues(alpha: 0.06),
            ),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(22, 28, 22, 46),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.spa_outlined,
                      color: LoginColors.accentGreen,
                      size: 19,
                    ),
                    SizedBox(width: 7),
                    Text(
                      'โปรไฟล์ของคุณ',
                      style: TextStyle(
                        color: LoginColors.accentGreen,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
                Spacer(),
                Text(
                  'โปรไฟล์',
                  style: TextStyle(
                    color: LoginColors.white,
                    fontSize: 30,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.4,
                  ),
                ),
                SizedBox(height: 5),
                Text(
                  'จัดการข้อมูลและตรวจสอบขอบเขตของระบบ',
                  style: TextStyle(color: Color(0xBFFFFFFF), fontSize: 14),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GuestCard extends StatelessWidget {
  const _GuestCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: LoginColors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: LoginColors.fieldBorder),
        boxShadow: const [
          BoxShadow(
            color: Color(0x120E2717),
            blurRadius: 20,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 58,
            height: 58,
            decoration: const BoxDecoration(
              color: LoginColors.segmentTrack,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.person_outline_rounded,
              color: LoginColors.primaryGreen,
              size: 28,
            ),
          ),
          const SizedBox(width: 14),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ผู้ใช้ทั่วไป',
                  style: TextStyle(
                    color: LoginColors.primaryText,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'ใช้งานโดยไม่เข้าสู่ระบบ',
                  style: TextStyle(
                    color: LoginColors.secondaryText,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: LoginColors.segmentTrack,
              borderRadius: BorderRadius.circular(999),
            ),
            child: const Text(
              'ใช้งานในเครื่อง',
              style: TextStyle(
                color: LoginColors.primaryGreen,
                fontSize: 10,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.title, required this.caption});

  final String title;
  final String caption;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              color: LoginColors.primaryText,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Text(
          caption,
          style: const TextStyle(
            color: LoginColors.secondaryText,
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}

class _ProfileRow extends StatelessWidget {
  const _ProfileRow({required this.item});

  final _ProfileItem item;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: LoginColors.segmentTrack.withValues(alpha: 0.75),
              borderRadius: BorderRadius.circular(13),
            ),
            child: Icon(item.icon, size: 20, color: LoginColors.primaryGreen),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: const TextStyle(
                    color: LoginColors.primaryText,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  item.subtitle,
                  style: const TextStyle(
                    color: LoginColors.secondaryText,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const Icon(
            Icons.chevron_right_rounded,
            color: LoginColors.secondaryText,
            size: 20,
          ),
        ],
      ),
    );
  }
}

class _ModelScopeCard extends StatelessWidget {
  const _ModelScopeCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFEAF2E6),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: LoginColors.fieldBorder),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.verified_user_outlined,
            color: LoginColors.primaryGreen,
            size: 21,
          ),
          SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ขอบเขตการวิเคราะห์',
                  style: TextStyle(
                    color: LoginColors.primaryText,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  'รองรับพืช 6 ชนิดตามรายการในระบบ ผลลัพธ์เป็นการประเมินเบื้องต้นจากระบบปัญญาประดิษฐ์',
                  style: TextStyle(
                    color: LoginColors.secondaryText,
                    fontSize: 12,
                    height: 1.45,
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

class _ProfileItem {
  const _ProfileItem(this.icon, this.title, this.subtitle);

  final IconData icon;
  final String title;
  final String subtitle;
}
