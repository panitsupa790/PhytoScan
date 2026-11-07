# PhytoScan — เอกสารส่งมอบสำหรับเตรียมนำเสนอและตอบคำถามกรรมการ

วันที่รวบรวมหลักฐาน: 2 พฤศจิกายน 2026  
ขอบเขตการตรวจ: Source Code, Configuration, Model Manifest, Dataset Metadata, Training Artifacts, Evaluation Reports และเอกสารที่มีอยู่จริงในเครื่องโครงการ  
ข้อควรจำ: เอกสารนี้แยก **ผลจำแนกชนิดพืช** ออกจาก **ผลจำแนกโรค/อาการ** และไม่ถือว่าคะแนนบนชุดข้อมูลที่เตรียมไว้เป็นความแม่นยำของภาพธรรมชาติทั่วไป

## สัญลักษณ์สถานะหลักฐาน

| สถานะ | ความหมาย |
|---|---|
| **ยืนยันจากโค้ด** | ตรวจพบพฤติกรรมหรือค่าจาก Source Code/Config/Manifest ปัจจุบัน |
| **ยืนยันจากผลทดลอง** | มี Metrics, Row-level Predictions, Confusion Matrix, Receipt หรือ Training History รองรับ |
| **ยังไม่มีหลักฐาน** | ไม่พบ Artifact ที่พอใช้ยืนยัน หรือยังไม่ได้ทดสอบตามขอบเขตนั้น |

---

# ส่วน A: สรุปฉบับอ่านเร็ว

## A1. PhytoScan คืออะไร

PhytoScan เป็นแอป Flutter ที่ส่งภาพใบพืชไปยัง FastAPI Backend เพื่อทำงานแบบสองขั้นตอน:

1. จำแนกชนิดพืชว่าเป็นหนึ่งใน 6 ชนิดที่รองรับ
2. เลือกโมเดลโรคเฉพาะชนิดพืชนั้น แล้วจำแนกโรค อาการผิดปกติ หรือใบสุขภาพดี

ระบบไม่ได้รัน TensorFlow Lite บนโทรศัพท์ โมเดลจริงเป็นไฟล์ `.keras` และประมวลผลที่ Backend ด้วย TensorFlow/Keras **ยืนยันจากโค้ด** จาก `mobile_app/lib/services/api_service.dart`, `backend/app/api/routes/analyze.py`, `backend/app/services/plant_classifier_service.py` และ `backend/app/services/plant_model_service.py`

### ปัญหาที่ต้องการช่วยแก้

- ลดขั้นตอนการเลือกโมเดลโรคด้วยตนเอง โดยจำแนกชนิดพืชก่อน
- ให้ผลวิเคราะห์เบื้องต้นจากภาพ พร้อมอาการ วิธีดูแล และการป้องกันที่มีใน Metadata
- เก็บประวัติการสแกนเพื่อย้อนดูผลเดิม
- ลดความเสี่ยงจากผลชนิดพืชที่ไม่ชัดด้วย Threshold และการให้ผู้ใช้ยืนยัน

### ขอบเขตที่ยืนยันได้

- รองรับพืช 6 ชนิดและ Disease Class 23 คลาส
- รับภาพ JPG/JPEG/PNG ครั้งละ 1–3 ภาพ ขนาดไม่เกิน 10 MB ต่อภาพ
- Plant Classifier มีขอบเขตที่ประกาศไว้สำหรับใบพืชบนพื้นหลังเรียบ/ควบคุมได้
- ผลเป็นการวิเคราะห์เบื้องต้นจากภาพ ไม่ใช่การตรวจทางห้องปฏิบัติการ
- ไม่รับประกันการปฏิเสธพืชนอก 6 ชนิดหรือภาพ OOD (Out-of-Distribution)

แหล่งหลัก: `backend/app/data/plant_classifier_final_metadata.json`, `backend/app/core/config.py`, `backend/app/services/image_service.py`

## A2. พืชและโรค/อาการที่รองรับ

| พืช | Plant code | จำนวนคลาส | โรค/อาการตาม Class Mapping ปัจจุบัน |
|---|---|---:|---|
| เบญจมาศ | `chrysanthemum` | 3 | อาการใบจุดจากแบคทีเรีย, ใบสุขภาพดี, ลักษณะใบจุดเซปโทเรีย |
| ดาวเรือง | `marigold` | 3 | ใบไหม้อัลเทอร์นาเรีย, ใบสุขภาพดี, ความเสียหายจากศัตรูพืช |
| พลูด่าง | `money_plant` | 3 | โรคเหี่ยวจากแบคทีเรีย, ใบสุขภาพดี, ภาวะแมงกานีสเป็นพิษ |
| กุหลาบ | `rose` | 8 | อาการใบด่างเหลืองคล้ายโมเสก, สนิม, ราแป้ง, โรสโมเสก, แมลงทำลาย, ใบสุขภาพดี, ราน้ำค้าง, ใบจุดดำ |
| ลิ้นมังกร | `snake_plant` | 3 | แอนแทรคโนส, ใบสุขภาพดี, ใบเหี่ยวหรือแห้ง |
| เศรษฐีเรือนใน | `spider_plant` | 3 | ลักษณะใบจุดจากเชื้อรา, ใบสุขภาพดี, ปลายใบแห้งตาย |

รวม 23 คลาส **ยืนยันจากโค้ด** จาก `backend/app/data/model_manifest.json` และ `backend/app/data/diseases.json`  
ข้อควรระวัง: Class code `Helathy Leaves` สะกดผิดมาตั้งแต่ Label ของโมเดล จึงยังต้องคง code เดิมเพื่อรักษา Class Mapping แต่ UI แสดงชื่อที่อ่านถูกได้

## A3. เทคโนโลยีที่ใช้จริง

| ส่วน | เทคโนโลยี | หน้าที่ | หลักฐาน |
|---|---|---|---|
| Mobile | Flutter/Dart, `http`, `image_picker`, `shared_preferences` | UI, เลือกภาพ, ตรวจไฟล์เบื้องต้น, เรียก API, cache ประวัติ | `mobile_app/pubspec.yaml` |
| API | FastAPI 0.115.12, Uvicorn 0.34.3 | รับ Multipart, ตรวจภาพ, จัด routing, ส่งผล JSON | `backend/requirements.txt`, `backend/app/main.py` |
| AI Runtime | TensorFlow 2.21.0, NumPy 2.5.3, Pillow 11.2.1 | โหลด `.keras`, preprocessing, inference | `backend/requirements.txt` |
| Database | SQLite | เก็บ reference data, model metadata และประวัติสแกน | `backend/app/db/database.py`, `backend/app/db/migrations/*.sql` |
| Model | EfficientNet-B0 / MobileNetV2 | Plant Classification และ Disease Classification | Model manifests และ training artifacts |

## A4. Workflow ที่ต้องจำ

```text
ผู้ใช้เลือก 1–3 ภาพ
→ Flutter ตรวจนามสกุล/ขนาด/จำนวนเบื้องต้น
→ POST /api/v1/analyze
→ Backend ตรวจ MIME + extension + เนื้อไฟล์จริง
→ RGB float32 [0,255] + bilinear resize 224×224
→ Plant Classifier คืน probability 6 คลาส
→ confidence = probability สูงสุด
→ margin = top-1 probability − top-2 probability
→ ผ่าน threshold ทุกภาพและเป็นพืชชนิดเดียวกันหรือไม่?
   ├─ Yes → เลือก Disease Classifier ของพืชนั้น
   └─ No  → manual_confirmation_required
             ├─ ภาพทำนายต่างชนิด → ให้แยก/แก้ชุดภาพ
             └─ คะแนนไม่ห่างพอ → ผู้ใช้ยืนยันหรือเลือกชนิดใหม่
→ Disease Classifier วิเคราะห์รายภาพ
→ ถ้าหลายภาพ ให้เฉลี่ย probability ของโรคเพื่อสร้างผลรวม
→ ดึงชื่อ/อาการ/การดูแล/การป้องกันจาก diseases.json
→ ส่งผลไป Flutter และบันทึกประวัติแบบ best-effort
```

แหล่งหลัก: `backend/app/services/analysis_router.py`, `backend/app/services/model_input.py`, `backend/app/services/plant_classifier_service.py`, `backend/app/services/plant_model_service.py`, `mobile_app/lib/screens/analyze_screen.dart`

