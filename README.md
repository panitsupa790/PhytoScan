# PhytoScan

PhytoScan คือแอป Flutter สำหรับวิเคราะห์ภาพใบพืช โดยส่งภาพไปประมวลผลที่ FastAPI Backend ด้วยโมเดล TensorFlow/Keras แบบสองขั้นตอน:

1. จำแนกชนิดพืชจาก 6 ชนิดที่รองรับ
2. เลือกโมเดลเฉพาะพืชเพื่อจำแนกโรค อาการผิดปกติ หรือใบสุขภาพดี

ระบบรองรับการถ่ายภาพ/เลือกภาพ 1–3 ภาพ, การยืนยันชนิดพืชเมื่อผลไม่ชัดเจน, ประวัติการสแกน และคลังข้อมูลพืชภาษาไทย

> **ขอบเขตการใช้งาน:** Plant Classifier ออกแบบและประเมินสำหรับภาพใบพืชบนพื้นหลังเรียบหรือควบคุมได้ ผลที่แสดงเป็นการวิเคราะห์เบื้องต้นจากภาพ ไม่ใช่การยืนยันโรคหรือเชื้อสาเหตุทางห้องปฏิบัติการ และยังไม่มีหลักฐานว่าระบบสามารถปฏิเสธพืชนอก 6 ชนิดได้อย่างน่าเชื่อถือ

## คุณสมบัติหลัก

- จำแนกพืช 6 ชนิดและผลโรค/อาการรวม 23 คลาส
- รับภาพ JPG, JPEG หรือ PNG ครั้งละ 1–3 ภาพ
- จำกัดขนาดเริ่มต้นไม่เกิน 10 MB ต่อภาพ
- Automatic Plant Classification พร้อมเกณฑ์ confidence/margin
- Manual Confirmation และ Manual Plant Selection
- วิเคราะห์หลายภาพและแสดงผลรายภาพ
- แสดงอาการ วิธีดูแล และการป้องกันจาก metadata ที่ตรวจสอบไว้
- เก็บประวัติใน SQLite และสำรองรายการล่าสุดในอุปกรณ์ด้วย SharedPreferences
- คลังพืชและข้อมูลการดูแลเบื้องต้น
- ตรวจ SHA-256, class mapping, input contract และ threshold receipt ก่อนเปิด automatic routing

## พืชที่รองรับ

| พืช | Plant code | จำนวนผลโรค/อาการ |
|---|---|---:|
| เบญจมาศ | `chrysanthemum` | 3 |
| ดาวเรือง | `marigold` | 3 |
| พลูด่าง | `money_plant` | 3 |
| กุหลาบ | `rose` | 8 |
| ลิ้นมังกร | `snake_plant` | 3 |
| เศรษฐีเรือนใน | `spider_plant` | 3 |

ชื่อโรค อาการ การดูแล และการป้องกันอยู่ใน [`backend/app/data/diseases.json`](backend/app/data/diseases.json) ส่วนลำดับคลาสของโมเดลกำหนดใน [`backend/app/data/model_manifest.json`](backend/app/data/model_manifest.json) และห้ามเปลี่ยนลำดับโดยไม่เปลี่ยนโมเดลให้ตรงกัน

## สถาปัตยกรรมระบบ

```text
Android / Flutter App
  ├─ Camera / Gallery
  ├─ ตรวจจำนวน นามสกุล และขนาดไฟล์เบื้องต้น
  ├─ Scan / Confirmation / Result / History / Plant Library
  └─ Multipart HTTP + X-Device-ID
                 │
                 ▼
FastAPI Backend
  ├─ ตรวจ MIME, extension, ขนาด และเนื้อไฟล์จริง
  ├─ Plant Classifier Service
  ├─ Threshold Decision + Manual Confirmation Gate
  ├─ Disease Model Router
  ├─ Disease / Plant Metadata
  └─ SQLite History
                 │
                 ▼
TensorFlow / Keras Models
  ├─ Plant Classifier 1 โมเดล → 6 classes
  └─ Disease Classifier 6 โมเดล → รวม 23 classes
```

