# PhytoScan Final Full System Test — 2026-10-27

## Final decision

**READY WITH LIMITATIONS**

Integration หลัก Flutter → FastAPI → Plant Classifier → Disease Router → Disease Classifier → Result Screen ผ่านบน Android Emulator กับ Backend/โมเดลจริง และไม่พบ Critical Bug ค้างอยู่ แต่ยังไม่ถือว่า production-verified เพราะ Web flow แบบ interactive และ Physical Android Device ยังไม่ได้ยืนยันครบ

## Scope and invariants

- Branch: `feature/plant-router-phase1`
- HEAD ตอนเริ่มตรวจ: `7107d736ceb3b9e5e53805b6d1efda333f9086be`
- ไม่ commit หรือ push
- ไม่แก้ model weights, dataset, labels, threshold หรือ frozen evaluation config
- Threshold runtime ยังคง `MIN_CONFIDENCE=0.0`, `MIN_MARGIN=0.6936511993408203`
- Frozen config SHA-256 ยังคง `96ebd02a1ed29d7f78d439903c5cd439260aee9a3bae3dfefe60a2ac240446c7`
- ไม่มีการใช้ผล Test เพื่อปรับ threshold
- ไม่มีการอ้างว่า threshold ตรวจจับ Unsupported/OOD plants ได้

## Test summary

| Area | Status | Fresh evidence from this run |
|---|---|---|
| Repository/environment audit | PASS | ตรวจ dirty worktree, runtime, dependencies, API URL rules และ `git diff --check` |
| 7 model artifacts | PASS | ไฟล์ครบ, SHA-256 ตรง manifest, load และ inference ได้จริงทุกตัว |
| Frozen config/receipt integrity | PASS | config hash และ corrective report/prediction hashes ตรง receipt |
| Backend automated suite | PASS | `64 passed in 27.15s` |
| Live API contracts | PASS | `/health`, `/plants`, automatic/manual analyze, multi-image, mixed-image และ error contracts |
| Flutter analyze | PASS | `No issues found` |
| Flutter unit/widget suite | PASS | `23 passed, 1 conditional integration skipped` |
| Flutter real-backend conditional test | PASS | `1 passed` เมื่อเปิด `RUN_BACKEND_INTEGRATION=true` |
| Android Emulator E2E | PASS | automatic, manual selection, low-margin confirmation/resubmit, timeout/retry |
| Android debug APK | PASS | build สำเร็จ |
| Flutter Web build | PASS | debug Web build สำเร็จ |
| Chrome interactive E2E | BLOCKED | เปิดแอปจริงได้ แต่ automation ไม่สามารถ activate Flutter Canvas/Semantics button ได้อย่างเชื่อถือได้ จึงไม่อ้างว่า Web E2E ผ่าน |
| Physical Android Device | NOT TESTED | ไม่มี physical device เชื่อมต่อ |

## Repository, models and frozen artifacts

- Runtime: Python `3.12.4`, TensorFlow `2.21.0`, Flutter `3.32.8`, Dart `3.8.1`, Android Emulator API 35
- Model bundle มี 7 ตัว: Plant Classifier 1 ตัวและ Disease Classifier 6 ตัว
- `verify_model_bundle.py` รายงาน `all_models_ready=true`
- Model files ถูก ignore ด้วย `*.keras`; Flutter build output ถูก ignore ด้วย `/build/`
- Input contract ตรง manifest: TensorFlow RGB decode → bilinear resize `224×224` → `float32` → pixel range `[0,255]` → no external normalization
- Plant class order: `chrysanthemum, marigold, money_plant, rose, snake_plant, spider_plant`
- Sunflower ไม่อยู่ใน active backend registry, API plant list หรือ Flutter UI แล้ว; ที่ค้นพบภายหลังมีเฉพาะ negative regression assertions/tests

Model SHA-256 ที่ตรวจตรง manifest:

| Model | SHA-256 |
|---|---|
| Plant classifier | `5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165` |
| Chrysanthemum | `61ee3c4cadb109c7d61d0e6e8e8b4a97d2522fcd79d06be9cd839d61407ea470` |
| Marigold | `68b4ea44f8a6abdfc74f5e46b6aa6432857d4aac89e5c55f0afa61b2aee68635` |
| Money plant | `2f8ebf9021548ee4ec4562241e79b6ba4139100c7e1c481bf10e22ece6e63dae` |
| Rose | `e284c7c693f612a31d3620526d59eff680d026d78dffebef67e22f18a2488c04` |
| Snake plant | `aec49000cc31fa5106d9358a603b5a47e263c4caebfa428a39c8f820274f1e41` |
| Spider plant | `6b80c7a02ae979b94b7854cdb2e54ff0f1688e6633f4192d01cb7e7a6850999a` |