## A5. ตารางตัวเลขสำคัญที่ควรจำ

| รายการ | ตัวเลข | สถานะ/แหล่ง |
|---|---:|---|
| พืชที่รองรับ | 6 ชนิด | **ยืนยันจากโค้ด**, `model_manifest.json` |
| โมเดลต่อหนึ่ง bundle | 7 โมเดล | Plant 1 + Disease 6 |
| Disease classes | 23 คลาส | **ยืนยันจากโค้ด**, `model_manifest.json` |
| ภาพต่อคำขอ | 1–3 ภาพ | **ยืนยันจากโค้ด**, `config.py` และ `image_service.py` |
| ขนาดสูงสุด | 10 MB/ภาพ | **ยืนยันจากโค้ด**, `config.py` |
| Input | 224×224×3 RGB, float32 [0,255] | **ยืนยันจากโค้ด**, `model_input.py` |
| Plant Train / Validation / Test | 3,599 / 2,340 / 1,580 | **ยืนยันจาก Dataset Metadata**, `plant_classifier_v1/dataset_config.json` |
| EfficientNet-B0 V1 Plant Test | 1,573/1,580 = 99.557% | **ยืนยันจากผลทดลอง** |
| MobileNetV2 Plant Test | 1,578/1,580 = 99.873% | **ยืนยันจากผลทดลอง** |
| Default Efficient threshold | confidence 0.0, margin 0.6936512 | **ยืนยันจาก Config** |
| Hybrid candidate threshold | confidence 0.0, margin 0.3455163 | **ยืนยันจาก Config** |
| ภาพ Emulator diagnostic | 25 ไฟล์ / 24 เนื้อหาไม่ซ้ำ | **ยืนยันจากผลทดลอง**, ไม่มี ground truth ครบ |
| Backend API warm latency | mean 0.517 s/request | **ยืนยันจาก Full-system diagnostic**, ไม่ใช่ inference time ต่อโมเดล |

## A6. ผลเปรียบเทียบ Plant Classifier บน Test Set เดียวกัน 1,580 ภาพ

| โมเดล | Accuracy | Macro Precision | Macro Recall | Macro F1 | Min class recall | ขนาดใน comparison report |
|---|---:|---:|---:|---:|---:|---:|
| EfficientNet-B0 V1 | 99.557% | 98.257% | 99.573% | 98.889% | 98.485% | 17.156 MB |
| MobileNetV2 | 99.873% | 99.444% | 99.972% | 99.703% | 99.829% | 23.041 MB |

สถานะ: **ยืนยันจากผลทดลอง** จาก `/home/mind_hp/phytoscan/phytoscan/models/plant_classifier_mobilenetv2/comparison_reports/20261101_035921_262354/comparison_metrics.csv` และ `backend/evaluation/hybrid_candidate_v1/final_test_20261101/`  
ผล Row-level ตรงกับรายงาน Jupyter และใช้ Test Manifest SHA-256 เดียวกัน แต่ชุดนี้เป็น prepared/controlled-domain test ไม่ใช่ External Mobile Test

## A7. Bundle ที่มีอยู่และสถานะปัจจุบัน

### Default/Active baseline

- Plant Classifier: EfficientNet-B0 V1
- Disease Classifier: EfficientNet-B0 ทั้ง 6 ชนิด
- Manifest: `backend/app/data/model_manifest.json`
- Threshold: `MIN_CONFIDENCE=0.0`, `MIN_MARGIN=0.6936511993408203`
- Metadata ระบุขอบเขตพื้นหลังควบคุม

### Hybrid candidate

- Plant Classifier: MobileNetV2
- Disease: MobileNetV2 สำหรับเบญจมาศ พลูด่าง กุหลาบ ลิ้นมังกร เศรษฐีเรือนใน
- Disease ดาวเรือง: EfficientNet-B0 เดิม เพราะ Macro F1 ของ EfficientNet สูงกว่าใน Test ที่เทียบกันได้
- Manifest ระบุ `candidate_staging_not_active` และต้องได้รับอนุมัติก่อน activate
- Manifest: `backend/app/data/model_manifest.hybrid_candidate.json`
- Threshold: `MIN_CONFIDENCE=0.0`, `MIN_MARGIN=0.34551629424095154`

### Runtime ณ วันที่ตรวจ

`backend/.env` ชี้กลับไป Default EfficientNet manifest และ corrective threshold แล้ว แต่โค้ด `backend/app/core/config.py` ไม่เรียก `load_dotenv()` เอง ดังนั้น `.env` จะมีผลเมื่อคำสั่งรันโหลดไฟล์นี้ เช่น `uvicorn app.main:app --env-file .env` หรือมี environment variables อยู่ก่อนเริ่ม process เท่านั้น หากรันแบบธรรมดาโดยไม่โหลด `.env` จะใช้ค่า default ใน `config.py` ซึ่งปัจจุบันเป็น EfficientNet baseline เหมือนกัน

## A8. สรุปความพร้อมและข้อจำกัด

### ใช้งานจริงในระบบแล้ว

- Flutter → FastAPI → Plant Classifier → Threshold → Disease Router → Disease Classifier → Result
- Automatic flow, manual plant selection และ manual confirmation
- ประวัติ Backend SQLite + local cache ใน Flutter
- Plant library API/UI
- การตรวจ checksum, shape, class count และ frozen threshold receipt แบบ fail-closed
- Android Emulator E2E ผ่านกับ Backend จริงตาม `FULL_SYSTEM_TEST_2026-10-27.md`

### ยังไม่สมบูรณ์หรือยังไม่มีหลักฐาน

- Login/Register/Forgot password เป็น UI เท่านั้น ยังไม่มี Auth flow จริง
- Profile ส่วนใหญ่เป็น guest/static
- Unsupported/OOD plant detection: **ยังไม่มีหลักฐาน**
- Physical Android device: **ยังไม่ได้ทดสอบ** ใน full-system report
- Interactive Web E2E: ยัง blocked
- EfficientNet disease model ของกุหลาบ: ไม่พบ Test metrics ที่กู้คืนได้
- Inference time แยกรายโมเดลทั้ง 14 artifact: **ยังไม่มี benchmark ที่ควบคุมเครื่อง/warm-up/batch แบบเดียวกัน**
- ภาพธรรมชาติทั่วไป: ทั้ง EfficientNet และ Hybrid ยังมี confident misclassification

---

# ส่วน B: อธิบายเชิงเทคนิคแบบเข้าใจง่าย

## B1. สถาปัตยกรรมระบบ

```text
Flutter App
  ├─ กล้อง / Gallery / ตรวจไฟล์เบื้องต้น
  ├─ หน้าสแกน / ยืนยันชนิดพืช / ผล / รายละเอียด / ประวัติ / คลังพืช
  └─ HTTP Multipart + X-Device-ID
          ↓
FastAPI Backend
  ├─ Image validation
  ├─ Plant Classifier Service
  ├─ Threshold Decision
  ├─ Disease Model Router
  ├─ Disease Metadata Catalog
  └─ SQLite History / Reference Data
          ↓
TensorFlow/Keras .keras Models
  ├─ Plant Classifier 1 โมเดล → 6 classes
  └─ Disease Classifier 6 โมเดล → รวม 23 classes
```

หน้าที่แต่ละส่วน:

- **Flutter** ดูแลประสบการณ์ผู้ใช้ ไม่ทำ inference ของโมเดล
- **FastAPI** ตรวจข้อมูล ประสาน flow เลือกโมเดลและสร้าง response
- **TensorFlow/Keras** โหลด checkpoint และคำนวณ probability
- **SQLite** เก็บข้อมูลอ้างอิงและประวัติ ไม่ใช่ที่เก็บ model weights

แหล่ง: `mobile_app/lib/main.dart`, `mobile_app/lib/services/api_service.dart`, `backend/app/main.py`, `backend/app/services/*.py`, `backend/app/db/migrations/*.sql`

## B2. ฟีเจอร์ที่ผู้ใช้เข้าถึงได้

