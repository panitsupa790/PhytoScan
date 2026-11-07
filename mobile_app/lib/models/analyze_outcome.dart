import 'analyze_result.dart';

sealed class AnalyzeOutcome {
  const AnalyzeOutcome();

  factory AnalyzeOutcome.fromJson(Map<String, dynamic> json) {
    return switch (json['status']) {
      'completed' => CompletedAnalyzeOutcome(AnalyzeResult.fromJson(json)),
      'manual_confirmation_required' => ManualConfirmationOutcome.fromJson(
        json,
      ),
      _ => throw const FormatException('Unknown analysis response status'),
    };
  }
}

final class CompletedAnalyzeOutcome extends AnalyzeOutcome {
  const CompletedAnalyzeOutcome(this.result, {this.scanId});

  final AnalyzeResult result;
  final String? scanId;
}

final class ManualConfirmationOutcome extends AnalyzeOutcome {
  const ManualConfirmationOutcome({
    required this.message,
    required this.suggestedPlant,
    required this.imagePredictions,
    required this.reasons,
  });

  final String message;
  final PredictionLabel? suggestedPlant;
  final List<ImagePlantPrediction> imagePredictions;
  final List<String> reasons;

  bool get hasInconsistentPlants => reasons.contains('inconsistent_plant');

  factory ManualConfirmationOutcome.fromJson(Map<String, dynamic> json) {
    final suggested = json['suggested_plant'];
    return ManualConfirmationOutcome(
      message: json['message'] as String? ?? '',
      suggestedPlant: suggested == null
          ? null
          : PredictionLabel.fromJson(suggested as Map<String, dynamic>),
      imagePredictions: (json['image_predictions'] as List<dynamic>)
          .map(
            (item) =>
                ImagePlantPrediction.fromJson(item as Map<String, dynamic>),
          )
          .toList(growable: false),
      reasons: (json['reasons'] as List<dynamic>).cast<String>(),
    );
  }
}

class ImagePlantPrediction {
  const ImagePlantPrediction({
    required this.index,
    required this.filename,
    required this.plant,
    required this.margin,
    required this.accepted,
    required this.reasons,
  });

  final int index;
  final String filename;
  final PredictionLabel plant;
  final double margin;
  final bool accepted;
  final List<String> reasons;

  factory ImagePlantPrediction.fromJson(Map<String, dynamic> json) {
    return ImagePlantPrediction(
      index: json['index'] as int,
      filename: json['filename'] as String? ?? '',
      plant: PredictionLabel.fromJson(json['plant'] as Map<String, dynamic>),
      margin: (json['margin'] as num).toDouble(),
      accepted: json['accepted'] as bool,
      reasons: (json['reasons'] as List<dynamic>? ?? const []).cast<String>(),
    );
  }
}
