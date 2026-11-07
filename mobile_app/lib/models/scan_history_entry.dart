import 'analyze_result.dart';

class ScanHistoryEntry {
  const ScanHistoryEntry({
    required this.id,
    required this.analyzedAt,
    required this.plantCode,
    required this.plantName,
    required this.plantConfidence,
    required this.diseaseCode,
    required this.diseaseName,
    required this.diseaseConfidence,
    required this.diseaseNames,
    required this.imageCount,
    required this.manuallyConfirmed,
  });

  final String id;
  final DateTime analyzedAt;
  final String plantCode;
  final String plantName;
  final double plantConfidence;
  final String diseaseCode;
  final String diseaseName;
  final double diseaseConfidence;
  final List<String> diseaseNames;
  final int imageCount;
  final bool manuallyConfirmed;

  factory ScanHistoryEntry.fromResult({
    required AnalyzeResult result,
    required bool manuallyConfirmed,
    DateTime? analyzedAt,
    String? id,
  }) {
    final timestamp = analyzedAt ?? DateTime.now();
    final names = result.imageResults
        .map((item) => item.disease.displayName.trim())
        .where((name) => name.isNotEmpty)
        .toSet()
        .toList(growable: false);
    return ScanHistoryEntry(
      id: id ?? '${timestamp.microsecondsSinceEpoch}-${result.plant.code}',
      analyzedAt: timestamp,
      plantCode: result.plant.code,
      plantName: result.plant.displayName,
      plantConfidence: result.plant.confidence,
      diseaseCode: result.disease.code,
      diseaseName: result.disease.displayName,
      diseaseConfidence: result.disease.confidence,
      diseaseNames: names.isEmpty ? [result.disease.displayName] : names,
      imageCount: result.imageCount,
      manuallyConfirmed: manuallyConfirmed,
    );
  }

  factory ScanHistoryEntry.fromJson(Map<String, dynamic> json) {
    final plantNameTh = json['plant_name_th'] as String? ?? '';
    final plantNameEn = json['plant_name_en'] as String? ?? '';
    final diseaseNameTh = json['disease_name_th'] as String? ?? '';
    final diseaseNameEn = json['disease_name_en'] as String? ?? '';
    final source = json['plant_source'] as String?;
    return ScanHistoryEntry(
      id: json['id'] as String,
      analyzedAt: DateTime.parse(json['analyzed_at'] as String),
      plantCode: json['plant_code'] as String? ?? '',
      plantName:
          json['plant_name'] as String? ??
          (plantNameTh.isNotEmpty ? plantNameTh : plantNameEn),
      plantConfidence: (json['plant_confidence'] as num? ?? 0).toDouble(),
      diseaseCode: json['disease_code'] as String? ?? '',
      diseaseName:
          json['disease_name'] as String? ??
          (diseaseNameTh.isNotEmpty ? diseaseNameTh : diseaseNameEn),
      diseaseConfidence: (json['disease_confidence'] as num? ?? 0).toDouble(),
      diseaseNames: (json['disease_names'] as List<dynamic>? ?? const [])
          .cast<String>(),
      imageCount: json['image_count'] as int? ?? 0,
      manuallyConfirmed:
          json['manually_confirmed'] as bool? ??
          (source != null && source != 'automatic'),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'analyzed_at': analyzedAt.toIso8601String(),
    'plant_code': plantCode,
    'plant_name': plantName,
    'plant_confidence': plantConfidence,
    'disease_code': diseaseCode,
    'disease_name': diseaseName,
    'disease_confidence': diseaseConfidence,
    'disease_names': diseaseNames,
    'image_count': imageCount,
    'manually_confirmed': manuallyConfirmed,
  };
}