1. Splash → Login UI → เข้าแบบผู้ใช้ทั่วไป
2. Home: ค้นหาพืช, Scan อัตโนมัติ, เลือกพืชเอง, คลังพืช, ประวัติ, Profile
3. Scan: กล้องหรือ Gallery สูงสุด 3 ภาพ
4. Manual Confirmation เมื่อผลชนิดพืชไม่ผ่านเกณฑ์
5. Result: ชนิดพืช, โรค/อาการ, รูป, รายละเอียด, คำแนะนำ
6. History: โหลดจาก Backend เมื่อออนไลน์และ fallback local cache
7. Plant Library: ข้อมูลพืชและการดูแลเบื้องต้น

### ส่วนที่มีโค้ดแต่ยังไม่เชื่อมใช้งานจริง

- `backend/app/services/mock_ai_service.py` มีอยู่แต่ Active Analyze Route ไม่ได้เรียกใช้
- `backend/app/services/eggplant_model_service.py` เป็น legacy/research path ไม่อยู่ใน Active 6-plant router
- ตาราง `users` และ `auth_sessions` มีใน SQLite schema แต่ Flutter login แจ้งว่า “ระบบบัญชียังไม่เปิดใช้งาน”
- Sunflower ไม่อยู่ใน Active Registry/API/UI แล้ว

## B3. Workflow แบบละเอียด

### B3.1 รับและตรวจภาพ

Flutter:

- ใช้ `image_picker`
- รับ 1–3 ภาพ
- รองรับ `.jpg`, `.jpeg`, `.png`
- ตรวจขนาดไม่เกิน 10 MB/ภาพและอ่านไฟล์ได้
- ป้องกัน double submit และคงภาพไว้เมื่อ retry

Backend เป็นผู้ตรวจขั้นสุดท้าย:

- จำนวนภาพ
- extension และ MIME type
- ขนาดไฟล์
- เปิดด้วย Pillow และ `verify()`
- actual format ต้องตรงกับ extension และ MIME

แหล่ง: `mobile_app/lib/screens/analyze_screen.dart`, `mobile_app/lib/services/api_service.dart`, `backend/app/services/image_service.py`

### B3.2 Preprocessing

```text
bytes
→ tf.io.decode_image(channels=3, expand_animations=False)
→ RGB
→ tf.cast(float32)
→ tf.image.resize([224,224], bilinear, antialias=False)
→ tensor ช่วง 0–255
→ normalization ภายใน checkpoint
```

- EfficientNet-B0 ใช้ embedded rescaling ของ EfficientNet
- MobileNetV2 มีชั้น `Rescaling(1/127.5, offset=-1)` ภายในโมเดล เพื่อแปลง 0–255 เป็น -1 ถึง 1
- Backend ไม่ normalize ซ้ำ

แหล่ง: `backend/app/services/model_input.py`, `backend/app/data/model_manifest*.json`, `plant_classifier_mobileV2.ipynb`

### B3.3 Softmax, Top-1, Top-2, Confidence และ Margin

Softmax อยู่ใน Dense layer สุดท้ายของโมเดล ไม่ได้คำนวณใหม่ใน Backend โมเดลส่ง probability รวมประมาณ 1.0 แล้ว Backend ตรวจความถูกต้องของผล

Classification head ของทั้งสอง architecture:

```text
Backbone feature map
→ GlobalAveragePooling2D
→ Dropout(0.3)
→ Dense(number_of_classes, activation="softmax")
```

Plant Classifier ส่ง 6 ค่า ส่วน Disease Classifier ส่ง 3 ค่า ยกเว้น Rose ส่ง 8 ค่า

Backend ทำดังนี้:

- Top-1 = class ที่ probability สูงสุด
- Top-2 = class ที่ probability สูงเป็นอันดับสอง
- Confidence = probability ของ Top-1
- Margin = Top-1 − Top-2

ตัวอย่างเพื่ออธิบาย (ตัวเลขสมมติเพื่อสาธิตสูตร ไม่ใช่ผลทดลอง):

```text
[0.02, 0.05, 0.03, 0.80, 0.06, 0.04]
Top-1 = rose = 0.80
Top-2 = snake_plant = 0.06
Confidence = 0.80
Margin = 0.80 - 0.06 = 0.74
```

แหล่ง: `backend/app/services/plant_classifier_service.py::_to_prediction()` และ actual model layer inspection/Notebook source

### B3.4 Automatic flow

```text
Automatic request ละ plant_code
→ จำแนกชนิดพืชทุกภาพ
→ ทุกภาพ confidence >= MIN_CONFIDENCE ?
→ ทุกภาพ margin >= MIN_MARGIN ?
→ ทุกภาพทำนายเป็น plant_code เดียวกัน ?
   ├─ Yes → ใช้ confidence ต่ำสุดในชุดเป็นค่าประกอบผลพืช
   │        → เรียก Disease Classifier ของ plant_code นั้น
   └─ No  → manual_confirmation_required
```

Backend จะไม่เรียก Disease Classifier ก่อน Plant Routing ผ่านเกณฑ์ **ยืนยันจากโค้ด** ที่ `backend/app/services/analysis_router.py`

### B3.5 Manual confirmation flow

กรณี confidence/margin ต่ำแต่แต่ละภาพเสนอพืชเดียวกัน:

1. Backend ส่ง `manual_confirmation_required` พร้อมคำทำนายรายภาพและเหตุผล
2. Flutter แสดง suggestion และรายชื่อพืชที่รองรับ
3. ผู้ใช้ยืนยันหรือเลือกชนิดใหม่
4. Flutter ส่งภาพเดิมซ้ำพร้อม `plant_code`
5. Backend validate `plant_code`
6. ข้าม Plant Classifier และเรียก Disease Classifier ของชนิดที่ผู้ใช้เลือก

ค่า plant confidence ภายใน response ที่เป็น `1.0` ในเส้นทางนี้หมายถึง “ผู้ใช้ยืนยัน” ไม่ใช่ AI มั่นใจ 100% และ UI ปัจจุบันไม่แสดงเป็นเปอร์เซ็นต์ AI

กรณีภาพหลายภาพถูกทำนายเป็นพืชต่างชนิด (`inconsistent_plant`): Flutter ไม่ให้กดยืนยันรวม แต่ให้กลับไปแยกหรือแก้ชุดภาพ

แหล่ง: `analysis_router.py`, `analyze.py`, `manual_plant_confirmation_screen.dart`, `api_service.dart`

### B3.6 ผู้ใช้เลือกชนิดพืชเองตั้งแต่ต้น

```text
Plant Selection
→ เปิด AnalyzeScreen พร้อม plant_code
→ ส่ง plant_code + ภาพ
→ Backend validate ว่าเป็น 6 ชนิดที่รองรับ
→ ไม่เรียก Plant Classifier
→ เรียก Disease Classifier ของพืชที่เลือก
```

นี่เป็น fallback ที่สำคัญเมื่อภาพจริงอยู่นอก distribution ของ Plant Classifier

### B3.7 Disease diagnosis และหลายภาพ

Disease Classifier ทำ prediction รายภาพและเก็บผลรายภาพไว้ ถ้ามีหลายภาพ ระบบเฉลี่ย probability vector ของทุกภาพแล้วเลือก class ที่ค่าเฉลี่ยสูงสุดเป็นผลรวม ไม่ได้เฉลี่ยชื่อโรคหรือรวมพืชต่างชนิดแบบเงียบ ๆ

หลังได้ class code ระบบอ่านชื่อ อาการ การดูแล และการป้องกันจาก `backend/app/data/diseases.json` หาก metadata ไม่มี ระบบ fail ด้วย inference error ไม่สร้างข้อมูลโรคขึ้นเอง

แหล่ง: `backend/app/services/plant_model_service.py`, `backend/app/services/disease_catalog.py`

### B3.8 แสดงผลและบันทึกประวัติ

Flutter แสดง:

- รูปที่ส่ง
- ชนิดพืช และระบุว่าอัตโนมัติหรือผู้ใช้ยืนยัน
- ชื่อโรค/อาการหรือ Healthy
- คำแนะนำจาก Backend Metadata
- คำเตือนว่าเป็นผลเบื้องต้นจากภาพ

ตามการออกแบบล่าสุด UI ไม่แสดง AI confidence percentage แต่ API model, database และ logs ยังคงเก็บ confidence เพื่อใช้ logic และตรวจสอบย้อนหลัง

Backend เก็บ:

- session/device
- filename, MIME, size, width/height, SHA-256 (ไม่เก็บ image bytes ใน schema ปัจจุบัน)
- plant prediction, probability candidates, confidence, margin และเหตุผล reject
- disease result และ metadata snapshot
- ประวัติลบแบบ soft delete

