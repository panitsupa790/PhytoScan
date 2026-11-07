import 'package:flutter/material.dart';

/// Login-specific tokens for the Botanical Premium visual language.
///
/// These tokens are intentionally not installed into the global [ThemeData]
/// yet, so the page-by-page redesign does not change existing screens.
abstract final class LoginColors {
  static const primaryGreen = Color(0xFF24361B);
  static const darkBotanicalGreen = Color(0xFF172C20);
  static const heroTop = Color(0xFF1D3928);
  static const heroBottom = Color(0xFF2B5036);
  static const accentGreen = Color(0xFF98CC6B);
  static const orangeHighlight = Color(0xFFED7A3B);
  static const backgroundCream = Color(0xFFEEF2EC);
  static const sheetSurface = Color(0xFFF7F9F4);
  static const segmentTrack = Color(0xFFDDE5DA);
  static const white = Color(0xFFFFFFFF);
  static const primaryText = Color(0xFF1B3021);
  static const secondaryText = Color(0xFF637065);
  static const fieldBorder = Color(0xFFD5DDD3);
}

abstract final class LoginSpacing {
  static const xSmall = 6.0;
  static const small = 10.0;
  static const medium = 16.0;
  static const large = 24.0;
  static const xLarge = 32.0;
}

abstract final class LoginRadii {
  static const small = 14.0;
  static const medium = 18.0;
  static const sheet = 30.0;
}
