import 'package:flutter/material.dart';

import 'login_design_tokens.dart';

/// Scan-page extensions of the shared Botanical Premium visual language.
abstract final class ScanColors {
  static const heroTop = LoginColors.heroTop;
  static const heroBottom = LoginColors.heroBottom;
  static const primary = LoginColors.primaryGreen;
  static const accent = LoginColors.accentGreen;
  static const surface = LoginColors.sheetSurface;
  static const background = LoginColors.backgroundCream;
  static const track = LoginColors.segmentTrack;
  static const border = LoginColors.fieldBorder;
  static const text = LoginColors.primaryText;
  static const textSecondary = LoginColors.secondaryText;
  static const orange = LoginColors.orangeHighlight;
  static const white = LoginColors.white;

  static const instruction = Color(0xFFE9F0E5);
  static const uploadSurface = Color(0xFFF0F4EC);
  static const error = Color(0xFFB84949);
}

abstract final class ScanRadii {
  static const sheet = 36.0;
  static const card = 22.0;
  static const control = 17.0;
}
