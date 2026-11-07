class PlantLibrarySummary {
  const PlantLibrarySummary({
    required this.plantCode,
    required this.nameTh,
    required this.nameEn,
    required this.scientificName,
    required this.summaryTh,
    required this.coverImage,
    required this.coverAltTextTh,
    required this.supportedDiseaseCount,
    required this.reviewStatus,
  });

  final String plantCode;
  final String nameTh;
  final String nameEn;
  final String scientificName;
  final String summaryTh;
  final String coverImage;
  final String coverAltTextTh;
  final int supportedDiseaseCount;
  final String reviewStatus;

  factory PlantLibrarySummary.fromJson(Map<String, dynamic> json) {
    return PlantLibrarySummary(
      plantCode: json['plant_code'] as String,
      nameTh: json['name_th'] as String,
      nameEn: json['name_en'] as String,
      scientificName: json['scientific_name'] as String,
      summaryTh: json['summary_th'] as String,
      coverImage: json['cover_image'] as String,
      coverAltTextTh: json['cover_alt_text_th'] as String,
      supportedDiseaseCount: json['supported_disease_count'] as int,
      reviewStatus: json['review_status'] as String,
    );
  }
}

class PlantLibraryDetail {
  const PlantLibraryDetail({
    required this.plantCode,
    required this.nameTh,
    required this.nameEn,
    required this.otherNamesTh,
    required this.otherNamesEn,
    required this.taxonomy,
    required this.overview,
    required this.identification,
    required this.care,
    required this.safety,
    required this.scanGuidance,
    required this.supportedDiseaseCodes,
    required this.media,
    required this.sources,
    required this.review,
  });

  final String plantCode;
  final String nameTh;
  final String nameEn;
  final PlantTaxonomy taxonomy;
  final PlantOverview overview;
  final List<String> otherNamesTh;
  final List<String> otherNamesEn;
  final PlantIdentification identification;
  final PlantCare care;
  final PlantSafety safety;
  final PlantScanGuidance scanGuidance;
  final List<String> supportedDiseaseCodes;
  final PlantMedia media;
  final List<PlantSource> sources;
  final PlantReview review;

  factory PlantLibraryDetail.fromJson(Map<String, dynamic> json) {
    return PlantLibraryDetail(
      plantCode: json['plant_code'] as String,
      nameTh: json['name_th'] as String,
      nameEn: json['name_en'] as String,
      otherNamesTh: _strings(json['other_names_th']),
      otherNamesEn: _strings(json['other_names_en']),
      taxonomy: PlantTaxonomy.fromJson(_map(json['taxonomy'])),
      overview: PlantOverview.fromJson(_map(json['overview'])),
      identification: PlantIdentification.fromJson(
        _map(json['identification']),
      ),
      care: PlantCare.fromJson(_map(json['care'])),
      safety: PlantSafety.fromJson(_map(json['safety'])),
      scanGuidance: PlantScanGuidance.fromJson(_map(json['scan_guidance'])),
      supportedDiseaseCodes: _strings(json['supported_disease_codes']),
      media: PlantMedia.fromJson(_map(json['media'])),
      sources: (json['sources'] as List<dynamic>)
          .map((item) => PlantSource.fromJson(_map(item)))
          .toList(growable: false),
      review: PlantReview.fromJson(_map(json['review'])),
    );
  }
}

class PlantTaxonomy {
  const PlantTaxonomy({
    required this.scientificName,
    required this.family,
    required this.genus,
    required this.notes,
  });

  final String scientificName;
  final String family;
  final String genus;
  final String notes;

  factory PlantTaxonomy.fromJson(Map<String, dynamic> json) => PlantTaxonomy(
    scientificName: json['scientific_name'] as String,
    family: json['family'] as String,
    genus: json['genus'] as String,
    notes: json['species_or_cultivar_notes'] as String,
  );
}

class PlantOverview {
  const PlantOverview({
    required this.summaryTh,
    required this.summaryEn,
    required this.origin,
    required this.growthHabit,
    required this.height,
  });

  final String summaryTh;
  final String summaryEn;
  final String origin;
  final String growthHabit;
  final NumericRange height;

  factory PlantOverview.fromJson(Map<String, dynamic> json) => PlantOverview(
    summaryTh: json['summary_th'] as String,
    summaryEn: json['summary_en'] as String,
    origin: json['origin'] as String,
    growthHabit: json['growth_habit'] as String,
    height: NumericRange.fromJson(_map(json['typical_height_cm'])),
  );
}

class NumericRange {
  const NumericRange({this.min, this.max});

  final num? min;
  final num? max;

  factory NumericRange.fromJson(Map<String, dynamic> json) =>
      NumericRange(min: json['min'] as num?, max: json['max'] as num?);

  String format({String suffix = ''}) {
    if (min == null && max == null) return 'ไม่ระบุ';
    if (min == null) return 'ไม่เกิน $max$suffix';
    if (max == null) return 'ตั้งแต่ $min$suffix';
    return '$min–$max$suffix';
  }
}

class PlantIdentification {
  const PlantIdentification({
    required this.leafShape,
    required this.leafColor,
    required this.stemFeatures,
    required this.flowerFeatures,
    required this.distinguishingFeatures,
  });

  final List<String> leafShape;
  final List<String> leafColor;
  final List<String> stemFeatures;
  final List<String> flowerFeatures;
  final List<String> distinguishingFeatures;

  factory PlantIdentification.fromJson(Map<String, dynamic> json) {
    return PlantIdentification(
      leafShape: _strings(json['leaf_shape']),
      leafColor: _strings(json['leaf_color']),
      stemFeatures: _strings(json['stem_features']),
      flowerFeatures: _strings(json['flower_features']),
      distinguishingFeatures: _strings(json['distinguishing_features']),
    );
  }
}

