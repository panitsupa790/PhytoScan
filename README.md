
```
phytoscan
├─ ai_model
│  ├─ configs
│  │  ├─ eggplant_d9_refinement.json
│  │  ├─ eggplant_efficientnetb0_d8_lite.json
│  │  ├─ eggplant_final_locked.json
│  │  ├─ eggplant_mobilenetv2_d7.json
│  │  └─ eggplant_preprocessing.json
│  ├─ evaluation
│  │  ├─ d11_final_test.py
│  │  └─ __init__.py
│  ├─ experiments
│  │  ├─ eggplant_backend_d12
│  │  │  ├─ D12_REPORT.md
│  │  │  ├─ golden_regression.json
│  │  │  ├─ http_verification.json
│  │  │  ├─ immutable_state_before.json
│  │  │  ├─ immutable_state_verification.json
│  │  │  ├─ performance_baseline.json
│  │  │  ├─ run_integration_verification.py
│  │  │  ├─ validate_d12.py
│  │  │  ├─ validation_result.json
│  │  │  └─ verify_immutable_state.py
│  │  ├─ eggplant_d9_refinement
│  │  │  ├─ comparison
│  │  │  │  ├─ comparison_summary.json
│  │  │  │  ├─ d9_refinement_comparison.csv
│  │  │  │  └─ training_behavior.json
│  │  │  ├─ D9_REPORT.md
│  │  │  ├─ generate_comparison.py
│  │  │  ├─ R1_finetune
│  │  │  │  ├─ augmentation.json
│  │  │  │  ├─ best_model.keras
│  │  │  │  ├─ classification_report.csv
│  │  │  │  ├─ class_weights.json
│  │  │  │  ├─ config_snapshot.json
│  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  ├─ confusion_matrix.png
│  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  ├─ fine_tune_policy.json
│  │  │  │  ├─ history.csv
│  │  │  │  ├─ history.json
│  │  │  │  ├─ image_access_audit.json
│  │  │  │  ├─ metrics.json
│  │  │  │  ├─ model_summary.txt
│  │  │  │  ├─ run_metadata.json
│  │  │  │  └─ training_curves.png
│  │  │  ├─ R2_class_weight
│  │  │  │  ├─ augmentation.json
│  │  │  │  ├─ best_model.keras
│  │  │  │  ├─ classification_report.csv
│  │  │  │  ├─ class_weights.json
│  │  │  │  ├─ config_snapshot.json
│  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  ├─ confusion_matrix.png
│  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  ├─ fine_tune_policy.json
│  │  │  │  ├─ history.csv
│  │  │  │  ├─ history.json
│  │  │  │  ├─ image_access_audit.json
│  │  │  │  ├─ metrics.json
│  │  │  │  ├─ model_summary.txt
│  │  │  │  ├─ run_metadata.json
│  │  │  │  └─ training_curves.png
│  │  │  ├─ R3_augmentation
│  │  │  │  ├─ augmentation.json
│  │  │  │  ├─ best_model.keras
│  │  │  │  ├─ classification_report.csv
│  │  │  │  ├─ class_weights.json
│  │  │  │  ├─ config_snapshot.json
│  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  ├─ confusion_matrix.png
│  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  ├─ fine_tune_policy.json
│  │  │  │  ├─ history.csv
│  │  │  │  ├─ history.json
│  │  │  │  ├─ image_access_audit.json
│  │  │  │  ├─ metrics.json
│  │  │  │  ├─ model_summary.txt
│  │  │  │  ├─ run_metadata.json
│  │  │  │  └─ training_curves.png
│  │  │  ├─ README.md
│  │  │  ├─ run_experiment.py
│  │  │  ├─ smoke
│  │  │  │  └─ R3_augmentation
│  │  │  │     ├─ augmentation.json
│  │  │  │     ├─ best_model.keras
│  │  │  │     ├─ classification_report.csv
│  │  │  │     ├─ class_weights.json
│  │  │  │     ├─ config_snapshot.json
│  │  │  │     ├─ confusion_matrix.csv
│  │  │  │     ├─ confusion_matrix.png
│  │  │  │     ├─ confusion_matrix_normalized.csv
│  │  │  │     ├─ confusion_matrix_normalized.png
│  │  │  │     ├─ fine_tune_policy.json
│  │  │  │     ├─ history.csv
│  │  │  │     ├─ history.json
│  │  │  │     ├─ image_access_audit.json
│  │  │  │     ├─ metrics.json
│  │  │  │     ├─ model_summary.txt
│  │  │  │     ├─ run_metadata.json
│  │  │  │     └─ training_curves.png
│  │  │  ├─ source_state_before.json
│  │  │  ├─ source_state_verification.json
│  │  │  ├─ validate_d9.py
│  │  │  ├─ validation_result.json
│  │  │  └─ verify_source_state.py
│  │  ├─ eggplant_efficientnetb0_d8_lite
│  │  │  ├─ compare_results.py
│  │  │  ├─ comparison
│  │  │  │  ├─ comparison_summary.json
│  │  │  │  └─ model_preprocessing_comparison.csv
│  │  │  ├─ D8_LITE_REPORT.md
│  │  │  ├─ README.md
│  │  │  ├─ runs
│  │  │  │  ├─ P0
│  │  │  │  │  ├─ best_head.keras
│  │  │  │  │  ├─ best_model.keras
│  │  │  │  │  ├─ classification_report.csv
│  │  │  │  │  ├─ config_snapshot.json
│  │  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  │  ├─ confusion_matrix.png
│  │  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  │  ├─ history.csv
│  │  │  │  │  ├─ history.json
│  │  │  │  │  ├─ image_access_audit.json
│  │  │  │  │  ├─ metrics.json
│  │  │  │  │  ├─ model_summary.txt
│  │  │  │  │  ├─ run_metadata.json
│  │  │  │  │  └─ training_curves.png
│  │  │  │  └─ P3
│  │  │  │     ├─ best_head.keras
│  │  │  │     ├─ best_model.keras
│  │  │  │     ├─ classification_report.csv
│  │  │  │     ├─ config_snapshot.json
│  │  │  │     ├─ confusion_matrix.csv
│  │  │  │     ├─ confusion_matrix.png
│  │  │  │     ├─ confusion_matrix_normalized.csv
│  │  │  │     ├─ confusion_matrix_normalized.png
│  │  │  │     ├─ history.csv
│  │  │  │     ├─ history.json
│  │  │  │     ├─ image_access_audit.json
│  │  │  │     ├─ metrics.json
│  │  │  │     ├─ model_summary.txt
│  │  │  │     ├─ run_metadata.json
│  │  │  │     └─ training_curves.png
│  │  │  ├─ run_experiment.py
│  │  │  ├─ smoke
│  │  │  │  └─ P0
│  │  │  │     ├─ best_head.keras
│  │  │  │     ├─ best_model.keras
│  │  │  │     ├─ classification_report.csv
│  │  │  │     ├─ config_snapshot.json
│  │  │  │     ├─ confusion_matrix.csv
│  │  │  │     ├─ confusion_matrix.png
│  │  │  │     ├─ confusion_matrix_normalized.csv
│  │  │  │     ├─ confusion_matrix_normalized.png
│  │  │  │     ├─ history.csv
│  │  │  │     ├─ history.json
│  │  │  │     ├─ image_access_audit.json
│  │  │  │     ├─ metrics.json
│  │  │  │     ├─ model_summary.txt
│  │  │  │     ├─ run_metadata.json
│  │  │  │     └─ training_curves.png
│  │  │  ├─ source_state_before.json
│  │  │  ├─ source_state_verification.json
│  │  │  ├─ validate_experiment.py
│  │  │  ├─ validation_summary.json
│  │  │  └─ verify_source_state.py
│  │  ├─ eggplant_final
│  │  │  ├─ d10_access_audit.json
│  │  │  ├─ D10_REPORT.md
│  │  │  ├─ D10_SELECTION.md
│  │  │  ├─ d11
│  │  │  │  ├─ classification_report.csv
│  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  ├─ confusion_matrix.png
│  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  ├─ D11_FINAL_TEST_REPORT.md
│  │  │  │  ├─ evaluation_metadata.json
│  │  │  │  ├─ preflight.json
│  │  │  │  ├─ run_final_test.py
│  │  │  │  ├─ source_state_before.json
│  │  │  │  ├─ source_state_verification.json
│  │  │  │  ├─ test_metrics.json
│  │  │  │  ├─ test_open_event.json
│  │  │  │  ├─ test_predictions.csv
│  │  │  │  ├─ validate_d11.py
│  │  │  │  ├─ validation_result.json
│  │  │  │  └─ validation_vs_test.json
│  │  │  ├─ D11_TEST_PROTOCOL.md
│  │  │  ├─ final_lock_manifest.json
│  │  │  ├─ lock_configuration.py
│  │  │  ├─ model_verification.json
│  │  │  ├─ source_state_before.json
│  │  │  ├─ source_state_verification.json
│  │  │  ├─ validate_d10.py
│  │  │  ├─ validation_result.json
│  │  │  └─ verify_source_state.py
│  │  ├─ eggplant_mobilenetv2_d7
│  │  │  ├─ compare_results.py
│  │  │  ├─ comparison
│  │  │  │  ├─ comparison_summary.json
│  │  │  │  └─ preprocessing_comparison.csv
│  │  │  ├─ D7_REPORT.md
│  │  │  ├─ README.md
│  │  │  ├─ runs
│  │  │  │  ├─ P0
│  │  │  │  │  ├─ best_head.keras
│  │  │  │  │  ├─ best_model.keras
│  │  │  │  │  ├─ classification_report.csv
│  │  │  │  │  ├─ config_snapshot.json
│  │  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  │  ├─ confusion_matrix.png
│  │  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  │  ├─ history.csv
│  │  │  │  │  ├─ history.json
│  │  │  │  │  ├─ image_access_audit.json
│  │  │  │  │  ├─ metrics.json
│  │  │  │  │  ├─ model_summary.txt
│  │  │  │  │  ├─ run_metadata.json
│  │  │  │  │  └─ training_curves.png
│  │  │  │  ├─ P1
│  │  │  │  │  ├─ best_head.keras
│  │  │  │  │  ├─ best_model.keras
│  │  │  │  │  ├─ classification_report.csv
│  │  │  │  │  ├─ config_snapshot.json
│  │  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  │  ├─ confusion_matrix.png
│  │  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  │  ├─ history.csv
│  │  │  │  │  ├─ history.json
│  │  │  │  │  ├─ image_access_audit.json
│  │  │  │  │  ├─ metrics.json
│  │  │  │  │  ├─ model_summary.txt
│  │  │  │  │  ├─ run_metadata.json
│  │  │  │  │  └─ training_curves.png
│  │  │  │  ├─ P2
│  │  │  │  │  ├─ best_head.keras
│  │  │  │  │  ├─ best_model.keras
│  │  │  │  │  ├─ classification_report.csv
│  │  │  │  │  ├─ config_snapshot.json
│  │  │  │  │  ├─ confusion_matrix.csv
│  │  │  │  │  ├─ confusion_matrix.png
│  │  │  │  │  ├─ confusion_matrix_normalized.csv
│  │  │  │  │  ├─ confusion_matrix_normalized.png
│  │  │  │  │  ├─ history.csv
│  │  │  │  │  ├─ history.json
│  │  │  │  │  ├─ image_access_audit.json
│  │  │  │  │  ├─ metrics.json
│  │  │  │  │  ├─ model_summary.txt
│  │  │  │  │  ├─ run_metadata.json
│  │  │  │  │  └─ training_curves.png
│  │  │  │  └─ P3
│  │  │  │     ├─ best_head.keras
│  │  │  │     ├─ best_model.keras
│  │  │  │     ├─ classification_report.csv
│  │  │  │     ├─ config_snapshot.json
│  │  │  │     ├─ confusion_matrix.csv
│  │  │  │     ├─ confusion_matrix.png
│  │  │  │     ├─ confusion_matrix_normalized.csv
│  │  │  │     ├─ confusion_matrix_normalized.png
│  │  │  │     ├─ history.csv
│  │  │  │     ├─ history.json
│  │  │  │     ├─ image_access_audit.json
│  │  │  │     ├─ metrics.json
│  │  │  │     ├─ model_summary.txt
│  │  │  │     ├─ run_metadata.json
│  │  │  │     └─ training_curves.png
│  │  │  ├─ run_experiment.py
│  │  │  ├─ smoke
│  │  │  │  └─ P0
│  │  │  │     ├─ best_head.keras
│  │  │  │     ├─ best_model.keras
│  │  │  │     ├─ classification_report.csv
│  │  │  │     ├─ config_snapshot.json
│  │  │  │     ├─ confusion_matrix.csv
│  │  │  │     ├─ confusion_matrix.png
│  │  │  │     ├─ confusion_matrix_normalized.csv
│  │  │  │     ├─ confusion_matrix_normalized.png
│  │  │  │     ├─ history.csv
│  │  │  │     ├─ history.json
│  │  │  │     ├─ image_access_audit.json
│  │  │  │     ├─ metrics.json
│  │  │  │     ├─ model_summary.txt
│  │  │  │     ├─ run_metadata.json
│  │  │  │     └─ training_curves.png
│  │  │  ├─ source_state_before.json
│  │  │  ├─ source_state_verification.json
│  │  │  ├─ validate_experiment.py
│  │  │  ├─ validation_summary.json
│  │  │  └─ verify_source_state.py
│  │  └─ eggplant_preprocessing
│  │     ├─ generate_previews.py
│  │     ├─ preprocessing_manifest.csv
│  │     ├─ preprocessing_statistics.csv
│  │     ├─ preprocessing_summary.json
│  │     ├─ previews
│  │     │  ├─ healthy_comparison.jpg
│  │     │  ├─ leaf_spot_comparison.jpg
│  │     │  └─ mosaic_virus_comparison.jpg
│  │     ├─ README.md
│  │     ├─ validate_experiment.py
│  │     └─ visual_sanity_review.md
│  ├─ finalization
│  │  ├─ d10_lock.py
│  │  └─ __init__.py
│  ├─ preprocessing
│  │  ├─ eggplant.py
│  │  └─ __init__.py
│  ├─ requirements.txt
│  ├─ tests
│  │  ├─ test_d10_lock.py
│  │  ├─ test_d11_evaluation.py
│  │  ├─ test_d7_pipeline.py
│  │  ├─ test_d8_pipeline.py
│  │  ├─ test_d9_pipeline.py
│  │  ├─ test_preprocessing.py
│  │  └─ test_preview_selection.py
│  └─ training
│     ├─ d7_mobilenetv2.py
│     ├─ d8_efficientnetb0.py
│     ├─ d9_refinement.py
│     └─ __init__.py
├─ backend
│  ├─ app
│  │  ├─ api
│  │  │  ├─ routes
│  │  │  │  ├─ analyze.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  ├─ core
│  │  │  ├─ config.py
│  │  │  ├─ errors.py
│  │  │  └─ __init__.py
│  │  ├─ data
│  │  │  └─ diseases.json
│  │  ├─ main.py
│  │  ├─ schemas
│  │  │  ├─ analyze.py
│  │  │  └─ __init__.py
│  │  ├─ services
│  │  │  ├─ disease_catalog.py
│  │  │  ├─ eggplant_model_service.py
│  │  │  ├─ image_service.py
│  │  │  ├─ mock_ai_service.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ README.md
│  ├─ requirements.txt
│  └─ tests
│     ├─ test_api.py
│     ├─ test_eggplant_model_service.py
│     └─ __init__.py
├─ documents
└─ mobile_app
   ├─ .metadata
   ├─ analysis_options.yaml
   ├─ android
   │  ├─ .gradle
   │  │  ├─ 8.12
   │  │  │  ├─ checksums
   │  │  │  │  ├─ checksums.lock
   │  │  │  │  ├─ md5-checksums.bin
   │  │  │  │  └─ sha1-checksums.bin
   │  │  │  ├─ executionHistory
   │  │  │  │  ├─ executionHistory.bin
   │  │  │  │  └─ executionHistory.lock
   │  │  │  ├─ expanded
   │  │  │  ├─ fileChanges
   │  │  │  │  └─ last-build.bin
   │  │  │  ├─ fileHashes
   │  │  │  │  ├─ fileHashes.bin
   │  │  │  │  ├─ fileHashes.lock
   │  │  │  │  └─ resourceHashesCache.bin
   │  │  │  ├─ gc.properties
   │  │  │  └─ vcsMetadata
   │  │  ├─ buildOutputCleanup
   │  │  │  ├─ buildOutputCleanup.lock
   │  │  │  ├─ cache.properties
   │  │  │  └─ outputFiles.bin
   │  │  ├─ file-system.probe
   │  │  ├─ noVersion
   │  │  │  └─ buildLogic.lock
   │  │  └─ vcs-1
   │  │     └─ gc.properties
   │  ├─ .kotlin
   │  │  └─ sessions
   │  ├─ app
   │  │  ├─ build.gradle.kts
   │  │  └─ src
   │  │     ├─ debug
   │  │     │  └─ AndroidManifest.xml
   │  │     ├─ main
   │  │     │  ├─ AndroidManifest.xml
   │  │     │  ├─ java
   │  │     │  │  └─ io
   │  │     │  │     └─ flutter
   │  │     │  │        └─ plugins
   │  │     │  │           └─ GeneratedPluginRegistrant.java
   │  │     │  ├─ kotlin
   │  │     │  │  └─ com
   │  │     │  │     └─ phytoscan
   │  │     │  │        └─ mobile_app
   │  │     │  │           └─ MainActivity.kt
   │  │     │  └─ res
   │  │     │     ├─ drawable
   │  │     │     │  └─ launch_background.xml
   │  │     │     ├─ drawable-v21
   │  │     │     │  └─ launch_background.xml
   │  │     │     ├─ mipmap-hdpi
   │  │     │     │  └─ ic_launcher.png
   │  │     │     ├─ mipmap-mdpi
   │  │     │     │  └─ ic_launcher.png
   │  │     │     ├─ mipmap-xhdpi
   │  │     │     │  └─ ic_launcher.png
   │  │     │     ├─ mipmap-xxhdpi
   │  │     │     │  └─ ic_launcher.png
   │  │     │     ├─ mipmap-xxxhdpi
   │  │     │     │  └─ ic_launcher.png
   │  │     │     ├─ values
   │  │     │     │  └─ styles.xml
   │  │     │     └─ values-night
   │  │     │        └─ styles.xml
   │  │     └─ profile
   │  │        └─ AndroidManifest.xml
   │  ├─ build.gradle.kts
   │  ├─ gradle
   │  │  └─ wrapper
   │  │     ├─ gradle-wrapper.jar
   │  │     └─ gradle-wrapper.properties
   │  ├─ gradle.properties
   │  ├─ gradlew
   │  ├─ gradlew.bat
   │  ├─ local.properties
   │  └─ settings.gradle.kts
   ├─ ios
   │  ├─ Flutter
   │  │  ├─ AppFrameworkInfo.plist
   │  │  ├─ Debug.xcconfig
   │  │  ├─ ephemeral
   │  │  │  ├─ flutter_lldbinit
   │  │  │  └─ flutter_lldb_helper.py
   │  │  ├─ flutter_export_environment.sh
   │  │  ├─ Generated.xcconfig
   │  │  └─ Release.xcconfig
   │  ├─ Runner
   │  │  ├─ AppDelegate.swift
   │  │  ├─ Assets.xcassets
   │  │  │  ├─ AppIcon.appiconset
   │  │  │  │  ├─ Contents.json
   │  │  │  │  ├─ Icon-App-1024x1024@1x.png
   │  │  │  │  ├─ Icon-App-20x20@1x.png
   │  │  │  │  ├─ Icon-App-20x20@2x.png
   │  │  │  │  ├─ Icon-App-20x20@3x.png
   │  │  │  │  ├─ Icon-App-29x29@1x.png
   │  │  │  │  ├─ Icon-App-29x29@2x.png
   │  │  │  │  ├─ Icon-App-29x29@3x.png
   │  │  │  │  ├─ Icon-App-40x40@1x.png
   │  │  │  │  ├─ Icon-App-40x40@2x.png
   │  │  │  │  ├─ Icon-App-40x40@3x.png
   │  │  │  │  ├─ Icon-App-60x60@2x.png
   │  │  │  │  ├─ Icon-App-60x60@3x.png
   │  │  │  │  ├─ Icon-App-76x76@1x.png
   │  │  │  │  ├─ Icon-App-76x76@2x.png
   │  │  │  │  └─ Icon-App-83.5x83.5@2x.png
   │  │  │  └─ LaunchImage.imageset
   │  │  │     ├─ Contents.json
   │  │  │     ├─ LaunchImage.png
   │  │  │     ├─ LaunchImage@2x.png
   │  │  │     ├─ LaunchImage@3x.png
   │  │  │     └─ README.md
   │  │  ├─ Base.lproj
   │  │  │  ├─ LaunchScreen.storyboard
   │  │  │  └─ Main.storyboard
   │  │  ├─ GeneratedPluginRegistrant.h
   │  │  ├─ GeneratedPluginRegistrant.m
   │  │  ├─ Info.plist
   │  │  └─ Runner-Bridging-Header.h
   │  ├─ Runner.xcodeproj
   │  │  ├─ project.pbxproj
   │  │  ├─ project.xcworkspace
   │  │  │  ├─ contents.xcworkspacedata
   │  │  │  └─ xcshareddata
   │  │  │     ├─ IDEWorkspaceChecks.plist
   │  │  │     └─ WorkspaceSettings.xcsettings
   │  │  └─ xcshareddata
   │  │     └─ xcschemes
   │  │        └─ Runner.xcscheme
   │  ├─ Runner.xcworkspace
   │  │  ├─ contents.xcworkspacedata
   │  │  └─ xcshareddata
   │  │     ├─ IDEWorkspaceChecks.plist
   │  │     └─ WorkspaceSettings.xcsettings
   │  └─ RunnerTests
   │     └─ RunnerTests.swift
   ├─ lib
   │  └─ main.dart
   ├─ linux
   │  ├─ CMakeLists.txt
   │  ├─ flutter
   │  │  ├─ CMakeLists.txt
   │  │  ├─ ephemeral
   │  │  │  └─ .plugin_symlinks
   │  │  ├─ generated_plugins.cmake
   │  │  ├─ generated_plugin_registrant.cc
   │  │  └─ generated_plugin_registrant.h
   │  └─ runner
   │     ├─ CMakeLists.txt
   │     ├─ main.cc
   │     ├─ my_application.cc
   │     └─ my_application.h
   ├─ macos
   │  ├─ Flutter
   │  │  ├─ ephemeral
   │  │  │  ├─ Flutter-Generated.xcconfig
   │  │  │  ├─ flutter_export_environment.sh
   │  │  │  └─ Packages
   │  │  │     └─ FlutterGeneratedPluginSwiftPackage
   │  │  │        ├─ Package.swift
   │  │  │        └─ Sources
   │  │  │           └─ FlutterGeneratedPluginSwiftPackage
   │  │  │              └─ FlutterGeneratedPluginSwiftPackage.swift
   │  │  ├─ Flutter-Debug.xcconfig
   │  │  ├─ Flutter-Release.xcconfig
   │  │  └─ GeneratedPluginRegistrant.swift
   │  ├─ Runner
   │  │  ├─ AppDelegate.swift
   │  │  ├─ Assets.xcassets
   │  │  │  └─ AppIcon.appiconset
   │  │  │     ├─ app_icon_1024.png
   │  │  │     ├─ app_icon_128.png
   │  │  │     ├─ app_icon_16.png
   │  │  │     ├─ app_icon_256.png
   │  │  │     ├─ app_icon_32.png
   │  │  │     ├─ app_icon_512.png
   │  │  │     ├─ app_icon_64.png
   │  │  │     └─ Contents.json
   │  │  ├─ Base.lproj
   │  │  │  └─ MainMenu.xib
   │  │  ├─ Configs
   │  │  │  ├─ AppInfo.xcconfig
   │  │  │  ├─ Debug.xcconfig
   │  │  │  ├─ Release.xcconfig
   │  │  │  └─ Warnings.xcconfig
   │  │  ├─ DebugProfile.entitlements
   │  │  ├─ Info.plist
   │  │  ├─ MainFlutterWindow.swift
   │  │  └─ Release.entitlements
   │  ├─ Runner.xcodeproj
   │  │  ├─ project.pbxproj
   │  │  ├─ project.xcworkspace
   │  │  │  └─ xcshareddata
   │  │  │     └─ IDEWorkspaceChecks.plist
   │  │  └─ xcshareddata
   │  │     └─ xcschemes
   │  │        └─ Runner.xcscheme
   │  ├─ Runner.xcworkspace
   │  │  ├─ contents.xcworkspacedata
   │  │  └─ xcshareddata
   │  │     └─ IDEWorkspaceChecks.plist
   │  └─ RunnerTests
   │     └─ RunnerTests.swift
   ├─ pubspec.yaml
   ├─ README.md
   ├─ test
   │  └─ widget_test.dart
   ├─ web
   │  ├─ favicon.png
   │  ├─ icons
   │  │  ├─ Icon-192.png
   │  │  ├─ Icon-512.png
   │  │  ├─ Icon-maskable-192.png
   │  │  └─ Icon-maskable-512.png
   │  ├─ index.html
   │  └─ manifest.json
   └─ windows
      ├─ CMakeLists.txt
      ├─ flutter
      │  ├─ CMakeLists.txt
      │  ├─ ephemeral
      │  │  └─ .plugin_symlinks
      │  ├─ generated_plugins.cmake
      │  ├─ generated_plugin_registrant.cc
      │  └─ generated_plugin_registrant.h
      └─ runner
         ├─ CMakeLists.txt
         ├─ flutter_window.cpp
         ├─ flutter_window.h
         ├─ main.cpp
         ├─ resource.h
         ├─ resources
         │  └─ app_icon.ico
         ├─ runner.exe.manifest
         ├─ Runner.rc
         ├─ utils.cpp
         ├─ utils.h
         ├─ win32_window.cpp
         └─ win32_window.h

```