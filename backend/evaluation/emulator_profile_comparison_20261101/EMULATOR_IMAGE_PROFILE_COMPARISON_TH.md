# PhytoScan — Emulator Image Comparison: EfficientNet vs Hybrid

วันที่ทดสอบ: 1 พฤศจิกายน 2026  
แหล่งภาพ: `/sdcard/Download` ของ Android Emulator `emulator-5554`  
ขอบเขต: ทดสอบแบบ read-only โดยไม่แก้โมเดล, threshold, active manifest หรือ deploy

## ขอบเขตข้อมูล

- พบและทดสอบไฟล์ภาพ 25 ไฟล์ (JPEG/PNG)
- มีเนื้อหาภาพไม่ซ้ำ 24 ภาพ เพราะ `Leaf Spot Disease Image 90.jpg` และ `.png` มี SHA-256 เดียวกัน
- ไม่มี Ground-truth Manifest กำกับภาพทั้งชุด จึง **ไม่รายงาน Accuracy** ของชุดนี้
- ผลนี้เป็น External/Diagnostic Test จากภาพที่อยู่ใน Emulator ไม่ใช่ Frozen Validation/Test

## Profile ที่ทดสอบ

| Profile | Plant Classifier | SHA-256 | MIN_MARGIN |
|---|---|---|---:|
| EfficientNet เดิม | EfficientNet-B0 V1 | `5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165` | 0.6936511993408203 |
| Hybrid Candidate | MobileNetV2 | `fa53ab449421b12c9b3244d380ecd68633514d5752d1b4167772b0453abdfad4` | 0.34551629424095154 |

ทั้งสอง profile ใช้ `MIN_CONFIDENCE=0.0` และ threshold/config ที่ freeze ไว้ของตัวเอง ไม่มีการปรับค่าจากภาพชุดนี้

## ผลรวม

| รายการ | EfficientNet เดิม | Hybrid Candidate |
|---|---:|---:|
| ภาพทั้งหมด | 25 | 25 |
| วิเคราะห์ต่อถึง Disease Classifier | 23 | 22 |
| ขอให้ผู้ใช้ยืนยันชนิดพืช | 2 | 3 |
| ทำนาย Plant ตรงกันระหว่างสอง profile | 21/25 (84%) | 21/25 (84%) |
| ให้ decision ตรงกัน | 22/25 (88%) | 22/25 (88%) |

สำหรับ 20 ภาพที่ทั้งสอง profile ระบุ Plant ตรงกันและผ่าน threshold ทั้งคู่:

- Disease Result ตรงกัน 13/20 ภาพ (65%)
- Disease Result ต่างกัน 7/20 ภาพ (35%)

## ภาพที่ Plant Classifier ให้ผลต่างกัน

| ไฟล์ | ตรวจภาพเบื้องต้น | EfficientNet เดิม | Hybrid Candidate | ข้อสังเกต |
|---|---|---|---|---|
| `0454038-SMPT.jpg` | รูปทรงใบสอดคล้องกับเบญจมาศ แต่ยังไม่มี label manifest ยืนยัน | chrysanthemum, margin 0.5566, ขอให้ยืนยัน | rose, margin 0.3448, ขอให้ยืนยัน | ทั้งคู่ fail-closed; EfficientNet สมเหตุสมผลกว่าจากภาพ |
| `images (4).jpg` | ลิ้นมังกรชัดเจน | rose, margin 0.9490, วิเคราะห์ต่อ | snake_plant, margin 0.0709, ขอให้ยืนยัน | Hybrid ได้ Top-1 ถูกกว่าและไม่ส่งต่ออัตโนมัติ; EfficientNet ผิดด้วย margin สูง |
| `images (7).jpg` | พลูด่างชัดเจน | rose, margin 0.3556, ขอให้ยืนยัน | money_plant, margin 0.9949, วิเคราะห์ต่อ | Hybrid ถูกกว่าอย่างชัดเจน |
| `Leaf Spot Disease Image 91.jpg` | ภาพใบเดี่ยว ไม่สามารถยืนยันชนิดจากภาพ/ชื่อไฟล์ได้ | rose, margin 0.6937, วิเคราะห์ต่อ | chrysanthemum, margin 0.5249, วิเคราะห์ต่อ | Ground truth NOT VERIFIED |

## กรณีผิดที่สำคัญ

1. `mgoldleaves4web.jpg` — ผู้ใช้เคยยืนยันว่าเป็นดาวเรือง แต่ทั้งสอง profile ทำนายเป็น `rose` ด้วย margin ประมาณ 0.9999 และส่งต่อ Disease Router อัตโนมัติ
   - EfficientNet disease result: `Rose_Mosaic_Virus`
   - Hybrid disease result: `Rose_Rust`
2. `dfd5825ed82df3808f47b9586e0530aa.png` — จากการตรวจภาพมีลักษณะเป็นลิ้นมังกร แต่ทั้งสอง profile ทำนายเป็น `marigold` และส่งต่อเป็น `Helathy Leaves`; ยังไม่มี label manifest จึงจัดเป็น visual-review finding ไม่ใช่ formal ground truth

สองกรณีนี้แสดงว่า threshold ไม่สามารถป้องกัน confident misclassification ได้ทุกภาพ และ Unsupported/OOD Detection ยังคง **NOT VERIFIED**

## ข้อสรุป

- Hybrid ไม่ได้แย่กว่าในทุกภาพ: แก้กรณีลิ้นมังกรและพลูด่างที่ EfficientNet ทำนายเป็น Rose ได้ในภาพที่ตรวจชัดเจน
- EfficientNet สมเหตุสมผลกว่าในภาพใบเบญจมาศ `0454038-SMPT.jpg`
- ทั้งสองแบบยังล้มเหลวกับภาพดาวเรืองกรณีเดิม และยังมีภาพลิ้นมังกรอีกแบบที่ถูกทำนายเป็นดาวเรือง
- จาก 25 ไฟล์นี้ยังตัดสินไม่ได้ว่า profile ใดแม่นกว่ารวม เพราะไม่มี Ground-truth Manifest ครบทุกภาพ
- ไม่ควรปรับ threshold จากผลชุดนี้ ควรเพิ่ม label จริงให้ทั้ง 24 ภาพไม่ซ้ำ แล้วคำนวณ paired accuracy/confusion matrix จึงจะเลือก profile ได้อย่างเป็นธรรม

## Artifacts

| ไฟล์ | SHA-256 |
|---|---|
| `efficientnet_predictions.csv` | `5e47990d023cfd3e3a1aa362b8c000e4c204dc60704ad5ae489e3de8305b228e` |
| `hybrid_predictions.csv` | `5de61f0fdc773116efa6b85c0a8edb86552c78f166e5e7b6cee2d686fd16f616` |
| `profile_comparison.csv` | `0164d8c74a0735a3a35c205232bfd28e8dab8ac2cc496272c6bf80625c6b9f8b` |

หมายเหตุ: การทดสอบใช้ไฟล์ต้นฉบับที่ดึงจาก Emulator ผ่าน ADB และรันผ่าน preprocessing, plant threshold chain และ disease routing จริงของ Backend แต่ไม่ได้กดเลือกภาพทีละไฟล์ผ่าน Flutter UI