Flutter เก็บ local summary ไม่เกิน 100 รายการด้วย SharedPreferences และ sync กับ Backend เมื่อออนไลน์

แหล่ง: `backend/app/db/migrations/001_initial_schema.sql`, `backend/app/db/analysis_repository.py`, `mobile_app/lib/services/scan_history_store.dart`

### B3.9 การจัดการข้อผิดพลาด

| กรณี | Backend/API | Flutter |
|---|---|---|
| ไม่มีภาพ/เกิน 3 | 400 | แจ้งผู้ใช้ |
| ชนิดไฟล์ไม่รองรับ | 415 | แจ้ง JPG/JPEG/PNG |
| ไฟล์เกิน 10 MB | 413 | แจ้งขนาดเกิน |
| ไฟล์เสีย/ชนิดไม่ตรง | 400 | แจ้งภาพไม่ถูกต้อง |
| plant code ไม่รองรับ | 400 | แจ้งให้เลือกใหม่ |
| model/checksum/config ไม่พร้อม | 503 | แสดง model unavailable และ retry |
| inference ล้มเหลว | 500 | แสดงข้อผิดพลาดและ retry |
| timeout/network/offline | client-side | เก็บภาพเดิมไว้และ retry ได้ |
| DB บันทึกไม่ได้ | log error | ยังคืนผล inference ที่สำเร็จ เพราะ persistence เป็น best-effort |

## B4. EfficientNet-B0 และ MobileNetV2 คืออะไร

ทั้งสองเป็น CNN backbone ที่ pretrain บน ImageNet แล้วนำ feature ที่เรียนรู้ทั่วไปมาปรับกับงาน PhytoScan

| ประเด็น | EfficientNet-B0 | MobileNetV2 |
|---|---|---|
| แนวคิด | ปรับสมดุล depth/width/resolution | ใช้ depthwise convolution และ inverted residual เพื่อความเบา |
| Normalization ในระบบ | EfficientNet embedded rescaling | embedded rescaling 0–255 → -1..1 |
| Plant V1 runtime file | 16.361 MiB | Candidate 21.974 MiB |
| Plant Test 1,580 | Accuracy 99.557%, Macro F1 98.889% | Accuracy 99.873%, Macro F1 99.703% |
| สถานะ | Default final integration baseline | Hybrid candidate, ไม่ active โดย manifest |
| ภาพจริง | มี confident errors | มี confident errors เช่นกัน |

คำว่า MobileNet ไม่ได้แปลว่าโมเดลนี้รันบนโทรศัพท์ในระบบปัจจุบัน และไฟล์ MobileNetV2 ที่ export มามีขนาดใหญ่กว่า Plant EfficientNet V1 เพราะขนาดไฟล์ขึ้นกับสิ่งที่ checkpoint บันทึก ไม่ใช่ชื่อ architecture อย่างเดียว

## B5. Transfer Learning และ Fine-tuning

**Transfer Learning** คือเริ่มจาก backbone ที่เรียนรู้ลักษณะภาพทั่วไปจาก ImageNet แล้วฝึกหัวจำแนกใหม่สำหรับคลาสของโครงการ  
**Fine-tuning** คือเปิดบางชั้นท้ายของ backbone ให้ปรับค่าน้ำหนักต่อด้วย learning rate ต่ำ

### MobileNetV2 Plant Classifier — ยืนยันครบ

- `weights="imagenet"`, `include_top=False`
- Phase 1 freeze backbone, Adam LR `1e-3`, max 20 epochs
- Phase 2 unfreeze 40 ชั้นท้าย, freeze BatchNorm, Adam LR `1e-5`, max 15 epochs
- Batch 8, sparse categorical cross-entropy
- EarlyStopping patience 5, ReduceLROnPlateau, checkpoint by validation loss
- ฝึกจริง Phase 1 = 12 epochs, Phase 2 = 6 epochs; เลือก Phase 2 best epoch 1

แหล่ง: `/home/mind_hp/phytoscan/phytoscan/plant_classifier_mobileV2.ipynb`, experiment `20261101_034517_516251/experiment_config.json`, histories และ `model_selection.json`

### MobileNetV2 Disease Classifiers — ยืนยันจาก Notebook และ histories

ค่าร่วมใน `MobileNetV2_Comparison.ipynb`:

- ImageNet MobileNetV2, input 224, Batch 8
- Phase 1 LR `1e-3`, max 20
- Phase 2 LR `1e-5`, max 15, fine-tune 40 ชั้นท้าย, freeze BatchNorm
- Adam + sparse categorical cross-entropy
- Augmentation: horizontal/vertical flip, rotation 0.15, zoom 0.15, translation 0.1, contrast 0.15
- EarlyStopping patience 5

| งาน | Epoch ที่ฝึกจริง Phase 1 + Phase 2 | Test checkpoint |
|---|---:|---|
| เบญจมาศ | 13 + 13 = 26 | Phase 2 |
| ดาวเรือง | 19 + 9 = 28 | Phase 2 |
| กุหลาบ | 16 + 12 = 28 | Phase 2 |
| พลูด่าง | 20 + 9 = 29 | Phase 2 |
| ลิ้นมังกร | 12 + 15 = 27 | Phase 2 |
| เศรษฐีเรือนใน | 20 + 15 = 35 | Phase 2 |

จำนวนจริงมาจากจำนวนแถวใน `phase1_history.csv` และ `phase2_history.csv` ของแต่ละ experiment  
ข้อจำกัด: เบญจมาศและดาวเรืองไม่มี `experiment_config.json` แยกใน run directory แต่มี Notebook source, histories และ Test metrics; จึงไม่ควรอ้าง config file ราย run ของสองงานนี้

### EfficientNet-B0

- Training Notebook แสดง ImageNet EfficientNet-B0, GAP, Dropout 0.3, softmax, Adam และสองระยะในหลายงาน
- Plant Classifier V2 config ระบุ Batch 32, head 15 epochs LR `1e-3`, fine-tune 50 epochs LR `1e-5`, fine-tune 40 ชั้นท้าย, patience 7 และ augmentation flip/rotation 0.08/zoom 0.1/contrast 0.1
- อย่างไรก็ตาม Active Plant model คือ V1 Phase 1 และไม่มี standalone V1 config/history ที่ผูกกับ SHA `5585...` ครบเท่า MobileNet artifact จึงห้ามนำ V2 config ไปอ้างเป็นค่า V1 โดยตรง
- Disease EfficientNet แต่ละ Notebook ใช้รายละเอียดต่างกัน และ artifact ที่ export ไม่ได้เก็บ standalone config/history ครบทุกชนิด ดังนั้นค่า 30/50 epochs, Batch 16/32 หรือ LR `0.001/0.0001` ที่อยู่ในร่างวิจัยไม่สามารถเหมารวมให้ทุกโมเดลได้

แหล่ง: `plant_classifier.ipynb`, `/models/plant_classifier_v2/configs/plant_classifier_v2_training.json`, Notebook รายพืช และ metrics export

## B6. Dataset และการแบ่งข้อมูล

### B6.1 Plant Classifier 6 ชนิด

| พืช | Train | Validation | Test |
|---|---:|---:|---:|
| เบญจมาศ | 977 | 233 | 161 |
| ดาวเรือง | 338 | 73 | 73 |
| พลูด่าง | 365 | 74 | 49 |
| กุหลาบ | 1,001 | 1,775 | 1,173 |
| ลิ้นมังกร | 427 | 86 | 58 |
| เศรษฐีเรือนใน | 491 | 99 | 66 |
| **รวม** | **3,599** | **2,340** | **1,580** |

แหล่ง: `/home/mind_hp/phytoscan/phytoscan/models/plant_classifier_v1/dataset_config.json` และ manifests 3 ไฟล์  
สัดส่วนรวมไม่ใช่ 75:15:10 เพราะนำ split จากหลาย source มาประกอบและ Validation/Test ถูกครอบงำด้วยกุหลาบ จึงต้องใช้ Macro metrics และ per-class recall ร่วมกับ Accuracy

### B6.2 Disease datasets