class PlantCareTopic {
  const PlantCareTopic({
    required this.details,
    this.level,
    this.frequency,
    this.type,
    this.warningSigns = const [],
    this.phRange,
  });

  final String details;
  final String? level;
  final String? frequency;
  final String? type;
  final List<String> warningSigns;
  final NumericRange? phRange;

  factory PlantCareTopic.fromJson(Map<String, dynamic> json) => PlantCareTopic(
    details: json['details'] as String,
    level: json['level'] as String?,
    frequency: json['frequency'] as String?,
    type: json['type'] as String?,
    warningSigns: _strings(json['warning_signs']),
    phRange: json['ph_range'] == null
        ? null
        : NumericRange.fromJson(_map(json['ph_range'])),
  );
}

class PlantTemperature {
  const PlantTemperature({required this.range, required this.details});

  final NumericRange range;
  final String details;

  factory PlantTemperature.fromJson(Map<String, dynamic> json) {
    return PlantTemperature(
      range: NumericRange.fromJson(json),
      details: json['details'] as String,
    );
  }
}

class PlantCare {
  const PlantCare({
    required this.light,
    required this.watering,
    required this.soil,
    required this.temperature,
    required this.humidity,
    required this.fertilizer,
    required this.pruning,
    required this.repotting,
  });

  final PlantCareTopic light;
  final PlantCareTopic watering;
  final PlantCareTopic soil;
  final PlantTemperature temperature;
  final PlantCareTopic humidity;
  final PlantCareTopic fertilizer;
  final String pruning;
  final String repotting;

  factory PlantCare.fromJson(Map<String, dynamic> json) => PlantCare(
    light: PlantCareTopic.fromJson(_map(json['light'])),
    watering: PlantCareTopic.fromJson(_map(json['watering'])),
    soil: PlantCareTopic.fromJson(_map(json['soil'])),
    temperature: PlantTemperature.fromJson(_map(json['temperature_c'])),
    humidity: PlantCareTopic.fromJson(_map(json['humidity'])),
    fertilizer: PlantCareTopic.fromJson(_map(json['fertilizer'])),
    pruning: json['pruning'] as String,
    repotting: json['repotting'] as String,
  );
}

class PlantSafety {
  const PlantSafety({
    required this.toxicityHumans,
    required this.toxicityPets,
    required this.handlingNotes,
  });

  final String toxicityHumans;
  final String toxicityPets;
  final List<String> handlingNotes;

  factory PlantSafety.fromJson(Map<String, dynamic> json) => PlantSafety(
    toxicityHumans: json['toxicity_humans'] as String,
    toxicityPets: json['toxicity_pets'] as String,
    handlingNotes: _strings(json['handling_notes']),
  );
}

class PlantScanGuidance {
  const PlantScanGuidance({
    required this.recommendedParts,
    required this.captureTips,
    required this.avoid,
  });

  final List<String> recommendedParts;
  final List<String> captureTips;
  final List<String> avoid;

  factory PlantScanGuidance.fromJson(Map<String, dynamic> json) {
    return PlantScanGuidance(
      recommendedParts: _strings(json['recommended_parts']),
      captureTips: _strings(json['capture_tips']),
      avoid: _strings(json['avoid']),
    );
  }
}

class PlantGalleryImage {
  const PlantGalleryImage({
    required this.image,
    required this.altTextTh,
    required this.source,
    required this.license,
    required this.attribution,
  });

  final String image;
  final String altTextTh;
  final String source;
  final String license;
  final String attribution;

  factory PlantGalleryImage.fromJson(Map<String, dynamic> json) {
    return PlantGalleryImage(
      image: json['image'] as String,
      altTextTh: json['alt_text_th'] as String,
      source: json['source'] as String,
      license: json['license'] as String,
      attribution: json['attribution'] as String,
    );
  }
}

class PlantMedia {
  const PlantMedia({
    required this.coverImage,
    required this.coverAltTextTh,
    required this.gallery,
    required this.source,
    required this.license,
  });

  final String coverImage;
  final String coverAltTextTh;
  final List<PlantGalleryImage> gallery;
  final String source;
  final String license;

  factory PlantMedia.fromJson(Map<String, dynamic> json) => PlantMedia(
    coverImage: json['cover_image'] as String,
    coverAltTextTh: json['cover_alt_text_th'] as String,
    gallery: (json['gallery'] as List<dynamic>)
        .map((item) => PlantGalleryImage.fromJson(_map(item)))
        .toList(growable: false),
    source: json['source'] as String,
    license: json['license'] as String,
  );
}

class PlantSource {
  const PlantSource({
    required this.title,
    required this.url,
    required this.type,
  });

  final String title;
  final String url;
  final String type;

  factory PlantSource.fromJson(Map<String, dynamic> json) => PlantSource(
    title: json['title'] as String,
    url: json['url'] as String,
    type: json['type'] as String,
  );
}

class PlantReview {
  const PlantReview({
    required this.status,
    required this.reviewedBy,
    required this.reviewedAt,
  });

  final String status;
  final String reviewedBy;
  final String? reviewedAt;

  factory PlantReview.fromJson(Map<String, dynamic> json) => PlantReview(
    status: json['status'] as String,
    reviewedBy: json['reviewed_by'] as String,
    reviewedAt: json['reviewed_at'] as String?,
  );
}

Map<String, dynamic> _map(Object? value) => value as Map<String, dynamic>;

List<String> _strings(Object? value) =>
    (value as List<dynamic>? ?? const []).cast<String>();
