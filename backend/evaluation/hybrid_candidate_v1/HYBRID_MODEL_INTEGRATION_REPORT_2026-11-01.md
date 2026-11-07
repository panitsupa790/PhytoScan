# PhytoScan Hybrid Model Integration — Candidate/Staging Report

วันที่ตรวจสอบ: 1 พฤศจิกายน 2026  
สถานะรวม: **PASS สำหรับ Candidate/Staging, NOT ACTIVATED, BLOCKED สำหรับ Production Activation**

## 1. ขอบเขตและสถานะ

- สร้าง candidate bundle แยกจาก active bundle สำเร็จ
- ไม่แก้ `backend/app/data/model_manifest.json` และไม่เปลี่ยน active model
- ไม่แก้ Flutter, API schema, dataset, checkpoint ต้นฉบับ หรือ threshold เดิม
- ไม่ Train/Fine-tune และไม่เปิด Test 1,580 ภาพซ้ำใน workflow นี้
- Automatic routing ของ candidate เปิดได้เฉพาะเมื่อเลือก candidate manifest และ frozen candidate threshold ผ่าน environment โดยชัดแจ้ง

## 2. Candidate Model Bundle

| งาน | Architecture | Checkpoint SHA-256 | Classes | สถานะ |
|---|---|---|---:|---|
| Plant Classifier | MobileNetV2 | `fa53ab449421b12c9b3244d380ecd68633514d5752d1b4167772b0453abdfad4` | 6 | PASS |
| Chrysanthemum Disease | MobileNetV2 | `ee2ac31fe0cd31b2cb744de7ce6857fafabcfee4d03350fa05ed66eb8c2aebd9` | 3 | PASS |
| Marigold Disease | EfficientNet-B0 เดิม | `68b4ea44f8a6abdfc74f5e46b6aa6432857d4aac89e5c55f0afa61b2aee68635` | 3 | PASS |
| Money Plant Disease | MobileNetV2 | `b4eb4ea4ceb5c9234f753531454af61bc499f81da896bbaa100879afe5cbcdc5` | 3 | PASS |
| Rose Disease | MobileNetV2 | `8269c31fa441d73a22a663b9fc09f344e19b70537976ddcdeada77ecba3217fe` | 8 | PASS |
| Snake Plant Disease | MobileNetV2 | `1774220b74719c7ddf39c2a61b5b0157308a6e499be35430008105cce9004729` | 3 | PASS |
| Spider Plant Disease | MobileNetV2 | `e32f7439ca2107218fae46a54ef4646b23585b36ea027803c846babc041a2622` | 3 | PASS |

ไฟล์ MobileNetV2 ทั้ง 6 ไฟล์มี SHA-256 ตรงกันระหว่าง `export_manifest.json`, export files และ source checkpoints ใน WSL ส่วน Marigold ใช้ binary active เดิมโดยไม่สร้างสำเนาเพิ่ม

ทุกโมเดลโหลดด้วย TensorFlow `2.21.0` / Keras `3.15.1` ได้จริง มี input `(None, 224, 224, 3)` และ output ตรง class mapping ใน Disease Metadata ทั้ง 23 คลาส ไม่มี Sunflower

## 3. Preprocessing Contract

- Runtime decode: TensorFlow RGB, `expand_animations=False`
- Resize: bilinear 224×224, `antialias=False`
- Runtime tensor: `float32`, ช่วง `[0,255]`
- ไม่มี external normalization
- MobileNetV2 ใช้ชื่อ contract `mobilenet_v2_embedded_minus1_1_from_0_255` และตรวจพบ `Rescaling(1/127.5, offset=-1)` ภายใน checkpoint จริง
- Marigold EfficientNet-B0 ใช้ `efficientnet_embedded_rescaling_from_0_255`
- ทดสอบแล้วว่า runtime ไม่ normalize ซ้ำ

## 4. Frozen Plant Threshold จาก Validation เท่านั้น

- Validation manifest: 2,340 ภาพ, ครบ 6 คลาส
- Validation manifest SHA-256: `8d0121c11c9845fedc276caa3139f820d07da03cec5694d42379728b1f296860`
- Exact observed-boundary search และ conservative selection เดิม
- `MIN_CONFIDENCE = 0.0`
- `MIN_MARGIN = 0.34551629424095154`
- Frozen config SHA-256: `b2d5def095d222c05c5b29ac94d3f734f9a74295cbffd7bb0663ed883d8d8ffd`
- Test data opened by this workflow: **False**