| พืช | Train | Validation | Test | Split/ข้อสังเกต |
|---|---:|---:|---:|---|
| เบญจมาศ Efficient source | 1,029 | 206 | 138 | representative 1,373; target 75/15/10 หลัง grouping |
| ดาวเรือง | 338 | 73 | 73 | representative 484; target 70/15/15 |
| พลูด่าง | 365 | 74 | 49 | 488; stratified 75/15/10 |
| กุหลาบ Mobile experiment | 8,793 | 1,775 | 1,173 | Efficient Test metrics ยังไม่กู้คืน |
| ลิ้นมังกร | 427 | 86 | 58 | 571; stratified 75/15/10 |
| เศรษฐีเรือนใน | 491 | 99 | 66 | 656; stratified 75/15/10 |

แหล่ง: WSL `models/chrysanthemum_v1`, `models/marigold_v1`, `models/indoor_plants_v1/*`, Mobile experiment configs/manifests

### B6.3 แหล่งข้อมูลและ Label

หลักฐาน manifest แสดง path จากหลาย source บน Windows เช่นชุด Rose, indoor plants, Chrysanthemum และ Rose/Marigold Leaf Disease โดย label mapping ถูก freeze ใน `dataset_config.json`, `labels.json` และ model manifest  
สิ่งที่ยืนยันไม่ได้ครบ: provenance/license ของ legacy images ทุกไฟล์และ original plant/session identity ของหลายชุด; Audit ระบุไว้ว่า license/attribution ledger ยังไม่ครบ

### B6.4 การป้องกัน leakage และข้อมูลซ้ำ

สิ่งที่ทำแล้ว:

- แยก `group_id` ใน Plant manifests
- ตรวจ path overlap และ group overlap
- ใช้ SHA-256 สำหรับ exact duplicates
- ใช้ pHash เป็น candidate ของ near-duplicates และบางชุดใช้ ORB/RANSAC
- คู่ pHash คนละคลาสถูก manual adjudication ใน exploratory workflow
- confirmed/source-related samples ถูกบังคับให้อยู่ split เดียวกัน
- Test ไม่ถูกใช้เลือก threshold ใน frozen workflows

ข้อจำกัด:

- pHash ใกล้กันไม่เท่ากับ duplicate จริงเสมอ
- legacy source บางส่วนไม่มี plant/session/observer identity
- Audit พบ near-duplicate candidates ที่ต้อง visual review และระบุว่า duplicate screening ไม่ exhaustive

แหล่ง: `PLANT_CLASSIFIER_TECHNICAL_AUDIT_AND_REDESIGN_PLAN_2026-10-29.md`, `ai_model/plant_classifier_fasttrack/.../split/*`, dataset configs

## B7. ผลการทดลอง Plant Classification

### B7.1 EfficientNet-B0 V1

- Validation: 2,333/2,340, Accuracy 99.701%, Macro F1 99.243%, loss 0.01034
- Test: 1,573/1,580, Accuracy 99.557%, Macro Precision 98.257%, Macro Recall 99.573%, Macro F1 98.889%, loss 0.01329
- Test errors: chrysanthemum→rose 1, rose→money 2, rose→snake 3, spider→snake 1

แหล่ง: `C:/Users/HP/Desktop/PhytoScan/plant_classifier/metrics.json` และ final metadata

### B7.2 MobileNetV2

- Validation checkpoint Phase 2: Accuracy 99.957%, Macro F1 99.899%, min recall 99.944%, best val loss 0.002596
- Test: 1,578/1,580, Accuracy 99.873%, Macro Precision 99.444%, Macro Recall 99.972%, Macro F1 99.703%
- Test errors: Rose ถูกทำนายเป็น Snake Plant 2 ภาพ

แหล่ง: `model_selection.json`, comparison report และ hybrid final test receipt

### B7.3 Fresh EfficientNet-B0 Run08

- เป็น `exploratory_only`; ห้าม deploy/promotion
- Internal Debug Validation 680 ภาพ: Accuracy 95.147%, Macro F1 94.572%
- Marigold recall 81.609% ต่ำสุด
- Known failures 2 ภาพ: ถูก 1; ดาวเรืองยังผิดเป็นกุหลาบ
- ไม่ได้เปิด Legacy/Locked Test และไม่ใช่หลักฐานภาพมือถือจริง

แหล่ง: `ai_model/plant_classifier_fasttrack/exploratory_only/exploratory_only_20261030_run08/`

## B8. ผลการทดลอง Disease Classification 6 งาน

ตัวเลขด้านล่างเป็น Test metrics ที่พบจริง ค่า N/A หมายถึง artifact ไม่มีหลักฐานเพียงพอ

| พืช | Architecture | Test | Accuracy | Macro Precision | Macro Recall | Macro F1 |
|---|---|---:|---:|---:|---:|---:|
| เบญจมาศ | EfficientNet-B0 | 138 | 95.652% | N/A | N/A | 95.595% |
| เบญจมาศ | MobileNetV2 | 137 | 99.270% | 99.306% | 99.206% | 99.248% |
| ดาวเรือง | EfficientNet-B0 | 73 | 86.301% | N/A | N/A | 74.288% |
| ดาวเรือง | MobileNetV2 | 73 | 87.671% | 75.820% | 68.413% | 69.230% |
| พลูด่าง | EfficientNet-B0 | 49 | 87.755% | 90.000% | 88.095% | 87.554% |
| พลูด่าง | MobileNetV2 | 49 | 93.878% | 94.118% | 95.238% | 94.210% |
| กุหลาบ | EfficientNet-B0 | N/A | N/A | N/A | N/A | N/A |
| กุหลาบ | MobileNetV2 | 1,173 | 95.652% | 96.600% | 96.872% | 96.696% |
| ลิ้นมังกร | EfficientNet-B0 | 58 | 89.655% | 90.999% | 89.649% | 89.817% |
| ลิ้นมังกร | MobileNetV2 | 58 | 93.103% | 93.461% | 92.982% | 93.052% |
| เศรษฐีเรือนใน | EfficientNet-B0 | 66 | 96.970% | 97.333% | 96.825% | 96.944% |
| เศรษฐีเรือนใน | MobileNetV2 | 66 | 98.485% | 98.611% | 98.413% | 98.478% |

แหล่ง EfficientNet: `C:/Users/HP/Desktop/PhytoScan/<plant>/metrics.json`  
แหล่ง MobileNetV2: `/home/mind_hp/phytoscan/phytoscan/models/mobilenetv2/<plant>/experiments/<run>/test_metrics.json`

ความเทียบกันได้:

- Marigold, Money Plant, Snake Plant และ Spider Plant มี Test Manifest SHA-256 ตรงกันระหว่างสอง architecture
- Chrysanthemum manifest ไม่ตรงกันและ Test ต่าง 138 กับ 137 ภาพ จึงไม่ควรสรุปจากตัวเลขตรง ๆ ว่า MobileNet ชนะบนชุดเดียวกัน
- Rose EfficientNet metrics เป็น `pending_metrics_recovery` จึงเทียบไม่ได้
- Marigold แสดงตัวอย่างว่าดู Accuracy อย่างเดียวไม่พอ: Mobile accuracy สูงกว่าเล็กน้อย แต่ Efficient Macro F1 สูงกว่า จึงคง Efficient ใน Hybrid candidate

### Confusion Matrix และ Training curves

- Plant Classifier: มี numeric confusion matrix และ row predictions ครบ
- Disease MobileNetV2: มี `confusion_matrix.png`, `test_predictions.csv`, `phase1_history.csv`, `phase2_history.csv` ทุกงาน
- Disease EfficientNet: Money/Snake/Spider มี numeric confusion matrix ใน metrics; Chrysanthemum/Marigold export metrics ไม่มี numeric matrix; Rose metrics ยังไม่กู้คืน
- จึงไม่ควรบอกว่ามี numeric confusion matrix ครบทุกโมเดล

## B9. Model size และ Inference time

### Model size ของ Runtime files

| โมเดล | EfficientNet runtime | MobileNet export/candidate |
|---|---:|---:|
| Plant Classifier | 16.361 MiB | 21.974 MiB |
| Chrysanthemum | 31.855 MiB | 9.207 MiB |
| Marigold | 31.855 MiB | 23.0 MB ใน export; Hybrid ใช้ EfficientNet |
| Money Plant | 27.635 MiB | 21.934 MiB |
| Rose | 32.040 MiB | 22.007 MiB |
| Snake Plant | 27.635 MiB | 21.934 MiB |
| Spider Plant | 27.635 MiB | 21.934 MiB |

