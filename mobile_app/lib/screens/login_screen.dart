import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/api_service.dart';
import '../services/scan_history_store.dart';
import '../theme/login_design_tokens.dart';
import '../widgets/botanical_login_hero.dart';
import '../widgets/primary_button.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.api,
    this.historyStore = const ScanHistoryStore(),
  });

  final PhytoScanApi api;
  final ScanHistoryRepository historyStore;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _emailFocusNode = FocusNode();
  final _passwordFocusNode = FocusNode();
  bool _obscurePassword = true;

  void _continueAsGuest() {
    FocusManager.instance.primaryFocus?.unfocus();
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) =>
            HomeScreen(api: widget.api, historyStore: widget.historyStore),
      ),
    );
  }

  void _authUnavailable() {
    FocusManager.instance.primaryFocus?.unfocus();
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        const SnackBar(
          content: Text('ระบบบัญชียังไม่เปิดใช้งาน กรุณาใช้งานแบบผู้ใช้ทั่วไป'),
        ),
      );
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _emailFocusNode.dispose();
    _passwordFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final viewInsets = MediaQuery.viewInsetsOf(context);

    const overlayStyle = SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
      systemNavigationBarColor: LoginColors.sheetSurface,
      systemNavigationBarIconBrightness: Brightness.dark,
      systemNavigationBarDividerColor: Colors.transparent,
      systemStatusBarContrastEnforced: false,
      systemNavigationBarContrastEnforced: false,
    );

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: overlayStyle,
      child: Scaffold(
        backgroundColor: LoginColors.heroTop,
        resizeToAvoidBottomInset: true,
        body: SafeArea(
          bottom: false,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final textScale = MediaQuery.textScalerOf(context).scale(16) / 16;
              final scaleAllowance = ((textScale - 1).clamp(0, 1)) * 360;
              final widthAllowance = constraints.maxWidth < 360 ? 48.0 : 0.0;
              final heroHeight =
                  (constraints.maxHeight * 0.34).clamp(290.0, 305.0) +
                  scaleAllowance +
                  widthAllowance;
              final sheetOverlap = textScale > 1.2 ? 30.0 : 42.0;
              return SingleChildScrollView(
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                padding: EdgeInsets.only(bottom: viewInsets.bottom),
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: Stack(
                    clipBehavior: Clip.none,
                    children: [
                      Positioned(
                        top: 0,
                        left: 0,
                        right: 0,
                        height: heroHeight,
                        child: const BotanicalLoginHero(),
                      ),
                      Padding(
                        padding: EdgeInsets.only(
                          top: heroHeight - sheetOverlap,
                        ),
                        child: _AuthenticationSheet(
                          emailController: _emailController,
                          passwordController: _passwordController,
                          emailFocusNode: _emailFocusNode,
                          passwordFocusNode: _passwordFocusNode,
                          obscurePassword: _obscurePassword,
                          onTogglePassword: () => setState(
                            () => _obscurePassword = !_obscurePassword,
                          ),
                          onLogin: _authUnavailable,
                          onRegister: _authUnavailable,
                          onForgotPassword: _authUnavailable,
                          onGuest: _continueAsGuest,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _AuthenticationSheet extends StatelessWidget {
  const _AuthenticationSheet({
    required this.emailController,
    required this.passwordController,
    required this.emailFocusNode,
    required this.passwordFocusNode,
    required this.obscurePassword,
    required this.onTogglePassword,
    required this.onLogin,
    required this.onRegister,
    required this.onForgotPassword,
    required this.onGuest,
  });

  final TextEditingController emailController;
  final TextEditingController passwordController;
  final FocusNode emailFocusNode;
  final FocusNode passwordFocusNode;
  final bool obscurePassword;
  final VoidCallback onTogglePassword;
  final VoidCallback onLogin;
  final VoidCallback onRegister;
  final VoidCallback onForgotPassword;
  final VoidCallback onGuest;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fieldTheme = theme.copyWith(
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: LoginColors.white,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        labelStyle: const TextStyle(color: LoginColors.secondaryText),
        prefixIconColor: LoginColors.secondaryText,
        suffixIconColor: LoginColors.secondaryText,
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(LoginRadii.medium),
          borderSide: const BorderSide(color: LoginColors.fieldBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(LoginRadii.medium),
          borderSide: const BorderSide(
            color: LoginColors.accentGreen,
            width: 1.8,
          ),
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(LoginRadii.medium),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          backgroundColor: LoginColors.primaryGreen,
          foregroundColor: LoginColors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(LoginRadii.medium),
          ),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      ),
    );
    final bottomSafeArea = MediaQuery.paddingOf(context).bottom;

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: LoginColors.sheetSurface,
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(LoginRadii.sheet),
        ),
        boxShadow: [
          BoxShadow(
            color: LoginColors.darkBotanicalGreen.withValues(alpha: 0.13),
            blurRadius: 28,
            offset: const Offset(0, -8),
          ),
        ],
      ),
      child: Padding(
        padding: EdgeInsets.fromLTRB(24, 10, 24, 34 + bottomSafeArea),
        child: Theme(
          data: fieldTheme,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 38,
                  height: 5,
                  decoration: BoxDecoration(
                    color: LoginColors.primaryText.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(99),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              const Text(
                'ยินดีต้อนรับ',
                style: TextStyle(
                  color: LoginColors.primaryText,
                  fontSize: 27,
                  height: 1.2,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'เข้าสู่บัญชีของคุณ หรือใช้งานต่อแบบผู้ใช้ทั่วไป',
                style: TextStyle(
                  color: LoginColors.secondaryText,
                  fontSize: 14,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 18),
              _AuthSegmentedControl(onRegister: onRegister),
              const SizedBox(height: 20),
              _PremiumInputShell(
                focusNode: emailFocusNode,
                child: TextField(
                  key: const Key('loginEmailField'),
                  controller: emailController,
                  focusNode: emailFocusNode,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  autofillHints: const [AutofillHints.email],
                  onSubmitted: (_) => passwordFocusNode.requestFocus(),
                  decoration: const InputDecoration(
                    labelText: 'อีเมล',
                    hintText: 'กรอกอีเมล',
                    prefixIcon: Icon(CupertinoIcons.mail, size: 22),
                  ),
                ),
              ),
              const SizedBox(height: 13),
              _PremiumInputShell(
                focusNode: passwordFocusNode,
                child: TextField(
                  key: const Key('loginPasswordField'),
                  controller: passwordController,
                  focusNode: passwordFocusNode,
                  obscureText: obscurePassword,
                  textInputAction: TextInputAction.done,
                  autofillHints: const [AutofillHints.password],
                  onSubmitted: (_) => onLogin(),
                  decoration: InputDecoration(
                    labelText: 'รหัสผ่าน',
                    prefixIcon: const Icon(CupertinoIcons.lock, size: 22),
                    suffixIcon: IconButton(
                      key: const Key('passwordVisibilityButton'),
                      tooltip: obscurePassword
                          ? 'แสดงรหัสผ่าน'
                          : 'ซ่อนรหัสผ่าน',
                      onPressed: onTogglePassword,
                      icon: Icon(
                        obscurePassword
                            ? CupertinoIcons.eye
                            : CupertinoIcons.eye_slash,
                        size: 22,
                      ),
                    ),
                  ),
                ),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  key: const Key('forgotPasswordButton'),
                  onPressed: onForgotPassword,
                  style: TextButton.styleFrom(
                    foregroundColor: LoginColors.primaryGreen,
                    minimumSize: const Size(48, 44),
                  ),
                  child: const Text('ลืมรหัสผ่าน?'),
                ),
              ),
              const SizedBox(height: 2),
              PrimaryButton(
                key: const Key('loginButton'),
                label: 'เข้าสู่ระบบ',
                onPressed: onLogin,
              ),
              const SizedBox(height: 19),
              const _OrDivider(),
              const SizedBox(height: 19),
              OutlinedButton.icon(
                key: const Key('guestButton'),
                onPressed: onGuest,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(54),
                  backgroundColor: LoginColors.white,
                  foregroundColor: LoginColors.primaryGreen,
                  side: const BorderSide(color: LoginColors.fieldBorder),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(LoginRadii.medium),
                  ),
                ),
                icon: const Icon(CupertinoIcons.arrow_right, size: 19),
                label: const Text('ใช้งานแบบผู้ใช้ทั่วไป'),
              ),
              const SizedBox(height: 16),
              const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: EdgeInsets.only(top: 2),
                    child: Icon(
                      CupertinoIcons.info_circle,
                      size: 16,
                      color: LoginColors.secondaryText,
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'ผู้ใช้ทั่วไปสามารถตรวจพืชได้โดยไม่บันทึกประวัติเข้าบัญชี',
                      style: TextStyle(
                        color: LoginColors.secondaryText,
                        fontSize: 12,
                        height: 1.45,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PremiumInputShell extends StatelessWidget {
  const _PremiumInputShell({required this.focusNode, required this.child});

  final FocusNode focusNode;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: focusNode,
      builder: (context, _) {
        final focused = focusNode.hasFocus;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(LoginRadii.medium),
            boxShadow: [
              BoxShadow(
                color: focused
                    ? LoginColors.accentGreen.withValues(alpha: 0.2)
                    : LoginColors.darkBotanicalGreen.withValues(alpha: 0.055),
                blurRadius: focused ? 18 : 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: child,
        );
      },
    );
  }
}

class _AuthSegmentedControl extends StatelessWidget {
  const _AuthSegmentedControl({required this.onRegister});

  final VoidCallback onRegister;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 48,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: LoginColors.segmentTrack,
        borderRadius: BorderRadius.circular(LoginRadii.medium),
        border: Border.all(
          color: LoginColors.primaryText.withValues(alpha: 0.06),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Semantics(
              selected: true,
              button: true,
              child: Container(
                key: const Key('loginSegment'),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: LoginColors.white,
                  borderRadius: BorderRadius.circular(LoginRadii.small),
                  boxShadow: [
                    BoxShadow(
                      color: LoginColors.darkBotanicalGreen.withValues(
                        alpha: 0.13,
                      ),
                      blurRadius: 12,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: const Text(
                  'เข้าสู่ระบบ',
                  style: TextStyle(
                    color: LoginColors.primaryText,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ),
          Expanded(
            child: Semantics(
              button: true,
              child: InkWell(
                key: const Key('registerSegment'),
                onTap: onRegister,
                borderRadius: BorderRadius.circular(LoginRadii.small),
                child: const Center(
                  child: Text(
                    'สมัครสมาชิก',
                    style: TextStyle(
                      color: LoginColors.primaryText,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
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

class _OrDivider extends StatelessWidget {
  const _OrDivider();

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        Expanded(child: Divider(color: LoginColors.fieldBorder)),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: 14),
          child: Text(
            'หรือ',
            style: TextStyle(
              color: LoginColors.secondaryText,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        Expanded(child: Divider(color: LoginColors.fieldBorder)),
      ],
    );
  }
}
