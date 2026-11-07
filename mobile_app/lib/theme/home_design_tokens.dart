import 'package:flutter/material.dart';

import 'login_design_tokens.dart';

/// Home-only extensions of the Botanical Premium design language.
///
/// Core colours intentionally come from [LoginColors] so the page-by-page
/// redesign stays visually consistent without changing the global theme.
abstract final class HomeColors {
  static const identifySoft = Color(0xFFFFE7D7);
  static const diagnoseSoft = Color(0xFFDDEBF3);
  static const tipSurface = Color(0xFF173A37);
  static const navInactive = Color(0xFF748078);
  static const subtleBorder = Color(0xFFE1E7DF);
  static const searchSurface = Color(0x29FFFFFF);
  static const searchBorder = Color(0x38FFFFFF);

  static const background = LoginColors.backgroundCream;
  static const surface = LoginColors.sheetSurface;
  static const primary = LoginColors.primaryGreen;
  static const heroTop = LoginColors.heroTop;
  static const heroBottom = LoginColors.heroBottom;
  static const accent = LoginColors.accentGreen;
  static const orange = LoginColors.orangeHighlight;
  static const text = LoginColors.primaryText;
  static const textSecondary = LoginColors.secondaryText;
  static const white = LoginColors.white;
}

abstract final class HomeRadii {
  static const card = 24.0;
  static const control = 18.0;
  static const sheet = 30.0;
}
