import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'screens/splash_screen.dart';
import 'services/api_service.dart';
import 'services/scan_history_store.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({
    super.key,
    this.api = const ApiService(),
    this.startAtHome = false,
  });

  final PhytoScanApi api;
  final bool startAtHome;

  @override
  Widget build(BuildContext context) {
    final historyStore = api is RemoteScanHistoryApi
        ? SyncedScanHistoryStore(remote: api as RemoteScanHistoryApi)
        : const ScanHistoryStore();
    return MaterialApp(
      title: 'PhytoScan',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: startAtHome
          ? HomeScreen(api: api, historyStore: historyStore)
          : SplashScreen(api: api, historyStore: historyStore),
    );
  }
}