### Workflow การวิเคราะห์

```text
เลือกภาพ 1–3 ภาพ
→ Flutter ตรวจไฟล์เบื้องต้น
→ POST /api/v1/analyze
→ Backend ตรวจไฟล์อีกครั้ง
→ RGB float32 [0,255] + resize 224×224
→ Plant Classifier คืน probability 6 คลาส
→ confidence = probability อันดับหนึ่ง
→ margin = probability อันดับหนึ่ง − อันดับสอง
→ ทุกภาพผ่าน threshold และเป็นพืชชนิดเดียวกันหรือไม่?
   ├─ Yes → เลือก Disease Classifier ของพืชนั้น
   └─ No  → manual_confirmation_required
             → ผู้ใช้ยืนยัน/แก้ชนิดพืช
             → ส่งภาพเดิมพร้อม plant_code
             → เลือก Disease Classifier ตามชนิดที่ยืนยัน
→ วิเคราะห์โรค/อาการรายภาพ
→ ดึง metadata ภาษาไทย
→ แสดงผลและบันทึกประวัติแบบ best-effort
```

Backend จะไม่เรียก Disease Classifier ใน automatic flow จนกว่า Plant Classifier จะผ่าน routing gate หากหลายภาพถูกจำแนกเป็นคนละพืช ระบบจะส่งสถานะ `inconsistent_plant` เพื่อให้ผู้ใช้แยกชุดภาพ

## โครงสร้าง Repository

```text
phytoscan/
├─ mobile_app/                 Flutter application
│  ├─ lib/models/              โมเดลข้อมูลฝั่งแอป
│  ├─ lib/screens/             หน้าจอหลัก
│  ├─ lib/services/            API, device identity และ history sync
│  ├─ lib/theme/               Design tokens และ theme
│  ├─ lib/widgets/             Shared UI components
│  └─ test/                    Flutter tests
├─ backend/                    FastAPI application
│  ├─ app/api/routes/          Analyze, history และ plant library endpoints
│  ├─ app/core/                Runtime settings และ error contract
│  ├─ app/data/                Manifest, thresholds และ metadata
│  ├─ app/db/                  SQLite migrations/repositories/seed
│  ├─ app/models/              Runtime .keras files (ไม่เก็บใน Git)
│  ├─ app/services/            Validation, inference และ routing
│  ├─ evaluation/              Evaluation reports และ receipts
│  ├─ scripts/                 Verification/evaluation utilities
│  └─ tests/                   Backend tests
├─ ai_model/                   Training pipelines และ research artifacts
├─ dataset/                    Dataset scripts, manifests และ placeholders
├─ documents/                  เอกสารประกอบโครงการ
└─ PHYTOSCAN_PRESENTATION_HANDOVER.md
```

## สิ่งที่ต้องติดตั้ง

### Backend

- Windows 10/11
- Python 3.12
- RAM เพียงพอสำหรับโหลด TensorFlow และโมเดล 2 ตัวต่อคำขอ
- โมเดล `.keras` ทั้ง 7 ไฟล์ตาม Runtime Model Bundle

### Mobile

- Flutter 3.32.x หรือเวอร์ชันที่รองรับ Dart `^3.8.1`
- Android Studio และ Android SDK
- Android Emulator หรืออุปกรณ์ Android ที่เปิด Developer Mode

ตรวจสอบเครื่องมือ:

```powershell
python --version
flutter --version
flutter doctor
```

## 1. เตรียม Runtime Model Bundle

ไฟล์โมเดลไม่ถูกเก็บใน Git เพื่อหลีกเลี่ยง binary ขนาดใหญ่ ให้นำไฟล์ต่อไปนี้วางใน `backend/app/models/`:

```text
backend/app/models/
├─ plant-classifier-v1.keras
├─ chrysanthemum-v1.keras
├─ marigold-v1.keras
├─ money-plant-v1.keras
├─ rose-v1.keras
├─ snake-plant-v1.keras
└─ spider-plant-v1.keras
```

