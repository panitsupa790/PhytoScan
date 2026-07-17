// lib/main.dart
import 'package:flutter/material.dart';
import 'package:mobile_app/screens/login_screen.dart';
import 'package:mobile_app/screens/home_screen.dart';
// Import แพ็กเกจสำหรับเช็กค่าในเครื่อง
import 'package:shared_preferences/shared_preferences.dart'; 

void main() async {
  //จำเป็นต้องมีบรรทัดนี้เมื่อมีการเรียกใช้ SharedPreferences ก่อน runApp
  WidgetsFlutterBinding.ensureInitialized(); 
  
  // เช็กว่าผู้ใช้เคยล็อกอินค้างไว้หรือไม่
  final prefs = await SharedPreferences.getInstance();
  final bool isLoggedIn = prefs.getBool('isLoggedIn') ?? false;

  runApp(MyApp(isLoggedIn: isLoggedIn));
}

class MyApp extends StatelessWidget {
  final bool isLoggedIn;
  
  const MyApp({super.key, required this.isLoggedIn});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PhytoScan',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF00BFA5)),
        useMaterial3: true,
      ),
      debugShowCheckedModeBanner: false,
      // สลับหน้าแรกตามสถานะล็อกอิน: ถ้าล็อกอินแล้วไป HomeScreen ทันที ถ้ายังไม่เคยล็อกอินให้ไป LoginScreen
      home: isLoggedIn ? const HomeScreen() : const LoginScreen(),
    );
  }
}