แหล่ง: ขนาดไฟล์ `backend/app/models/*.keras`, `backend/app/candidate_models/hybrid-v1/*.keras` และ `C:/Users/HP/Desktop/PhytoScan_MobileNetV2_Export/export_manifest.json`  
หน่วยใน export manifest ใช้ MB ส่วนตารางจาก Windows file length ใช้ MiB จึงอาจต่างเล็กน้อย

### เวลา inference

- **ยังไม่มีหลักฐาน** benchmark แบบแยก per-model ที่รัน EfficientNet/MobileNet ด้วยเครื่อง, batch, warm-up และจำนวนรอบเดียวกัน
- `FULL_SYSTEM_TEST_2026-10-27.md` วัด end-to-end Backend บน Windows CPU: cold automatic 4.312 s, warm 0.605 s, 10 warm requests mean 0.517 s และ p95 0.541 s
- ตัวเลขนี้รวม HTTP/preprocessing/Plant/Disease routing และไม่ใช่เวลาโมเดลเดียว จึงห้ามใช้กล่าวว่า architecture ใดเร็วกว่า
- Run08 วัด 680 ภาพที่ 64.34 images/s บน WSL/GPU แต่เป็น batch evaluation และไม่เทียบกับ MobileNet ภายใต้ protocol เดียวกัน

## B10. Threshold และเหตุผลการเลือก

### Default EfficientNet V1

```text
MIN_CONFIDENCE = 0.0
MIN_MARGIN     = 0.6936511993408203
```

แหล่ง: `backend/app/data/plant_classifier_evaluation_corrective.json`

### Hybrid MobileNetV2 candidate

```text
MIN_CONFIDENCE = 0.0
MIN_MARGIN     = 0.34551629424095154
```

แหล่ง: `backend/app/data/plant_classifier_threshold.hybrid_candidate.json`

### วิธีเลือก

1. ใช้ Validation เท่านั้น
2. Candidate thresholds มาจาก 0, 1 และ `nextafter(observed_value, +inf)` ใน float32
3. Accept เมื่อ confidence และ margin มากกว่าหรือเท่ากับ threshold ทั้งคู่
4. ต้องมี accepted sample อย่างน้อยหนึ่งภาพทุก true class และห้าม reject ทุกภาพ
5. เลือก accepted errors = 0 ก่อน แล้ว coverage สูงสุด
6. ถ้าเสมอ เลือก confidence ต่ำสุด แล้ว margin ต่ำสุด
7. Freeze config ก่อนเปิด Test และห้ามปรับจาก Test

Hybrid margin มีค่าดังกล่าวเพราะ Validation มีภาพที่ทำนายผิด Rose→Snake ด้วย margin `0.3455162644`; threshold คือ float32 ถัดขึ้นไป `0.3455162942` ทำให้ภาพผิดนี้ถูก reject โดยยังได้ coverage สูงสุดในกลุ่ม zero accepted errors ค่า confidence จึงคง 0.0 เพราะ margin เพียงพอและ tie-break เลือกค่าต่ำสุด

### Metrics หลัง threshold

| Profile | Set | Coverage | Accepted Accuracy | Accepted Errors |
|---|---|---:|---:|---:|
| Efficient V1 corrective | Test 1,580 | 1,556/1,580 = 98.481% | 1,555/1,556 = 99.936% | 1 |
| Hybrid candidate | Test 1,580 | 1,577/1,580 = 99.810% | 1,576/1,577 = 99.937% | 1 |

แหล่ง Efficient: `FULL_SYSTEM_TEST_2026-10-27.md`, corrective evaluation reports  
แหล่ง Hybrid: `backend/evaluation/hybrid_candidate_v1/final_test_20261101/FINAL_HYBRID_CANDIDATE_TEST_REPORT_TH.md`

ข้อจำกัดสำคัญ: Threshold เป็นตัวกรอง low-separation prediction ของ 6 คลาส ไม่ใช่ OOD detector และยังรับภาพที่ผิดแต่ margin สูงได้ 1 ภาพใน Hybrid Test

## B11. ผลภาพจริงและเหตุผลที่ต่างจาก Dataset

Diagnostic จาก Android Emulator มี 25 ไฟล์ แต่เนื้อหาไม่ซ้ำ 24 ภาพ และไม่มี ground-truth manifest ครบ จึงคำนวณ Accuracy ไม่ได้

| ประเด็น | Efficient | Hybrid |
|---|---:|---:|
| วิเคราะห์ต่อถึง Disease | 23/25 | 22/25 |
| ขอ manual confirmation | 2/25 | 3/25 |
| Plant predictions ตรงกัน | 21/25 | 21/25 |

ตัวอย่าง:

- ภาพดาวเรืองที่ผู้ใช้ยืนยัน: ทั้งสองทำนายเป็น Rose ด้วย margin ประมาณ 0.9999 และ route ไปโมเดลโรคกุหลาบ
- ภาพลิ้นมังกรหนึ่งภาพ: Efficient ทำนาย Rose ด้วย margin สูง; Hybrid Top-1 เป็น Snake Plant แต่ margin ต่ำจึงขอ confirmation
- ภาพพลูด่างหนึ่งภาพ: Efficient ขอ confirmation เป็น Rose; Hybrid ทำนาย Money Plant ด้วย margin สูง
- อีกภาพที่ดูคล้ายลิ้นมังกร: ทั้งสองทำนาย Marigold แต่ยังไม่มี formal label manifest

สาเหตุที่เป็นไปได้และมีหลักฐานสนับสนุน:

- Dataset domain/background shortcut: ดาวเรือง train มี corner brightness เฉลี่ย 0.09 ขณะที่คลาสอื่นประมาณ 155–173
- Natural/mobile coverage น้อยและไม่สมดุล
- Validation/Test ส่วนใหญ่เป็นภาพจาก source style เดิมและ Rose ครองจำนวนมาก
- Softmax อาจมั่นใจสูงกับภาพนอก distribution; confidence ไม่ใช่ความน่าจะเป็นว่าคำตอบถูกจริง

แหล่ง: `backend/evaluation/emulator_profile_comparison_20261101/EMULATOR_IMAGE_PROFILE_COMPARISON_TH.md`, `PLANT_CLASSIFIER_TECHNICAL_AUDIT_AND_REDESIGN_PLAN_2026-10-29.md`

## B12. ปัญหาที่พบระหว่างพัฒนาและสิ่งที่แก้แล้ว

| ปัญหา | สิ่งที่ทำ | สถานะ |
|---|---|---|
| Notebook กับ Backend ให้ error count ต่างกัน | เปลี่ยน Backend จาก Pillow preprocessing เป็น TensorFlow decode/resize ให้ตรง contract | แก้แล้วและมี parity audit |
| Threshold เดิมผูกกับ preprocessing เก่า | Recalibrate ด้วย Validation และทำ corrective Test โดยไม่เขียนทับผลเดิม | แก้แล้ว |
| หลายภาพต่างพืชอาจ route ผิด | เพิ่ม `inconsistent_plant` และห้ามยืนยันรวมอัตโนมัติ | แก้แล้ว |
| Model/config ไม่ตรง artifact | ตรวจ SHA, shape, class order, frozen config/receipt และ fail-closed | แก้แล้ว |
| Confidence 1.0 หลัง manual อาจถูกเข้าใจเป็น AI 100% | UI แสดงว่า “ยืนยันโดยผู้ใช้” และซ่อนเปอร์เซ็นต์ AI | แก้แล้ว |
| Plant misclassification บนภาพธรรมชาติ | เพิ่ม manual selection/confirmation และจำกัด claim เป็น controlled background | บรรเทาแล้ว แต่โมเดลยังมีข้อจำกัด |
| Sunflower เคยอยู่ในระบบ | ถอดออกจาก Active Registry/API/UI | แก้แล้ว |

## B13. Test และความพร้อมระบบ

- Phase 1.2 Backend: 63 passed จาก `backend/evaluation/automated_test_results_phase1_2.txt`
- Final full system เดิม: Backend 64 passed, Flutter 23 passed + 1 conditional skipped, real-backend conditional 1 passed, Android debug build PASS
- Hybrid final report: Backend 81 passed และ candidate receipt/runtime smoke 8 passed
- Android Emulator flow หลัก PASS
- Physical Android: NOT TESTED
- Web interactive E2E: BLOCKED

