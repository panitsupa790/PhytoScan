# PhytoScan — Final Plant Classifier Model Selection & Integration

วันที่ปิดงาน: 30 ตุลาคม 2026  
ขอบเขตที่อนุมัติ: การจำแนกพืช 6 ชนิดจากภาพใบพืชแบบสตูดิโอ หรือภาพที่ถ่ายบนพื้นหลังเรียบและควบคุมได้

## 1. คำตัดสิน

เลือก **Plant Classifier V1** เป็น `final_integration_baseline` สำหรับ FastAPI โดยไม่เปลี่ยน Binary Checkpoint เดิม

- Model version: `plant-classifier-v1`
- Architecture: EfficientNet-B0
- Runtime artifact: `backend/app/models/plant-classifier-v1.keras`
- SHA-256: `5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165`
- สถานะคำกล่าวอ้าง: Final Integration Baseline แต่ยังไม่ใช่โมเดลที่พิสูจน์แล้วว่าแม่นยำที่สุดบนชุดทดสอบอิสระ

เหตุผลคือ V1 มี Minimum Per-Class Recall สูงสุดในชุดประเมินร่วม มี Runtime/Frozen Threshold/Corrective Test chain ที่ตรวจสอบย้อนกลับได้ครบ และไม่ต้องย้ายหรือทำสำเนา Binary ใหม่ แม้ V2 จะมี Macro-F1 สูงกว่าเล็กน้อย แต่ความต่างดังกล่าวมาจาก Validation ที่ถูกใช้ซ้ำและไม่สมดุล จึงยังไม่เพียงพอสำหรับสรุปว่า V2 เหนือกว่าอย่างพิสูจน์แล้ว

## 2. Protocol การเปรียบเทียบ

Checkpoint จริงของ V1, V2, V3, V4, V5 และ Fresh EfficientNet-B0 Run08 ถูกโหลดด้วย Standalone Evaluation Script ที่ไม่พึ่ง Notebook state และประเมินบน Manifest เดียวกันทุกโมเดล

- Dataset role: `overused_controlled_validation_diagnostic`
- Manifest: V1 `valid_split.csv`
- Manifest SHA-256: `8d0121c11c9845fedc276caa3139f820d07da03cec5694d42379728b1f296860`
- จำนวน: 2,340 ภาพ
- Class counts: chrysanthemum 233, marigold 73, money_plant 74, rose 1,775, snake_plant 86, spider_plant 99
- Locked Test: ไม่ได้เปิดและไม่ได้ใช้เลือกโมเดล
- Legacy Test: ไม่ได้ใช้เลือกโมเดลในรอบนี้

ข้อจำกัดสำคัญคือไม่มีชุดภาพสตูดิโออิสระที่ไม่เคยถูกใช้เลือกหรือประเมินโมเดลมาก่อน ชุดนี้จึงใช้เป็นหลักฐานประกอบการตัดสินใจเชิง Integration เท่านั้น ไม่ใช่ blind final test

## 3. ผลเปรียบเทียบที่คำนวณจากชุดเดียวกัน

| Model | Accuracy | Macro-F1 | Macro Recall | Minimum Class Recall | Errors | Wrong confidence ≥ 90% |
|---|---:|---:|---:|---:|---:|---:|
| V1 | 99.7009% | 99.2428% | 99.9343% | **99.6056%** | 7 | **0** |
| V2 | **99.7863%** | **99.4494%** | 99.7372% | 98.6486% | **5** | **0** |
| V3 | 99.2735% | 98.2132% | 99.8404% | 99.0423% | 17 | 4 |
| V4 | 99.5299% | 98.7967% | 99.6809% | 98.6486% | 11 | 3 |
| V5 | 99.6581% | 99.1129% | 99.7090% | 98.6486% | 8 | 1 |
| Fresh B0 Run08 | 99.5726% | 98.9145% | 99.9061% | 99.4366% | 10 | 1 |

### Recall แยกคลาสของ V1