| True Plant | Total | Accepted | Coverage | Accepted Accuracy | Accepted Errors | Correct Rejections | Wrongful Rejections |
|---|---:|---:|---:|---:|---:|---:|---:|
| chrysanthemum | 233 | 233 | 100.0000% | 100.0000% | 0 | 0 | 0 |
| marigold | 73 | 73 | 100.0000% | 100.0000% | 0 | 0 | 0 |
| money_plant | 74 | 73 | 98.6486% | 100.0000% | 0 | 0 | 1 |
| rose | 1,775 | 1,774 | 99.9437% | 100.0000% | 0 | 1 | 0 |
| snake_plant | 86 | 86 | 100.0000% | 100.0000% | 0 | 0 | 0 |
| spider_plant | 99 | 99 | 100.0000% | 100.0000% | 0 | 0 | 0 |
| **Overall** | **2,340** | **2,338** | **99.9145%** | **100.0000%** | **0** | **1** | **1** |

Validation มี prediction ผิดเพียง 1 ภาพ จึงไม่สามารถรับประกัน zero-error ในการใช้งานจริง และ threshold นี้ไม่ใช่ Unsupported/OOD detector

## 5. Regression Evidence เดิม (ไม่ได้ใช้เลือก Threshold)

รายงานเดิม `comparison_reports/20261101_035921_262354` มี 1,580 แถว:

| Model | Correct | Accuracy | Macro F1 | Minimum Recall |
|---|---:|---:|---:|---:|
| EfficientNet-B0 V1 | 1,573/1,580 | 99.5570% | 98.8893% | 98.4848% |
| MobileNetV2 | 1,578/1,580 | 99.8734% | 99.7033% | 99.8295% |

ใช้เป็น regression evidence เท่านั้น เนื่องจาก Test ถูกเปิดแล้วและ row-level report ไม่มี cryptographic receipt ที่ผูก predictions เข้ากับ checkpoint ขณะ inference อย่างสมบูรณ์ ห้ามใช้ผลนี้ปรับ threshold

## 6. Runtime/API Verification

- Candidate bundle verification: PASS ทั้ง 7 โมเดล
- Automatic route จริง: PASS ทั้ง 6 พืช
- Marigold route ไป EfficientNet-B0: PASS
- อีก 5 disease routes ไป MobileNetV2: PASS
- 3 ภาพชนิดเดียวกัน: PASS
- ภาพต่างชนิด: PASS แบบ fail-closed เป็น `manual_confirmation_required`
- Manual confirmation: PASS
- Disease Metadata mapping: PASS ครบ 23 classes
- API contract และ 1–3 image behavior: ไม่เปลี่ยน
- Active default test suite: `81 passed`
- Candidate-targeted suite: `49 passed`

## 7. Activation และ Rollback

Candidate staging สามารถเปิดแบบ explicit process configuration เท่านั้น:

```text
MODEL_MANIFEST=app/data/model_manifest.hybrid_candidate.json
PLANT_THRESHOLD_CONFIG=app/data/plant_classifier_threshold.hybrid_candidate.json
PLANT_THRESHOLD_REQUIRE_TEST_RECEIPT=false
```

ค่านี้ใช้สำหรับ staging ก่อน Test receipt เท่านั้น ห้ามใช้เป็น production configuration

ก่อน production activation ต้อง:

1. ได้รับอนุมัติแยกต่างหาก
2. ประเมิน Test หนึ่งครั้งหลัง frozen config โดยไม่ปรับ threshold
3. สร้างและตรวจ candidate Test receipt ที่ผูก config/model/artifact SHA-256
4. เปลี่ยน `PLANT_THRESHOLD_REQUIRE_TEST_RECEIPT=true`
5. ทำ deployment smoke test และบันทึก deployment revision

Rollback: ลบ environment override ทั้งสามตัวแล้ว restart process ระบบจะกลับไปใช้ active EfficientNet bundle และ corrective threshold เดิมทันที เพราะ active manifest/checkpoints ไม่ถูกแก้

## 8. ข้อจำกัด/ประเด็นก่อน Deploy

- Candidate ยังไม่มี corrective/final Test receipt จึงยังไม่อนุญาต production activation
- ไม่มี Unsupported/OOD dataset และห้ามอ้างว่าระบบตรวจพืชที่ไม่รองรับได้
- ผลเดิม 1,580 ภาพเป็นชุดที่เปิดแล้ว ใช้ได้เพียง regression evidence
- Chrysanthemum export ไม่มี standalone `model_selection.json`; Rose มี config ระบุ `val_loss` แต่ไม่มี standalone selection record จึงมี selection provenance ไม่สมบูรณ์เท่า Plant/Money/Snake/Spider
- Validation/Test เดิมไม่ใช่หลักฐาน external mobile generalization
- Binary `.keras` ถูก ignore จาก Git จึงต้องจัดส่ง candidate model artifacts ผ่าน deployment artifact storage พร้อมตรวจ SHA-256 ทุกครั้ง

## Final Decision

**Candidate/Staging: PASS**  
**Active model changed: NO**  
**Production activation/deploy: BLOCKED จนกว่าจะมี explicit approval และ candidate Test receipt**
