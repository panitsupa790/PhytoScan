class AnalysisResult {
  final bool success;
  final int imageCount;
  final PlantPrediction plant;
  final DiseasePrediction disease;
  final List<String> symptoms;
  final List<String> care;
  final List<String> prevention;

  const AnalysisResult({
    required this.success,
    required this.imageCount,
    required this.plant,
    required this.disease,
    required this.symptoms,
    required this.care,
    required this.prevention,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    final success = json['success'];
    if (success != true) {
      throw const FormatException('Analysis response was not successful.');
    }

    final imageCount = _readInt(json, 'image_count');
    if (imageCount < 1 || imageCount > 3) {
      throw const FormatException('image_count must be between 1 and 3.');
    }

    return AnalysisResult(
      success: true,
      imageCount: imageCount,
      plant: PlantPrediction.fromJson(_readMap(json, 'plant')),
      disease: DiseasePrediction.fromJson(_readMap(json, 'disease')),
      symptoms: _readStringList(json, 'symptoms'),
      care: _readStringList(json, 'care'),
      prevention: _readStringList(json, 'prevention'),
    );
  }
}

class PlantPrediction {
  final String code;
  final String nameTh;
  final String nameEn;
  final double confidence;

  const PlantPrediction({
    required this.code,
    required this.nameTh,
    required this.nameEn,
    required this.confidence,
  });

  factory PlantPrediction.fromJson(Map<String, dynamic> json) {
    return PlantPrediction(
      code: _readString(json, 'code'),
      nameTh: _readString(json, 'name_th'),
      nameEn: _readString(json, 'name_en'),
      confidence: _readConfidence(json),
    );
  }
}

class DiseasePrediction {
  final String code;
  final String nameTh;
  final String nameEn;
  final double confidence;

  const DiseasePrediction({
    required this.code,
    required this.nameTh,
    required this.nameEn,
    required this.confidence,
  });

  factory DiseasePrediction.fromJson(Map<String, dynamic> json) {
    return DiseasePrediction(
      code: _readString(json, 'code'),
      nameTh: _readString(json, 'name_th'),
      nameEn: _readString(json, 'name_en'),
      confidence: _readConfidence(json),
    );
  }
}

Map<String, dynamic> _readMap(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! Map) {
    throw FormatException('$key must be an object.');
  }
  return value.cast<String, dynamic>();
}

String _readString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String || value.trim().isEmpty) {
    throw FormatException('$key must be a non-empty string.');
  }
  return value;
}

int _readInt(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! int) {
    throw FormatException('$key must be an integer.');
  }
  return value;
}

double _readConfidence(Map<String, dynamic> json) {
  final value = json['confidence'];
  if (value is! num) {
    throw const FormatException('confidence must be numeric.');
  }

  final confidence = value.toDouble();
  if (confidence < 0 || confidence > 1) {
    throw const FormatException('confidence must be between 0 and 1.');
  }
  return confidence;
}

List<String> _readStringList(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! List || value.any((item) => item is! String)) {
    throw FormatException('$key must be a list of strings.');
  }
  return List<String>.unmodifiable(value.cast<String>());
}