ชื่อไฟล์, SHA-256, input shape, preprocessing และ class order ต้องตรงกับ [`backend/app/data/model_manifest.json`](backend/app/data/model_manifest.json) ทุกค่า ระบบจะปฏิเสธการโหลดเมื่อ checksum หรือ contract ไม่ตรงกัน

## 2. ตั้งค่าและรัน Backend

เปิด PowerShell ที่ root ของโปรเจกต์:

```powershell
cd C:\phytoscan\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

ไฟล์ `backend/.env` เป็นค่าของเครื่องผู้พัฒนาและถูก ignore จาก Git ค่าเริ่มต้นที่สำคัญ:

```dotenv
MAX_IMAGES=3
MAX_IMAGE_SIZE_BYTES=10485760
MODEL_MANIFEST=app/data/model_manifest.json
PLANT_THRESHOLD_CONFIG=app/data/plant_classifier_evaluation_corrective.json
PLANT_THRESHOLD_RECEIPT=app/data/plant_classifier_corrective_test_receipt.json
PLANT_THRESHOLD_REQUIRE_TEST_RECEIPT=true
DATABASE_PATH=data/phytoscan.db
```

รัน Backend โดยระบุ `--env-file` เสมอ เพราะ `config.py` ไม่โหลด `.env` เอง:

```powershell
python -m uvicorn app.main:app --env-file .env --host 0.0.0.0 --port 8000 --reload
```

เมื่อ Backend เริ่มทำงาน ระบบจะสร้าง/อัปเกรด SQLite schema และ seed reference data อัตโนมัติ

ตรวจสอบสถานะ:

```powershell
curl.exe http://127.0.0.1:8000/health
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- SQLite เริ่มต้น: `backend/data/phytoscan.db`

## 3. รัน Flutter บน Android Emulator

Android Emulator เข้าถึง localhost ของ Windows ผ่าน `10.0.2.2` ซึ่งเป็นค่าเริ่มต้นของแอปอยู่แล้ว:

```powershell
cd C:\phytoscan\mobile_app
flutter pub get
flutter run
```

Backend ต้องเปิดอยู่ที่ port `8000` ก่อนเริ่มสแกน

## 4. รันบนมือถือ Android จริง

1. เชื่อมคอมพิวเตอร์และมือถือเข้ากับ Wi-Fi เครือข่ายเดียวกัน
2. รัน Backend ด้วย `--host 0.0.0.0`
3. ตรวจ IPv4 ของคอมพิวเตอร์ด้วย `ipconfig`
4. อนุญาต port 8000 ผ่าน Windows Firewall เฉพาะเครือข่ายที่เชื่อถือได้
5. ส่ง API URL ตอน build/run ด้วย `--dart-define`

ตัวอย่างเมื่อ IP ของคอมพิวเตอร์คือ `192.168.1.50`:

```powershell
cd C:\phytoscan\mobile_app
flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000
```

ทดสอบ URL `http://192.168.1.50:8000/health` จาก browser บนมือถือก่อน หากเปิดไม่ได้ แอปก็จะเชื่อม Backend ไม่ได้เช่นกัน

## 5. สร้าง APK

### APK สำหรับ Android Emulator

```powershell
cd C:\phytoscan\mobile_app
flutter build apk --release
```

### APK สำหรับมือถือจริง

```powershell
flutter build apk --release `
  --dart-define=API_BASE_URL=http://192.168.1.50:8000
```

ไฟล์ที่ได้:

```text
mobile_app/build/app/outputs/flutter-apk/app-release.apk
```

ติดตั้งด้วย ADB:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r `
  "C:\phytoscan\mobile_app\build\app\outputs\flutter-apk\app-release.apk"