จำนวน test ต่างกันเพราะเป็นคนละช่วงเวลา/ขอบเขต ไม่ควรรวมเป็นยอดเดียว

## B14. ข้อจำกัดที่ต้องพูดให้ชัด

1. ระบบรองรับเพียง 6 ชนิดและ 23 class ที่กำหนด
2. ไม่ได้พิสูจน์ว่าแยก unsupported/OOD plants ได้
3. Plant metrics สูงบน prepared dataset แต่ไม่เท่ากับภาพธรรมชาติทั่วไป
4. Confidence สูงยังผิดได้ เพราะโมเดลเลือกคำตอบที่ใกล้ feature ที่เรียนรู้ที่สุด
5. Manual confirmation เป็น safety fallback ไม่ใช่หลักฐานว่าโมเดลถูก
6. Disease result คือ image classification ไม่ใช่ pathogen/lab confirmation
7. Metadata บางโรคใช้ถ้อยคำ “ลักษณะคล้าย” เพื่อไม่ยืนยันสาเหตุเกินภาพ
8. Test set ของ Disease Efficient/Mobile ไม่ตรงกันครบทุกงาน
9. Efficient Rose metrics และ per-model latency ยังไม่มีหลักฐาน
10. Auth, physical-device validation, full Web E2E ยังไม่เสร็จ

---

# ส่วน C: เตรียมตอบคำถามกรรมการ

## C1. คำถามและคำตอบสั้นที่พูดได้จริง

### 1) PhytoScan ทำอะไร?

“ระบบรับภาพใบพืช 1–3 ภาพ จำแนกชนิดพืช 6 ชนิดก่อน แล้วเลือกโมเดลโรคเฉพาะพืชเพื่อให้ผลโรคหรืออาการเบื้องต้น พร้อมคำแนะนำและประวัติ โดย inference ทำที่ FastAPI Backend”

### 2) ทำไมต้องมีสองขั้น Plant แล้ว Disease?

“เพราะแต่ละพืชมีชุดโรคต่างกัน การระบุชนิดพืชก่อนทำให้เลือกโมเดลและ label space ที่ถูกต้อง และป้องกันไม่ให้เอาคลาสโรคของพืชหนึ่งไปใช้กับอีกพืชหนึ่ง”

### 3) ทำไมเลือก EfficientNet-B0 และ MobileNetV2?

“EfficientNet-B0 เป็น baseline ที่มี runtime และ threshold chain ผ่านการตรวจแล้ว ส่วน MobileNetV2 เป็น candidate ที่ออกแบบให้คำนวณมีประสิทธิภาพและนำมาเทียบภายใต้ Test เดียวกันสำหรับ Plant Classifier แต่ในระบบนี้ทั้งคู่ยังรันบน Backend ไม่ใช่บนมือถือ”

### 4) Transfer Learning คืออะไร และใช้จริงหรือไม่?

“ใช้จริงครับ/ค่ะ โดยเริ่ม backbone จาก ImageNet แล้วฝึกหัวจำแนกของเรา จากนั้น fine-tune ชั้นท้ายด้วย learning rate ต่ำ หลักฐานอยู่ใน training notebooks และ experiment histories”

### 5) Fine-tuning ต่างจากการฝึกหัวจำแนกอย่างไร?

“ระยะแรก freeze backbone แล้วฝึก Dense head ส่วน fine-tuning เปิดบางชั้นท้ายของ backbone เช่น 40 ชั้น เพื่อปรับ feature ให้เข้ากับใบพืช พร้อม freeze BatchNorm เพื่อลดความไม่เสถียร”

### 6) CNN คำนวณคำตอบจากภาพอย่างไร?

“CNN สกัด feature เช่นขอบ รูปร่าง สี และ texture ผ่านหลายชั้น แล้ว Global Average Pooling ย่อ feature ก่อน Dense softmax แปลงเป็นคะแนนรวม 1 สำหรับแต่ละ class”

### 7) Softmax, Confidence และ Margin ต่างกันอย่างไร?

“Softmax คือ vector คะแนนทุกคลาส Confidence คือคะแนนสูงสุด ส่วน Margin คือคะแนนอันดับหนึ่งลบอันดับสอง ใช้ดูว่าคำตอบนำคู่แข่งมากแค่ไหน”

### 8) ทำไม MIN_CONFIDENCE เป็น 0 แต่ยังกรองได้?

“เพราะการทดลอง Validation พบว่า Margin เป็นตัวแยก error ได้ตามเกณฑ์ conservative อยู่แล้ว การ tie-break จึงเลือก confidence ต่ำสุด 0 เพื่อรักษา coverage โดยยังต้องผ่าน margin”

### 9) ทำไม Hybrid MIN_MARGIN เท่ากับ 0.3455162942?

“Validation มีภาพผิดที่ margin 0.3455162644 จึงใช้ค่า float32 ถัดขึ้นไปด้วย `nextafter` เพื่อ reject ภาพนั้น แล้วเลือกคู่ที่ zero accepted errors และ coverage สูงสุด โดยไม่ได้ใช้ Test ปรับค่า”

### 10) Threshold รับประกันว่าผลถูกหรือไม่?

“ไม่รับประกันครับ/ค่ะ Test ของ Hybrid ยังมี accepted error 1 ภาพ และภาพจริงดาวเรืองผิดเป็นกุหลาบด้วย margin สูง Threshold จึงลดความเสี่ยงบางกรณี แต่ไม่ใช่ตัวตรวจ OOD”

### 11) ทำไม AI มั่นใจสูงแต่ตอบผิด?

“Softmax วัดความเด่นสัมพัทธ์ระหว่าง 6 ตัวเลือก ไม่ได้วัดว่าภาพอยู่ในข้อมูลที่โมเดลรู้จักหรือไม่ ถ้า dataset มี background/source bias โมเดลอาจจับ shortcut แล้วมั่นใจสูงกับคำตอบผิด”

### 12) ผล MobileNetV2 ดีกว่า EfficientNet-B0 หรือไม่?

“บน Plant Test 1,580 ภาพเดียวกัน MobileNetV2 มี Accuracy และ Macro F1 สูงกว่า แต่ยังสรุปว่าเหนือกว่าทุกสถานการณ์ไม่ได้ เพราะ Test เป็น prepared domain และภาพ Emulator ไม่มี ground truth ครบ ทั้งสองยังผิดกับภาพจริงบางภาพ”

### 13) Hybrid ต่างจาก EfficientNet bundle เดิมอย่างไร?

“Hybrid ใช้ MobileNetV2 เป็น Plant Classifier และใช้ MobileNetV2 สำหรับโรค 5 พืช แต่คง EfficientNet-B0 สำหรับดาวเรืองเพราะ Macro F1 ดีกว่าใน Test เดียวกัน ปัจจุบันเป็น candidate staging ไม่ใช่ active manifest”

### 14) ทำไมไม่ใช้ Accuracy อย่างเดียว?

“ข้อมูลไม่สมดุล โดย Rose มี 1,173 จาก 1,580 ภาพใน Plant Test Accuracy อาจถูกคลาสใหญ่ครอบงำ เราจึงดู Macro Precision/Recall/F1 และ minimum per-class recall ด้วย”

### 15) Dataset แบ่ง 75:15:10 หรือไม่?

“Disease datasets บางชุดใช้ 75:15:10 เช่นพลูด่าง ลิ้นมังกร เศรษฐีเรือนใน และเบญจมาศตั้งเป้า 75:15:10 แต่ดาวเรืองใช้ 70:15:15 ส่วน Plant Classifier รวมหลาย source/split จึงไม่ใช่ 75:15:10 โดยรวม”

### 16) ป้องกัน Data Leakage อย่างไร?

“ใช้ group-aware split, ตรวจ path/SHA-256, pHash และบางชุดใช้ ORB/RANSAC คู่ที่เสี่ยงข้ามคลาสต้อง manual review และ Test ไม่ถูกใช้เลือก threshold แต่ audit ยอมรับว่ายังตรวจ near-duplicate ไม่ exhaustive”

### 17) ระบบรองรับพืชนอก 6 ชนิดหรือไม่?

