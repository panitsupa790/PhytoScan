class Plant {
  const Plant({
    required this.code,
    required this.nameTh,
    required this.nameEn,
    required this.diseaseCount,
  });

  final String code;
  final String nameTh;
  final String nameEn;
  final int diseaseCount;

  factory Plant.fromJson(Map<String, dynamic> json) {
    return Plant(
      code: json['code'] as String,
      nameTh: json['name_th'] as String,
      nameEn: json['name_en'] as String,
      diseaseCount: json['disease_count'] as int? ?? 0,
    );
  }
}