```

> Release configuration ปัจจุบันยังลงนามด้วย debug key เพื่อใช้ทดสอบภายใน หากต้องเผยแพร่ผ่าน Play Store ต้องสร้าง release keystore, แยก secret ออกจาก repository และตั้งค่า signing ใหม่ก่อน

## API หลัก

| Method | Endpoint | หน้าที่ |
|---|---|---|
| `GET` | `/health` | ตรวจสถานะ API |
| `GET` | `/api/v1/plants` | รายการพืชที่รองรับ |
| `POST` | `/api/v1/analyze` | วิเคราะห์ภาพแบบ automatic หรือ manual |
| `GET` | `/api/v1/history` | อ่านประวัติของอุปกรณ์ |
| `GET` | `/api/v1/history/{scan_id}` | อ่านรายละเอียดประวัติ |
| `DELETE` | `/api/v1/history/{scan_id}` | ลบประวัติรายการเดียว |
| `DELETE` | `/api/v1/history` | ล้างประวัติของอุปกรณ์ |
| `GET` | `/api/v1/plant-library` | รายการคลังพืช |
| `GET` | `/api/v1/plant-library/{plant_code}` | รายละเอียดพืช |

ตัวอย่าง Automatic Analysis:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyze" `
  -H "X-Device-ID: local-readme-test" `
  -F "images=@C:\path\to\leaf.jpg"
```

ตัวอย่าง Manual Plant Selection/Confirmation:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyze" `
  -H "X-Device-ID: local-readme-test" `
  -F "plant_code=rose" `
  -F "images=@C:\path\to\rose-leaf.jpg"
```

## Runtime Profiles

### Default profile

- Plant Classifier: EfficientNet-B0 V1
- Disease Classifier: EfficientNet-B0 ทั้ง 6 ชนิด
- Manifest: `backend/app/data/model_manifest.json`
- Threshold: `backend/app/data/plant_classifier_evaluation_corrective.json`
- เป็น profile เริ่มต้นของระบบ

### Hybrid candidate

- Plant Classifier: MobileNetV2
- Disease Classifier: MobileNetV2 จำนวน 5 ชนิด และ EfficientNet-B0 สำหรับดาวเรือง
- Manifest: `backend/app/data/model_manifest.hybrid_candidate.json`
- Threshold: `backend/app/data/plant_classifier_threshold.hybrid_candidate.json`
- เป็น candidate สำหรับสภาพแวดล้อมทดสอบภายใน ไม่ใช่ active profile เริ่มต้น

ห้ามเปลี่ยน manifest เพียงไฟล์เดียว ต้องใช้ model bundle, threshold config และ receipt ที่เป็นชุดเดียวกัน มิฉะนั้น runtime verification จะ fail-closed

## Database และประวัติ

Backend ใช้ SQLite โดย migrations อยู่ที่ `backend/app/db/migrations/` และ seed ข้อมูลจากไฟล์ JSON ใน `backend/app/data/`

ข้อมูลประวัติประกอบด้วยข้อมูลไฟล์, SHA-256, ผลจำแนกพืช, probability candidates, confidence/margin ภายใน, ผลโรค และ metadata snapshot โดย schema ปัจจุบันไม่เก็บ image bytes ต้นฉบับ

Flutter ใช้ `X-Device-ID` เพื่ออ่าน/ลบประวัติของอุปกรณ์ และเก็บ cache สูงสุด 100 รายการใน SharedPreferences เพื่อรองรับการเปิดดูเมื่อ Backend ติดต่อไม่ได้

รายละเอียดฐานข้อมูล: [`backend/DATABASE.md`](backend/DATABASE.md)

## ทดสอบระบบ

### Backend

```powershell
cd C:\phytoscan\backend
.\.venv\Scripts\python.exe -m pytest
```

### Flutter

```powershell
cd C:\phytoscan\mobile_app
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
```

Integration test ที่เรียก Backend จริงต้องเปิด Backend ก่อนและตั้ง environment ตามคำอธิบายใน `mobile_app/test/backend_contract_integration_test.dart`

## แก้ปัญหาเบื้องต้น

### `MODEL_UNAVAILABLE` หรือ Backend คืน 503

- ตรวจว่าไฟล์ `.keras` ครบ 7 ไฟล์
- ตรวจชื่อไฟล์และตำแหน่งตาม manifest
- ตรวจ SHA-256 ด้วย `Get-FileHash -Algorithm SHA256`
- ตรวจว่า threshold config และ receipt เป็นชุดเดียวกับ manifest

### Emulator ติดต่อ Backend ไม่ได้

- ตรวจว่า Backend ทำงานที่ port 8000
- ใช้ `http://10.0.2.2:8000` ไม่ใช่ `localhost` ภายใน Emulator
- ตรวจ `http://127.0.0.1:8000/health` จาก Windows ก่อน

