class PredictionLabel {
  const PredictionLabel({
    required this.code,
    required this.nameTh,
    required this.nameEn,
    required this.confidence,
  });

  static const double mediumConfidenceMinimum = 0.55;

  final String code;
  final String nameTh;
  final String nameEn;
  final double confidence;

  String get displayName => nameTh.trim().isNotEmpty ? nameTh : nameEn;

  factory PredictionLabel.fromJson(Map<String, dynamic> json) {
    return PredictionLabel(
      code: json['code'] as String,
      nameTh: json['name_th'] as String? ?? '',
      nameEn: json['name_en'] as String? ?? json['code'] as String,
      confidence: (json['confidence'] as num).toDouble(),
    );
  }
}

class ImageResult {
  const ImageResult({
    required this.index,
    required this.filename,
    required this.disease,
    required this.symptoms,
    required this.care,
    required this.prevention,
  });

  final int index;
  final String filename;
  final PredictionLabel disease;
  final List<String> symptoms;
  final List<String> care;
  final List<String> prevention;

  bool get hasDetails =>
      symptoms.isNotEmpty || care.isNotEmpty || prevention.isNotEmpty;

  factory ImageResult.fromJson(Map<String, dynamic> json) {
    List<String> strings(String key) =>
        (json[key] as List<dynamic>? ?? const []).cast<String>();

    return ImageResult(
      index: json['index'] as int,
      filename: json['filename'] as String? ?? '',
      disease: PredictionLabel.fromJson(
        json['disease'] as Map<String, dynamic>,
      ),
      symptoms: strings('symptoms'),
      care: strings('care'),
      prevention: strings('prevention'),
    );
  }
}
