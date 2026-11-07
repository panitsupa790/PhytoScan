# PhytoScan — Final Hybrid Candidate Test

วันที่ทดสอบ: 1 พฤศจิกายน 2026 (เวลาประเทศไทย)  
สถานะ: **PASS สำหรับการเปิดใช้ในสภาพแวดล้อมทดสอบภายใน**  
Active Model: **ไม่เปลี่ยน**  
Deploy: **ไม่ได้ดำเนินการ**

## 1. Artifact และ Frozen Configuration

| รายการ | SHA-256 / ค่า | สถานะ |
|---|---|---|
| Candidate Manifest | `e0265ab9b971340467925e57b9f745b6a4f4585c5ac487f42604e7cc73ca740c` | PASS |
| Frozen Threshold Config | `b2d5def095d222c05c5b29ac94d3f734f9a74295cbffd7bb0663ed883d8d8ffd` | PASS — ไม่เปลี่ยน |
| Test Manifest | `e5306f553a0d22b3b699cc3668696d68c389227be359dc12cadef7fce62cc152` | PASS |
| Test Predictions | `942c1041eeb7ee7f61d94a77b89dacb163cb57bf191ceaa24fee00f9881d5bb6` | PASS |
| Test Report | `960cb0b762a518087a4f86d2b9fa1616c375fbe20514767c61726c1f9bb70779` | PASS |
| Confusion Matrix | `3b17f87184fe9763dadec0b36e71bda2a116578ecd89c1be025d6301f21d9c17` | PASS |
| Candidate Test Receipt | `9471fc9cda0da643723dec5fb009d93c296da44a258c3a4ad321dd206eeb026e` | PASS |

Frozen threshold ที่ใช้ตลอดการทดสอบ:

- `MIN_CONFIDENCE = 0.0`
- `MIN_MARGIN = 0.34551629424095154`
- ไม่มีการสร้าง candidate threshold จาก Test
- ไม่มีการปรับ threshold หรือเลือก model จากผล Test

## 2. Candidate Model SHA-256

| งาน | Architecture | SHA-256 | สถานะ |
|---|---|---|---|
| Plant Classifier | MobileNetV2 | `fa53ab449421b12c9b3244d380ecd68633514d5752d1b4167772b0453abdfad4` | PASS |
| Chrysanthemum | MobileNetV2 | `ee2ac31fe0cd31b2cb744de7ce6857fafabcfee4d03350fa05ed66eb8c2aebd9` | PASS |
| Marigold | EfficientNet-B0 | `68b4ea44f8a6abdfc74f5e46b6aa6432857d4aac89e5c55f0afa61b2aee68635` | PASS |
| Money Plant | MobileNetV2 | `b4eb4ea4ceb5c9234f753531454af61bc499f81da896bbaa100879afe5cbcdc5` | PASS |
| Rose | MobileNetV2 | `8269c31fa441d73a22a663b9fc09f344e19b70537976ddcdeada77ecba3217fe` | PASS |
| Snake Plant | MobileNetV2 | `1774220b74719c7ddf39c2a61b5b0157308a6e499be35430008105cce9004729` | PASS |
| Spider Plant | MobileNetV2 | `e32f7439ca2107218fae46a54ef4646b23585b36ea027803c846babc041a2622` | PASS |

## 3. Raw Plant Classification Metrics

จำนวน Test: 1,580 ภาพ

| Metric | ผล |
|---|---:|
| Correct | 1,578/1,580 |
| Accuracy | 99.8734% |
| Macro Precision | 99.4444% |
| Macro Recall | 99.9716% |
| Macro F1-score | 99.7033% |
| Minimum Per-Class Recall | 99.8295% |

## 4. ผลรายคลาส

| True Class | Test Images | Correct | Precision | Recall | F1 | Threshold Coverage |
|---|---:|---:|---:|---:|---:|---:|
| chrysanthemum | 161 | 161 | 100.0000% | 100.0000% | 100.0000% | 161/161 (100.0000%) |
| marigold | 73 | 73 | 100.0000% | 100.0000% | 100.0000% | 73/73 (100.0000%) |
| money_plant | 49 | 49 | 100.0000% | 100.0000% | 100.0000% | 48/49 (97.9592%) |
| rose | 1,173 | 1,171 | 100.0000% | 99.8295% | 99.9147% | 1,171/1,173 (99.8295%) |
| snake_plant | 58 | 58 | 96.6667% | 100.0000% | 98.3051% | 58/58 (100.0000%) |
| spider_plant | 66 | 66 | 100.0000% | 100.0000% | 100.0000% | 66/66 (100.0000%) |