“ไม่รองรับและยังไม่มี OOD dataset สำหรับพิสูจน์การ reject จึงอาจบังคับเลือกหนึ่งใน 6 คลาส ผู้ใช้ควรเลือกชนิดเองหรือไม่ใช้ผลถ้าพืชอยู่นอกขอบเขต”

### 18) ถ้าภาพหลายภาพเป็นคนละพืช ระบบทำอย่างไร?

“ถ้า Plant predictions ไม่ตรงกัน Backend ส่ง `inconsistent_plant` และ Flutter ให้ผู้ใช้แยกหรือแก้ชุดภาพ ไม่ส่งภาพเหล่านั้นไป Disease Classifier เป็นผลเดียวโดยอัตโนมัติ”

### 19) ข้อมูลโรคและคำแนะนำมาจากไหน?

“ชื่อ อาการ การดูแล และการป้องกันอ่านจาก `diseases.json` และ snapshot ลง SQLite ระบบไม่สร้างข้อมูลใหม่จากโมเดล หาก metadata ไม่มีจะ fail แทนการแต่งข้อมูล”

### 20) ระบบพร้อม Production หรือยัง?

“Flow หลักผ่าน Emulator และ automated tests แล้ว แต่ยังไม่ควรเรียก production-verified เพราะยังไม่มี physical-device validation ครบ, Web E2E ยัง blocked, OOD ไม่ได้พิสูจน์, ภาพธรรมชาติยังมี confident errors และ Auth ยังไม่เชื่อมจริง”

## C2. จุดที่ไม่ควรตอบเกินหลักฐาน

- อย่าพูดว่า “รองรับพืชทุกชนิด” — รองรับ 6 ชนิดเท่านั้น
- อย่าพูดว่า “ตรวจโรคได้แน่นอน” — เป็น classification เบื้องต้นจากภาพ
- อย่าพูดว่า “Accuracy ภาพจริง 99%” — 99% มาจาก prepared Test Set
- อย่าพูดว่า “MobileNet เร็วกว่า” — ยังไม่มี controlled per-model latency benchmark
- อย่าพูดว่า “ทุก disease model ใช้ Test เดียวกัน” — Chrysanthemum ต่าง 1 ภาพ และ Rose Efficient metrics ไม่มี
- อย่าพูดว่า “Threshold ตรวจจับพืชนอกระบบได้” — Unsupported/OOD NOT VERIFIED
- อย่าพูดว่า “MobileNet ทำงานบนมือถือ” — ปัจจุบันรันบน FastAPI Backend
- อย่าพูดว่า “Login ใช้งานได้แล้ว” — ยังเป็น UI/guest flow
- อย่ารวม Plant Accuracy กับ Disease Accuracy เป็นคะแนนเดียว
- อย่าใช้ Validation เป็น Test หรือใช้ Emulator diagnostic ที่ไม่มี label เป็น Accuracy

## C3. ชุดตัวเลขสั้นสำหรับท่องก่อนนำเสนอ

```text
6 พืช / 23 disease classes / 7 โมเดลต่อ bundle
ภาพ 1–3 / JPG-JPEG-PNG / 10 MB ต่อภาพ
Input 224×224 RGB float32 [0,255]

Plant Test = 1,580 ภาพ
Efficient V1: Accuracy 99.557%, Macro F1 98.889%
MobileNetV2: Accuracy 99.873%, Macro F1 99.703%

Default margin = 0.6936512
Hybrid margin = 0.3455163
Hybrid threshold Test coverage = 99.810%
Hybrid accepted accuracy = 99.937%, accepted errors = 1

ภาพ Emulator = 25 files / 24 unique / ไม่มี ground truth ครบ
Warm end-to-end API mean = 0.517 s (ไม่ใช่ per-model benchmark)
```

---

# ภาคผนวก: แผนที่หลักฐานสำหรับตรวจย้อนหลัง

## Source Code หลัก

- Flutter entry/navigation: `mobile_app/lib/main.dart`, `mobile_app/lib/screens/home_screen.dart`
- Upload/scan: `mobile_app/lib/screens/analyze_screen.dart`
- API client: `mobile_app/lib/services/api_service.dart`
- Manual confirmation: `mobile_app/lib/screens/manual_plant_confirmation_screen.dart`
- Result/detail/history: `mobile_app/lib/screens/result_screen.dart`, `disease_detail_screen.dart`, `history_screen.dart`
- Local/remote history: `mobile_app/lib/services/scan_history_store.dart`
- FastAPI app/routes: `backend/app/main.py`, `backend/app/api/routes/*.py`
- Runtime settings: `backend/app/core/config.py`, `backend/.env`
- Validation/preprocessing: `backend/app/services/image_service.py`, `model_input.py`
- Plant inference/threshold: `plant_classifier_service.py`, `analysis_router.py`, `threshold_config.py`
- Disease inference/router: `plant_model_service.py`, `model_registry.py`, `disease_catalog.py`
- Database: `backend/app/db/database.py`, `analysis_repository.py`, `history_repository.py`, `migrations/*.sql`

## Runtime Config/Metadata

- Default models: `backend/app/data/model_manifest.json`
- Hybrid candidate: `backend/app/data/model_manifest.hybrid_candidate.json`
- Default threshold: `backend/app/data/plant_classifier_evaluation_corrective.json`
- Hybrid threshold: `backend/app/data/plant_classifier_threshold.hybrid_candidate.json`
- Hybrid test receipt: `backend/app/data/plant_classifier_hybrid_candidate_test_receipt.json`
- Plant scope/final metadata: `backend/app/data/plant_classifier_final_metadata.json`
- Diseases: `backend/app/data/diseases.json`
- Plants/library: `backend/app/data/plants.json`, `plant_library.json`

## Evaluation Reports

- Parity/corrective evaluation: `backend/evaluation/plant_classifier_parity_audit.*`, `plant_classifier_*_corrective_*`
- Final system: `FULL_SYSTEM_TEST_2026-10-27.md`
- Hybrid: `backend/evaluation/hybrid_candidate_v1/`
- Real/emulator images: `backend/evaluation/emulator_profile_comparison_20261101/`
- Plant technical audit: `PLANT_CLASSIFIER_TECHNICAL_AUDIT_AND_REDESIGN_PLAN_2026-10-29.md`
- Fresh B0 Run08: `ai_model/plant_classifier_fasttrack/exploratory_only/exploratory_only_20261030_run08/`

## External/WSL Artifacts ที่เอกสารนี้อ้างถึง

- Plant dataset/training: `/home/mind_hp/phytoscan/phytoscan/models/plant_classifier_v1/`, `plant_classifier.ipynb`, `plant_classifier_mobileV2.ipynb`
- Mobile disease training/results: `/home/mind_hp/phytoscan/phytoscan/models/mobilenetv2/`, `MobileNetV2_Comparison.ipynb`
- Efficient exported metrics: `C:/Users/HP/Desktop/PhytoScan/<model>/metrics.json`
- Mobile export manifest: `C:/Users/HP/Desktop/PhytoScan_MobileNetV2_Export/export_manifest.json`

ไฟล์นอก Repository เหล่านี้เป็นหลักฐานในเครื่องพัฒนา แต่ถ้าจะส่งเล่มหรือ archive งานวิจัย ควร export สำเนาแบบ read-only พร้อม SHA-256 และ provenance เข้า research archive โดยไม่แก้ผลเดิม

## รายการที่ควรตรวจเพิ่มก่อนวันนำเสนอ

1. กู้คืน Test metrics/row predictions ของ EfficientNet-B0 Rose หรือระบุ N/A ต่อไป
2. ทำ controlled latency benchmark รายโมเดลบน hardware เดียวกัน พร้อม warm-up/batch/repetition
3. ทำ ground-truth manifest ให้ภาพ Emulator 24 ภาพไม่ซ้ำก่อนคำนวณ paired accuracy
4. ทดสอบ Physical Android device อย่างน้อยหนึ่งเครื่อง
5. ยืนยันคำสั่งรันว่าจะโหลด `.env` แบบใด และบันทึก effective manifest/threshold ตอน startup
6. เก็บ source/license/attribution ledger ของ legacy datasets ให้ครบ
7. หากต้องอ้างภาพธรรมชาติ ให้สร้าง independent external mobile test; ห้ามนำ prepared test 1,580 ไปอ้างแทน