### มือถือจริงติดต่อ Backend ไม่ได้

- ห้ามใช้ `10.0.2.2` บนมือถือจริง
- Build ด้วย `API_BASE_URL` ที่เป็น LAN IP ของคอมพิวเตอร์
- ตรวจว่าอุปกรณ์อยู่เครือข่ายเดียวกันและ Firewall อนุญาต port 8000

### PowerShell หา `adb` ไม่พบ

```powershell
$env:Path += ";$env:LOCALAPPDATA\Android\Sdk\platform-tools"
adb devices
```

### แก้ `.env` แล้วค่าไม่เปลี่ยน

หยุด Backend แล้วเริ่มใหม่ด้วย `--env-file .env` การแก้ `.env` ไม่มีผลกับ process ที่กำลังทำงานอยู่

## ข้อจำกัดปัจจุบัน

- รองรับเฉพาะพืช 6 ชนิดและ label space ที่กำหนด
- Plant Classifier เหมาะกับภาพใบพืชบนพื้นหลังเรียบ/ควบคุมได้
- Unsupported/OOD detection ยังไม่ผ่านการยืนยันด้วยชุดทดสอบอิสระ
- ผลจาก softmax อาจมั่นใจสูงแต่ผิดได้ จึงต้องคง manual selection/confirmation
- ผลโรคเป็น image classification เบื้องต้น ไม่ใช่คำวินิจฉัยทางห้องปฏิบัติการ
- Login/Register ยังไม่ใช่ระบบบัญชีผู้ใช้เต็มรูปแบบ
- Runtime inference อยู่บน Backend ไม่ได้รัน TensorFlow Lite บนโทรศัพท์
- Release signing สำหรับการเผยแพร่จริงยังไม่ได้ตั้งค่า

## เอกสารอ้างอิงใน Repository

- [`PHYTOSCAN_PRESENTATION_HANDOVER.md`](PHYTOSCAN_PRESENTATION_HANDOVER.md) — ภาพรวมระบบและหลักฐานสำหรับนำเสนอ
- [`FULL_SYSTEM_TEST_2026-10-27.md`](FULL_SYSTEM_TEST_2026-10-27.md) — ผลทดสอบระบบแบบ end-to-end
- [`FINAL_PLANT_CLASSIFIER_CLOSURE_2026-10-30.md`](FINAL_PLANT_CLASSIFIER_CLOSURE_2026-10-30.md) — การเลือก Plant Classifier baseline
- [`PLANT_CLASSIFIER_TECHNICAL_AUDIT_AND_REDESIGN_PLAN_2026-10-29.md`](PLANT_CLASSIFIER_TECHNICAL_AUDIT_AND_REDESIGN_PLAN_2026-10-29.md) — Technical audit และข้อจำกัดด้านข้อมูล
- [`backend/evaluation/hybrid_candidate_v1/`](backend/evaluation/hybrid_candidate_v1/) — หลักฐาน Hybrid candidate
- [`ai_model/plant_classifier_fasttrack/README.md`](ai_model/plant_classifier_fasttrack/README.md) — Training/Evaluation pipeline สำหรับงานวิจัย

## หมายเหตุด้านข้อมูลและความเป็นส่วนตัว

- ห้าม commit `backend/.env`, database runtime, model binaries หรือ signing keys
- อย่านำข้อมูลส่วนบุคคลหรือภาพที่ไม่มีสิทธิ์ใช้งานเข้า dataset/evaluation artifacts
- การนำระบบไปใช้ภายนอกเครือข่ายทดสอบควรเพิ่ม HTTPS, authentication, rate limiting, secret management และนโยบายเก็บรักษาข้อมูลก่อน