Corrective evaluation ที่มีอยู่และไม่ได้รันใหม่หรือปรับค่า:

| Split | Total | Coverage | Accepted accuracy | Accepted errors | FAR among incorrect | Correct rejections | Wrongful rejections |
|---|---:|---:|---:|---:|---:|---:|---:|
| Validation | 2,340 | 2,311/2,340 = 98.7607% | 2,311/2,311 = 100% | 0 | 0/7 = 0% | 7/7 | 22/2,333 |
| Corrective Test | 1,580 | 1,556/1,580 = 98.4810% | 1,555/1,556 = 99.9357% | 1 | 1/7 = 14.2857% | 6/7 | 18/1,573 |

Validation มี incorrect predictions เพียง 7 ภาพ จึงไม่รับประกัน zero-error ในงานจริง และไม่มี Unsupported/OOD dataset

## Backend and live API

Automated suite: `64 passed in 27.15s` รวม regression ที่ load/infer ผ่านไฟล์โมเดลจริงทั้ง 7 ตัว

Live FastAPI results:

- `GET /api/v1/plants`: HTTP 200, 6 plants, ไม่มี Sunflower
- Automatic single image: HTTP 200 `completed`; plant `chrysanthemum` 87.8%, disease `Septoria` 77.3%
- Manual `plant_code=rose`: HTTP 200 `completed`; UI แสดงว่า user-confirmed และไม่ใช้ plant `confidence=1.0` เป็น AI confidence
- Known low-margin validation image: `manual_confirmation_required`, predicted rose 64.0%, margin 29.1%; disease classifier ไม่ถูกเรียกก่อนยืนยัน
- Same-image batch 2 ภาพ: `completed`, `image_results.index` เป็น `0,1`
- Mixed supported plants: `manual_confirmation_required`, reason `inconsistent_plant`, ไม่มี disease result
- Unsupported plant: HTTP 400 `UNSUPPORTED_PLANT`
- Missing images: HTTP 400 `NO_IMAGES`
- Four images: HTTP 400 `TOO_MANY_IMAGES`
- Fake JPEG: HTTP 400 `INVALID_IMAGE`
- Oversized image: HTTP 413 `FILE_TOO_LARGE`
- Text upload: HTTP 415 `UNSUPPORTED_FILE_TYPE`
- HTTP 500/503 paths ตรวจด้วย isolated monkeypatched service failures ใน automated tests เพื่อไม่ทำลาย runtime จริง
- Disease metadata ที่ไม่มีข้อมูลยังเป็น empty lists; ไม่ได้สร้างข้อมูลโรคเพิ่ม

## Android Emulator E2E

Device: `emulator-5554`, Android 15/API 35, x86_64; Backend จริงที่ `10.0.2.2:8000`

- PASS — Automatic detection → disease result: 940 ms, app RSS 314,126,336 → 320,000,000 bytes
- PASS — Manual plant selection → disease result: 1,372 ms, app RSS 356,995,072 → 371,707,904 bytes
- PASS — Low-margin automatic request → manual confirmation: 802 ms
- PASS — Confirm rose → resubmit same image → disease result: 576 ms; app RSS 326,512,640 → 350,257,152 bytes
- PASS — Result distinguishes plant confidence from disease confidence. After confirmation it says `ชนิดพืชนี้ได้รับการยืนยันโดยผู้ใช้`; the displayed 100.0% belongs to the disease result
- PASS — Timeout twice against an unreachable endpoint: 3,054 ms and 3,003 ms; image remained selected and retry remained available
- PASS — No crash or navigation error observed in tested flows
- PASS at live API / automated UI level — same-plant and mixed-plant batches, index order, invalid image handling
- NOT TESTED through Android photo picker — invalid non-image selection (system picker filters it) and a complete 2-image picker interaction; corresponding client/backend behavior passed automated/live API tests

Evidence is under `mobile_app/build/`, including:

- `fulltest-android-auto-result.png`
- `fulltest-android-manual-result.png`
- `fulltest-android-manual-confirmation.png`
- `fulltest-android-confirmed-result.png`
- `fulltest-android-timeout-fixed.png`
- matching UI hierarchy XML files

## Performance and stability

Backend process-tree measurements on Windows CPU runtime:

- Startup to healthy: 9.723 s
- Cold automatic inference: 4.312 s
- Warm automatic inference: 0.605 s
- 10 sequential warm requests: 10/10 HTTP 200, min 0.496 s, mean 0.517 s, p95 0.541 s, max 0.541 s
- Working set: 252.09 MB before inference, 452.14 MB after cold, 443.49 MB after warm
- After other route/model loads: 623.03 MB before sequential run → 629.93 MB after
- No high-volume stress test was run
- Debug emulator showed first-render skipped-frame warnings; release/profile performance and physical-device jank remain unverified

## Builds

- Android debug APK: `mobile_app/build/app/outputs/flutter-apk/app-debug.apk`
  - size: 115,763,949 bytes
  - SHA-256: `C35952E5F345AB4D7D199D8517EF2CBA0D4ACC61E1C86509F4BF380C47D2C2E7`
- Web debug build: `mobile_app/build/web/`
  - `main.dart.js` SHA-256: `832CC172A77B4B10F4DB651C77636CE9577F3AAC3E8FFA011BC2AD36322B35CC`

Web build success is not counted as Web E2E success. Chrome loaded the real Flutter page at `localhost:8080` and its initial semantics without console/network errors, but the available DevTools automation could not reliably activate the Flutter-rendered submit control. A `flutter test -d chrome` alternative is unsuitable for real HTTP E2E because `TestWidgetsFlutterBinding` intercepts HTTP. Interactive Chrome automatic/manual/upload/result flows therefore remain **BLOCKED**, not PASS.

## Bugs fixed and regression coverage

1. Stale `Rose และ Sunflower` text remained in Profile although Sunflower was removed from active registry. Changed to `รองรับพืช 6 ชนิด` and added a widget regression.
2. Timeout/network error text was below scroll content and was not immediately visible on the emulator. Moved the existing error component above the fixed submit button and added a regression checking visible error plus preserved-image retry behavior.
3. Added real model runtime smoke coverage that loads and infers Plant Classifier plus all six Disease Classifiers and validates class mapping/load count.
4. Made the device test harness avoid unsupported `ProcessInfo.currentRss` access on Web and accept a test-only asset path; production UI/API contract was not changed by this harness update.

Files changed specifically by this final-test pass:

- `backend/tests/test_runtime_smoke.py`
- `mobile_app/lib/screens/analyze_screen.dart`
- `mobile_app/lib/screens/profile_screen.dart`
- `mobile_app/test/screens/analyze_flow_test.dart`
- `mobile_app/test/widget_test.dart`
- `mobile_app/tool/phase2_3_device_harness.dart`
- this report

Audit note: running `verify_model_bundle.py` without `--check-only` unintentionally regenerated the existing untracked `backend/evaluation/model_bundle_verification.json` and `.md` receipts with a new timestamp. No model, threshold, dataset, corrective evaluation config, validation/test report, or prediction file was changed. Because the prior receipts were untracked, their old local content could not be restored; this must be reviewed before staging.

## Physical device checklist

Physical device: **NOT TESTED** — no device was connected.

Before production or external pilot:

1. Install the final APK on at least one physical Android device.
2. Configure a reachable HTTPS or LAN API URL; do not use emulator-only `10.0.2.2`.
3. Test camera permission/capture and gallery selection for 1, 2 and 3 images.
4. Test automatic, manual selection, low-confidence confirmation and mixed-plant correction.
5. Test airplane mode, timeout, reconnect and retry while confirming selected images persist.
6. Test rotation, app background/foreground, memory pressure and repeated analyses.
7. Record device model, Android version, latency, memory, screenshots and crash logs.
8. Keep new phone photos clearly separated from the frozen Validation/Test evaluation; do not tune threshold from them without a new approved protocol.

## Navigation handoff for UI/UX redesign

Current principal flow:

`Splash → Login/Guest → Home → Automatic Analyze → [Manual Confirmation when required] → Result → Disease Detail`

Alternative manual flow:

`Home/Plants → Plant Selection → Analyze with selected plant → Result → Disease Detail`

Primary screens to preserve behavior for:

- Splash and Login
- Home dashboard and bottom navigation
- Plant list/selection
- Analyze/image picker/loading/error states
- Manual plant confirmation and inconsistent-image correction
- Per-image Result list and overall summary
- Disease detail
- Profile

## Git and handoff

The worktree already contains accumulated uncommitted Phase 1/1.2/2.2/2.3 changes. No commit or push was performed. Before committing, review/stage by phase, exclude `mobile_app/build/`, `.keras`, local logs/screenshots and the regenerated model-bundle receipts unless intentionally retained. UI/UX redesign can start on a separate branch after this integration state is reviewed, while keeping the remaining Web interactive and physical-device checks visible as limitations.