Confusion Matrix พบความผิดพลาด 2 ภาพ โดยภาพ Rose ถูกทำนายเป็น Snake Plant 2 ภาพ คลาสอื่นทำนายถูกทั้งหมด

## 5. Frozen Threshold Chain Metrics

| Metric | ผล |
|---|---:|
| Coverage | 1,577/1,580 (99.8101%) |
| Accepted Accuracy | 1,576/1,577 (99.9366%) |
| Accepted Errors | 1 |
| Accepted Error Rate | 1/1,577 (0.0634%) |
| Correct Rejections | 1/2 incorrect predictions (50.0000%) |
| Wrongful Rejections | 2/1,578 correct predictions (0.1267%) |
| FAR among incorrect predictions | 1/2 (50.0000%) |

ผลรายภาพที่เกี่ยวกับ threshold:

1. Rose Insect Damage → Snake Plant, margin `0.4948688`: ทำนายผิดและ **Accepted**
2. Rose Healthy → Snake Plant, margin `0.2357765`: ทำนายผิดและ **Rejected**
3. Rose Black Spot → Rose, margin `0.2020243`: ทำนายถูกแต่ **Rejected**
4. Money Plant Bacterial Wilt → Money Plant, margin `0.0835883`: ทำนายถูกแต่ **Rejected**

ผลนี้ถูกรายงานตามจริงและไม่ได้ใช้ลดหรือเพิ่ม threshold

## 6. Regression กับ Jupyter เดิม

| รายการ | Jupyter เดิม | Final Candidate Test | ความแตกต่าง |
|---|---:|---:|---:|
| Rows | 1,580 | 1,580 | 0 |
| Correct | 1,578 | 1,578 | 0 |
| Accuracy | 99.8734% | 99.8734% | 0 |
| Macro F1 | 99.7033% | 99.7033% | 0 |
| Minimum Recall | 99.8295% | 99.8295% | 0 |
| Row-level predicted labels | — | — | **0 disagreements** |

Test paths, labels และ class mapping ตรงกันทั้งหมด ผล Jupyter เดิมไม่ได้ถูกใช้เลือก threshold หรือ model ในรอบนี้

## 7. Runtime และ Receipt Verification

- TensorFlow: `2.21.0`
- Keras: `3.15.1`
- NumPy: `2.5.3`
- Inference precision: `float32`
- Candidate receipt enforcement (`PLANT_THRESHOLD_REQUIRE_TEST_RECEIPT=true`): PASS
- Receipt/model/config/artifact SHA binding: PASS
- Backend automated tests: `81 passed`
- Candidate receipt/runtime smoke tests: `8 passed`

## 8. Rollback Verification

ทดสอบการสลับด้วย environment override โดยไม่แก้ manifest:

1. Candidate mode โหลด Plant MobileNetV2 SHA `fa53...` และ threshold margin `0.3455162` สำเร็จ
2. ลบ candidate environment overrides แล้วเริ่ม process ใหม่
3. ระบบกลับไป Active EfficientNet-B0 SHA `5585...` และ threshold margin `0.6936512` สำเร็จ
4. Disease models ทั้ง 6 ตัวกลับเป็น EfficientNet-B0 ตาม active manifest

ผล: **PASS** — rollback ทำได้โดยไม่แก้หรือเขียนทับ active manifest/model

## 9. ข้อจำกัด

- Unsupported/OOD Detection: **NOT VERIFIED**
- Test Set นี้ไม่ใช่ External Mobile Test
- Validation มีข้อผิดพลาดน้อยมาก จึงไม่รับประกัน zero-error ในการใช้งานจริง
- Threshold ยังรับ prediction ที่ผิด 1 ภาพ จึงต้องคง Manual Confirmation และคำเตือนผลวิเคราะห์เบื้องต้น
- ยังไม่มีการ Deploy และไม่มีการเปลี่ยน Active Model

## Final Decision

| Scope | Decision |
|---|---|
| Artifact integrity | PASS |
| Frozen threshold compliance | PASS |
| Final Test evaluation | PASS |
| Jupyter regression parity | PASS |
| Receipt enforcement | PASS |
| Rollback | PASS |
| Unsupported/OOD | NOT VERIFIED |
| เปิดใช้ Candidate ในสภาพแวดล้อมทดสอบภายใน | **PASS** |
| Production deployment | **NOT PERFORMED / ต้องได้รับอนุมัติแยก** |

Candidate ผ่านเกณฑ์สำหรับเปิดใช้ในสภาพแวดล้อมทดสอบภายใน โดยต้องใช้ Candidate Manifest, Frozen Threshold และ Candidate Test Receipt ชุดนี้ร่วมกัน ห้ามปรับ threshold จากผล Test รอบนี้