| Class | Recall | จำนวนจริง |
|---|---:|---:|
| chrysanthemum | 100.0000% | 233/233 |
| marigold | 100.0000% | 73/73 |
| money_plant | 100.0000% | 74/74 |
| rose | 99.6056% | 1,768/1,775 |
| snake_plant | 100.0000% | 86/86 |
| spider_plant | 100.0000% | 99/99 |

V1 ผิด 7 ภาพ ซึ่งทั้งหมดมี True Label เป็น Rose และถูกทำนายเป็น Money Plant หรือ Snake Plant ไม่มีความผิดพลาดของ V1 ที่มี Top-1 Confidence ตั้งแต่ 90% ขึ้นไปในชุดนี้ อย่างไรก็ตามข้อมูลนี้ไม่สามารถรับประกันพฤติกรรมกับภาพธรรมชาติหรือพืชที่ไม่รองรับ

ผลรายภาพ, confusion matrix และ receipt ของแต่ละรุ่นอยู่ที่ `ai_model/plant_classifier_fasttrack/artifacts/final_selection_20261030_r1/` ส่วนตารางรวมและ high-confidence errors อยู่ในโฟลเดอร์ `summary/`

## 4. Model และ Preprocessing Contract

Class order ต้องคงที่ดังนี้:

1. `chrysanthemum`
2. `marigold`
3. `money_plant`
4. `rose`
5. `snake_plant`
6. `spider_plant`

Preprocessing ที่ใช้ทั้ง Evaluation และ FastAPI:

```text
tf.io.decode_image(channels=3, expand_animations=False)
→ RGB
→ tf.cast(float32)
→ tf.image.resize(224×224, bilinear, antialias=False)
→ pixel range [0,255]
→ EfficientNet embedded rescaling
```

Runtime ตรวจ SHA-256 ก่อนโหลด ตรวจ input/output shape และโหลดโมเดลหนึ่งครั้งต่อ process ผ่าน cached service

## 5. FastAPI Integration

ไม่ได้สร้าง Endpoint หรือ Service ซ้ำ เนื่องจากของเดิมรองรับสัญญาที่ต้องการอยู่แล้ว

- `GET /api/v1/plants` คืนพืชที่รองรับ 6 ชนิด
- `POST /api/v1/analyze` รับภาพ JPG/JPEG/PNG จำนวน 1–3 ภาพ ขนาดไม่เกิน 10 MB ต่อภาพ
- Automatic request ต้องไม่ส่ง `plant_code`
- Backend ตรวจนามสกุล, MIME type, binary image, ขนาด และความสอดคล้องของชนิดไฟล์
- Plant Classifier ทำงานก่อน Disease Classifier
- Runtime threshold ที่ผ่าน corrective evaluation คือ `MIN_CONFIDENCE=0.0` และ `MIN_MARGIN=0.6936511993408203`
- หากคะแนนไม่ผ่านหรือภาพหลายภาพให้คนละ plant code ระบบคืน `manual_confirmation_required` และไม่เรียก Disease Classifier
- หากผู้ใช้ยืนยัน `plant_code` ระบบตรวจว่าค่านั้นอยู่ใน 6 ชนิดที่รองรับก่อนส่งไป Disease Classifier
- Disease Router เลือกโมเดลตาม Plant Code ไม่มีการ hardcode Rose
- หากโมเดลไม่มีหรือ SHA ไม่ตรง ระบบ fail-closed ด้วย `model_unavailable`

Active model manifest, frozen threshold config และ final metadata อ้างถึง V1 SHA เดียวกัน การ Integration รอบนี้จึงไม่แก้ Binary, Model Weights, Threshold หรือ Dataset

## 6. Automated Validation

