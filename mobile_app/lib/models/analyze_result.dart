import 'image_result.dart';

export 'image_result.dart';

class AnalyzeResult {
  const AnalyzeResult({
    required this.imageCount,
    required this.plant,
    required this.disease,
    required this.symptoms,
    required this.care,
    required this.prevention,
    required this.imageResults,
  });

  final int imageCount;
  final PredictionLabel plant;
  final PredictionLabel disease;
  final List<String> symptoms;
  final List<String> care;
  final List<String> prevention;
  final List<ImageResult> imageResults;

  bool get resultsAgree =>
      imageResults.isNotEmpty &&
      imageResults.every(
        (item) => item.disease.code == imageResults.first.disease.code,
      );

  factory AnalyzeResult.fromJson(Map<String, dynamic> json) {
    List<String> strings(String key) =>
        (json[key] as List<dynamic>? ?? const []).cast<String>();

    return AnalyzeResult(
      imageCount: json['image_count'] as int,
      plant: PredictionLabel.fromJson(json['plant'] as Map<String, dynamic>),
      disease: PredictionLabel.fromJson(
        json['disease'] as Map<String, dynamic>,
      ),
      symptoms: strings('symptoms'),
      care: strings('care'),
      prevention: strings('prevention'),
      imageResults: (json['image_results'] as List<dynamic>? ?? const [])
          .map((item) => ImageResult.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}