คำสั่ง:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests -q --junitxml=backend/evaluation/final_plant_classifier_pytest.xml
```

ผลจริง: **66 passed in 25.34s**

ขอบเขตที่ครอบคลุม:

- Model loading และ SHA verification
- Class mapping และ output shape
- TensorFlow preprocessing parity
- API inference และ response contract
- Invalid/corrupt image
- Unsupported file type และ file size
- Threshold boundary และ manual confirmation
- Multiple images และ inconsistent plant guard
- Disease routing และ regression tests
- ความสอดคล้องของ Final Metadata, Active Manifest และ Frozen Threshold

หลักฐาน JUnit: `backend/evaluation/final_plant_classifier_pytest.xml`

## 7. ข้อความที่ Flutter ต้องแสดง

ก่อนถ่ายหรือเลือกรูป ควรแสดงข้อความใกล้ปุ่ม Scan:

> เพื่อผลที่เหมาะสม ให้ถ่ายใบพืชชนิดเดียวบนพื้นหลังเรียบ แสงสม่ำเสมอ และให้ใบพืชเห็นชัด ระบบรองรับเฉพาะพืช 6 ชนิดที่ระบุ และยังไม่สามารถตรวจจับพืชชนิดอื่นได้อย่างน่าเชื่อถือ

หน้าผลลัพธ์ควรระบุว่า Confidence เป็นคะแนนจากโมเดล ไม่ใช่การยืนยันทางพฤกษศาสตร์หรือห้องปฏิบัติการ และกรณีผู้ใช้ยืนยันชนิดพืชเองต้องไม่แสดง `1.0` เป็น AI Confidence 100%

## 8. ข้อมูลสำหรับบทที่ 3

ระบบใช้สถาปัตยกรรมสองขั้นตอน โดย Flutter ส่งภาพผ่าน Multipart HTTP ไปยัง FastAPI จากนั้น Backend ตรวจสอบไฟล์และแปลงภาพเป็น RGB ชนิด `float32` ขนาด 224×224 พิกเซลด้วย Bilinear Resize ก่อนส่งเข้า EfficientNet-B0 เพื่อจำแนกชนิดพืช 6 คลาส เมื่อผลผ่านเกณฑ์หรือได้รับการยืนยันจากผู้ใช้ ระบบจึงเลือก Disease Classifier ที่ตรงกับชนิดพืช การแยกขั้นตอนดังกล่าวป้องกันไม่ให้ระบบส่งภาพไปยังโมเดลโรคผิดชนิดเมื่อผลจำแนกพืชยังไม่แน่นอน

โมเดลถูกโหลดครั้งเดียวต่อ Backend process และตรวจ SHA-256, Input Shape, Output Shape และ Class Mapping ก่อน Inference ระบบรองรับภาพ JPG, JPEG และ PNG จำนวน 1–3 ภาพต่อคำขอ และใช้ Manual Confirmation เมื่อ Margin ต่ำหรือภาพในชุดถูกทำนายเป็นพืชต่างชนิด

## 9. ข้อมูลสำหรับบทที่ 4

โมเดล 6 รุ่นถูกประเมินซ้ำด้วย Standalone Script บน Controlled-domain Validation Manifest เดียวกัน 2,340 ภาพ V2 ให้ Macro-F1 สูงสุด 99.4494% ขณะที่ V1 ให้ Minimum Per-Class Recall สูงสุด 99.6056% และไม่มีความผิดพลาดที่ Confidence ตั้งแต่ 90% ขึ้นไป เมื่อพิจารณาความไม่เป็นอิสระและความไม่สมดุลของ Validation ร่วมกับความพร้อมของ Runtime Artifact และ Frozen Threshold จึงเลือก V1 เป็น Final Integration Baseline โดยไม่กล่าวอ้างว่าเป็นโมเดลที่แม่นยำที่สุดอย่างพิสูจน์แล้ว

ผลนี้อธิบายได้เฉพาะภาพใบพืชที่มีพื้นหลังควบคุม ไม่ควรนำไปสรุปความแม่นยำกับภาพธรรมชาติทั่วไปหรือพืชที่อยู่นอก 6 คลาส การประเมินแบบ blind ในอนาคตต้องใช้ชุดภาพสตูดิโออิสระที่ไม่เคยใช้เลือกโมเดลมาก่อน

## 10. สถานะปิดงาน

- Final baseline selected: PASS
- Model metadata and SHA frozen: PASS
- FastAPI integration: PASS
- Automatic/manual routing safeguards: PASS
- Automated tests: PASS
- Automatic deployment: **ไม่ได้ดำเนินการ**
- Commit/Push: **ไม่ได้ดำเนินการ**
- Natural image support claim: **ไม่อยู่ในขอบเขตและไม่กล่าวอ้าง**
