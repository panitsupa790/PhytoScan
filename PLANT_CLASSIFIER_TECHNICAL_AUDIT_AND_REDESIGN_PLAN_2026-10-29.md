# PhytoScan — Plant Classifier Technical Audit & Redesign Plan

วันที่ตรวจสอบ: 29 ตุลาคม 2026  
ขอบเขต: Audit และ Planning เท่านั้น  
แหล่งที่ตรวจ: `/home/mind_hp/phytoscan/phytoscan`, checkpoint V1–V5, manifests, config, training history, Notebook outputs และ Backend runtime contract  

> ไม่มีการแก้ Source Code, Dataset, Manifest หรือ Checkpoint และไม่มีการฝึกโมเดลหรือใช้ Legacy Test เพื่อเลือกโมเดล

## 1. Executive Diagnosis

### ข้อวินิจฉัยหลัก

| ลำดับ | ข้อวินิจฉัย | ระดับความมั่นใจ | หลักฐานสำคัญ |
|---|---|---:|---|
| P0 | ปัญหาหลักคือ data-domain/source shortcut และ natural-image coverage ไม่เพียงพอ ไม่ใช่ขนาดของ EfficientNet-B0 เพียงอย่างเดียว | สูง | Marigold train มี corner brightness เฉลี่ย `0.09` เทียบกับคลาสอื่นประมาณ `155–173`; V5 มี natural train เพียง 97 ภาพ และ natural rose เพียง 3 ภาพ |
| P0 | Evaluation ปัจจุบันยังใช้ตัดสิน production/promotion ไม่ได้ | สูง | External validation มีเพียง 20 ภาพ, ไม่มี Rose, 3 ภาพไม่เห็น target plant ชัด และถูกใช้เลือก V3–V5 ซ้ำ |
| P0 | V4 External metric ใน Notebook ไม่ reproducible จาก checkpoint ปัจจุบัน | สูง | Notebook output ระบุ 12/20 แต่ direct checkpoint inference ได้ 11/20; `pred_v4` ถูกใช้โดยไม่มี cell ปัจจุบันที่สร้างตัวแปรนี้ |
| P0 | V2→V5 สืบทอด representation และ shortcut เดิมต่อเนื่อง | สูง | V3 ต่อจาก V2, V4 ต่อจาก V2, V5 ต่อจาก V4; V2–V5 มี architecture/head/augmentation เดียวกันและ trainable parameters เท่ากัน |
| P1 | Training/Runtime preprocessing ตรงกัน | สูง | ทุกเวอร์ชันใช้ RGB decode → float32 → bilinear 224×224 → pixel range 0–255, `antialias=False` |
| P1 | Exact leakage ที่ตรวจด้วย path/SHA/group ไม่พบ แต่ยังมี near-duplicate และ group-semantic risks | สูงสำหรับ exact, ปานกลางสำหรับ near-duplicate | V1 path/group overlap = 0; registry SHA overlap = 0; แต่พบ pHash near-match 11 คู่จาก V2 train ไป Legacy valid/test และ cross-split external near-match 1 คู่ |
| P1 | Architecture change อย่างเดียวไม่น่าทำให้ real-image accuracy ดีขึ้นอย่างยั่งยืน | สูง | V4/V5 Legacy >99% แต่ External เพียง 55–60%; V5 เพิ่ม natural marigold แล้ว known failure ยังผิดเป็น Rose |

### คำตัดสินสั้น

1. **ยังไม่ควร fine-tune ต่อจาก V5** เพราะจะสืบทอด shortcut และใช้ development set ที่ถูกเปิดดูซ้ำแล้ว
2. **ยังไม่ควรเปลี่ยน architecture แล้วคาดหวังว่าปัญหาจะหายเอง** ต้องแก้ data/evaluation protocol ก่อน
3. แนวทางที่เหมาะสมคือสร้าง **fresh ImageNet baseline** ด้วย EfficientNet-B0 ภายใต้ split ใหม่ แล้วใช้ EfficientNetV2-B0 เป็น challenger แบบควบคุมตัวแปร
4. MobileNetV3 ควรทดสอบเมื่อมีข้อกำหนด on-device จริงเท่านั้น เพราะ Runtime ปัจจุบันประมวลผลบน FastAPI Backend

## 2. Evidence Table

| Evidence | File / Location | Code / Data reference | Finding |
|---|---|---|---|
| Class order | `models/plant_classifier_v1/dataset_config.json` | `plant_class_names`, `class_to_idx` | ลำดับ 6 คลาสตรงตามข้อกำหนด |
| V1 split counts | `models/plant_classifier_v1/{train,valid,test}_split.csv` | CSV rows | Train 3,599; Valid 2,340; Test 1,580 |
| Background shortcut | `plant_classifier.ipynb` | Cell 4, lines 10–47; saved output | Marigold corner brightness `0.09`; คลาสอื่น `155.64–172.95` |
| Background sensitivity | `plant_classifier.ipynb` | Cell 5, lines 48–117 | เปลี่ยนเฉพาะมุมภาพทำ prediction บางคลาสเปลี่ยน; เป็นสัญญาณ shortcut แต่ยังไม่ใช่ segmentation experiment |
| V2 architecture | `plant_classifier.ipynb` | Cell 54, lines 37–70 | ImageNet EfficientNet-B0 + GAP + Dropout 0.30 + 6-way softmax |
| V2 fine-tuning | `plant_classifier.ipynb` | Cell 56, lines 67–100 | เปิดท้าย backbone 40 layers, freeze BatchNorm, Adam `1e-5` |
| V2 data config | `models/plant_classifier_v2/configs/plant_classifier_v2_training.json` | `training`, `augmentation` | Batch 32; head LR `1e-3`; fine-tune LR `1e-5`; ไม่ใช้ class weights |
| Input parity | `plant_classifier.ipynb` | Cell 53 lines 36–55; Cell 95 lines 24–42; Cell 152 lines 29–44 | Train V2/V3/V5 ใช้ preprocessing เดียวกับ Backend runtime |
| V3 source sampling | `plant_classifier.ipynb` | Cell 95, lines 9–15, 67–74 | Legacy 5,377 + natural 84; natural sampling 20% |
| V4 source sampling | `plant_classifier.ipynb` | Cell 111, lines 14–27 | Legacy 90% / natural 10% |
| V5 source sampling | `plant_classifier.ipynb` | Cell 152, lines 14–26, 78–84 | Legacy 5,377 + natural 97; 90/10 sampler |
| V5 training | `plant_classifier.ipynb` | Cell 153, lines 41–65, 85–90 | Adam `1e-5`, categorical CE, max 20 epochs, patience 6; best epoch 1 |
| V5 overfit signal | `models/plant_classifier_v5/.../training_history.csv` | Epoch 1–7 | Train accuracy 98.91%→99.98%; val lossดีที่สุด epoch 1 และแย่ลงหลังจากนั้น |
| External coverage | `models/plant_classifier_v3/manifests/external_development_split_v3.csv` | `v3_split=dev_valid` | 20 ภาพ: chrys 3, marigold 2, money 5, rose 0, snake 6, spider 4 |
| External quality | `models/plant_classifier_v3/manifests/external_validation_quality_review.csv` | 3 flagged rows | 3/20 ระบุ target not visible, not single clear target และ leaf insufficient |
| V4/V5 stored result | `plant_classifier.ipynb` | Cell 154 stored HTML output | V4 12/20, Macro-F1 0.4015; V5 12/20, Macro-F1 0.4631 |
| V4 reproducibility failure | `plant_classifier.ipynb` | Cell 154 line 7 uses `pred_v4`; no defining cell in current notebook | Direct current checkpoint = 11/20, Macro-F1 0.3687; stored 12/20 cannot be traced to current source state |
| V5 direct verification | V5 checkpoint + external dev manifest | inference-only audit | 12/20, Macro-F1 0.4631; matches stored output |
| Known failures | `models/plant_classifier_v2/data/known_failures/` | Cell 160 stored output | Marigold: V4 Rose 66.71%, V5 Rose 75.59%; Snake Plant correctทั้งคู่ |
| Marigold gap | `models/plant_classifier_v5/reports/v5_marigold_dataset_gap.csv` | 5 rows | Natural marigold เดิม 9 ภาพ; natural diseased verified = 0 |
| V5 manual additions | `v5_marigold_final_decisions.csv` | `manual_decision`, `final_status` | 13 approved, 1 rejected; แต่ `final_approval=False` ทั้ง 14 แถว เป็น schema inconsistency |
| Exact leakage checks | V1 manifests, V2 hash registry, V3 source groups | recomputed read-only | Path/SHA/group/observer overlap ของ split ที่ตรวจ = 0 |
| Near-duplicate risk | `models/plant_classifier_v2/evaluation/*.csv` | pHash distance ≤4 records | V2 train↔Legacy eval 11 matches; external dev train↔valid 1 cross-class match; ต้อง visual adjudication |
| License metadata | `external_development_split_v3.csv` | `photo_license` | iNaturalist: CC-BY 77, CC0 27 |
| Missing governance docs | classifier V1–V5 directories | file inventory | ไม่พบ dedicated LICENSE/CITATION/ATTRIBUTION สำหรับ Mendeley/legacy sources — **Not Verified** |
| WSL provenance | `/home/mind_hp/phytoscan/phytoscan` | directory inspection | directory นี้ไม่มี `.git`; source revision ของ Notebook/checkpoints จึงระบุ commit ไม่ได้ |

### Artifact hashes ที่ยืนยันใน audit

| Artifact | SHA-256 |
|---|---|
| V1 model | `5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165` |
| V4 model | `efc090d7cb543b717cd842eb5a4dc7fb4f5cc75e1c51847ad3d72beadcff457d` |
| V5 model | `006ab06399c50aae26d3b53aab2cc20c7e338ff2c33fc9f7a50a965507ff798e` |
| V5 train manifest | `b73c5f04c2dd1ec40a0c40619ff82e5c790c61a465cf2bfc665c81242dfef253` |
| External development V3 manifest | `af42cd7802aa0f329008261a6730f3dbb3458be0656a6ad4237b4ee8088a7244` |
| Legacy validation manifest | `8d0121c11c9845fedc276caa3139f820d07da03cec5694d42379728b1f296860` |
| Legacy test manifest | `e5306f553a0d22b3b699cc3668696d68c389227be359dc12cadef7fce62cc152` |

## 3. Dataset Health Assessment

### Counts

| Plant | V1 Train | V1 Valid | V1 Test | V5 Train | V5 Natural subset |
|---|---:|---:|---:|---:|---:|
| chrysanthemum | 977 | 233 | 161 | 1,871 | 11 |
| marigold | 338 | 73 | 73 | 577 | 22 |
| money_plant | 365 | 74 | 49 | 542 | 22 |
| rose | 1,001 | 1,775 | 1,173 | 1,228 | 3 |
| snake_plant | 427 | 86 | 58 | 592 | 22 |
| spider_plant | 491 | 99 | 66 | 664 | 17 |

### จุดแข็ง

- V1 path และ `group_id` แยก Train/Validation/Test โดยไม่ overlap ตาม manifest
- V2 hash registry 9,520 records ไม่พบ exact SHA duplicate ข้าม source ที่ลงทะเบียน
- V3 external split แยก observer/source group ระหว่าง dev_train/dev_valid ได้ 0 overlap
- iNaturalist 104 ภาพผ่าน manual review และมี `photo_license`
- V5 Marigold มี exact/near duplicate audit และ observer audit ก่อนเพิ่ม 13 ภาพ
- Class order และ label mapping คงที่ตลอด V1–V5

### จุดอ่อนและ Leakage Risks

1. **Background/source confounding สูง**  
   Marigold legacy มีพื้นหลังดำ/ขาวเกือบทั้งหมด และ corner brightness แตกต่างจากทุกคลาสอย่างสุดขั้ว โมเดลจึงมีช่องทางเรียนรู้ background แทน morphology

2. **Natural data ต่ำมากเมื่อเทียบกับ Legacy**  
   V5 มี natural 97/5,474 ภาพจริง แต่ sampler ดึง natural 10% ทำให้ภาพ natural แต่ละภาพถูกใช้โดยคาดหมายประมาณ 5.67 ครั้งต่อ epoch ขณะที่เพิ่มความเสี่ยง memorization

3. **Sampler ไม่ได้ทำ class balance**  
   Expected sample mix ต่อ epoch ยังเป็น chrysanthemum 32.27%, rose 20.81%, marigold 11.56%, money 10.97%, snake 11.81%, spider 12.58%

4. **External validation ไม่ครบ 6 คลาส**  
   ไม่มี Rose และ Marigold มีเพียง 2 ภาพ ทำให้ Macro-F1/Recall ผันผวนสูงและใช้ตัดสิน promotion ไม่ได้

5. **External validation มี quality-invalid samples 3/20**  
   ตัวอย่างเหล่านี้ควรอยู่ใน quality-gate challenge set ไม่ควรปะปนกับ species-classification score โดยไม่มี protocol แยก

6. **Development set ถูกใช้ซ้ำหลายรอบ**  
   ชุด 20 ภาพถูกใช้เลือก/เปรียบเทียบ V3, V4, V5 จึงไม่ใช่ blind evaluation อีกต่อไป

7. **Legacy validation/test ไม่ใช่หลักฐาน real-world generalization**  
   แหล่งภาพและ background ใกล้ training และมี rose ครอง 75% ของ Validation/Test; accuracy รวมจึงถูกครอบงำด้วย Rose

8. **Near-duplicate risk ยังไม่ปิด**  
   พบ V2 training candidates ใกล้ Legacy valid/test ตาม pHash 11 คู่ และ external train/valid 1 คู่ ค่านี้เป็น candidate ไม่ใช่หลักฐาน leakage จนกว่าจะ visual review

9. **Label audit ยังไม่ครบ**  
   Indoor external candidates 576 ภาพมีสถานะ `sample_reviewed_pending_full_label_audit`; 454 ภาพถูกนำเข้า V2 train แล้ว

10. **Observer/plant/session semantics บางแหล่งยัง Not Verified**  
    โดยเฉพาะ Chrysanthemum tree semantics และ legacy datasets ที่ไม่มี observer/session metadata ครบ

11. **Natural diseased-leaf coverage ไม่พอ**  
    Marigold มี natural diseased verified = 0; coverage ของโรค/แมลงใน natural scene สำหรับอีก 5 คลาสยัง **Not Verified**

12. **License/Attribution governance ยังไม่ครบ**  
    iNaturalist มี license per image แต่ไม่พบ consolidated attribution export; Mendeley/legacy license และ citation ไม่ถูกบันทึกเป็น artifact เฉพาะ

### คำตอบเรื่อง Dataset เพียงพอหรือไม่

จำนวน Legacy เพียงพอสำหรับสร้าง baseline แต่ **ยังไม่เพียงพอสำหรับอ้าง real-world/mobile generalization** เพราะ diversity, domain balance, diseased natural leaves, group metadata และ locked external test ยังไม่ครบ

## 4. Training Pipeline Assessment

### Architecture และ Head

- V1–V5 ใช้ EfficientNet-B0, input 224×224×3, GAP, Dropout และ Dense softmax 6 คลาส
- V1 มี 4,057,257 parameters แต่ trainable เพียง 7,686 — backbone frozen
- V2–V5 มี 4,057,257 parameters, trainable 2,045,206, non-trainable 2,012,051
- BatchNorm 49 layers ถูก freeze ใน V2–V5 ซึ่งเหมาะกับ batch เล็กและ domain adaptation ที่ข้อมูลน้อย

### Preprocessing

Training และ Runtime ตรงกัน:

```text
tf.io.decode_image(channels=3)
→ tf.cast(float32)
→ tf.image.resize(224×224, bilinear, antialias=False)
→ pixel range [0,255]
→ EfficientNet embedded rescaling
```

จึงไม่พบ preprocessing mismatch เป็นสาเหตุของ V4/V5 real-image failure

### Augmentation

V2–V5 checkpoint ฝัง augmentation เดิม:

- horizontal and vertical flip
- rotation ±0.08
- zoom 0.10
- contrast 0–0.10

Notebook มีการนิยาม V3 augmentation ที่แรงขึ้น แต่ training config ระบุ `embedded_v2_only`; จึงไม่ได้ใช้ augmentation ใหม่ในการฝึก V3–V5 จริง ไม่มี background randomization, random erasing, color/illumination stress หรือ foreground-aware augmentation

### Optimization และ Overfitting

- V2: head LR `1e-3`, fine-tune last 40 layersด้วย LR `1e-5`
- V3/V4/V5: continued fine-tuning LR `1e-5`
- V5 train accuracy เกิน 99% อย่างรวดเร็ว แต่ best external validation loss อยู่ epoch 1
- การฝึกต่อถึง epoch 7 ไม่ทำให้ best checkpoint ดีขึ้น เป็นสัญญาณว่า tiny external validation และ repeated natural samples ไม่รองรับการ fine-tune ต่อ

### Reproducibility / Provenance

จุดแข็ง:

- Seed 42 ถูกใช้ใน config/sampling หลายส่วน
- Manifests และ checkpoints มีไฟล์คงอยู่และสามารถคำนวณ SHA ได้
- Preprocessing contract ระบุชัด

จุดอ่อน:

- WSL project directory ไม่ใช่ Git repository จึงไม่มี commit SHA ของ Notebook/code
- V5 ไม่มี standalone training config/summary ที่บันทึก dataset hashes, environment lock และ checkpoint hashครบ
- ใช้ TensorFlow `2.22.0-rc0` และ Keras development build เพิ่มความเสี่ยง reproducibility
- Notebook state มี stale variables (`pred_v4`, `pred_v5`, `eval_df`, `y_true`) ที่ไม่ถูกสร้างใน visible current cells ก่อน evaluation
- V4 stored external metric ไม่ตรงกับ direct checkpoint inference

## 5. Architecture Comparison

| Option | ข้อดี | ข้อเสีย / ความเสี่ยง | Training cost บน RTX 4050 3.5 GB | บทบาทที่แนะนำ |
|---|---|---|---|---|
| Fresh EfficientNet-B0 | รู้จัก pipeline แล้ว, 4.06M params ใน current custom model, engineering risk ต่ำ | อาจยังเรียน shortcut หาก data protocol ไม่เปลี่ยน | ต่ำ–ปานกลาง; batch 16–32 ตาม memory | **P0 baseline หลัก** |
| Continue V5 EfficientNet-B0 | ถูกที่สุดและเริ่มได้ทันที | สืบทอด shortcut/overfit และ dev-set history เดิม | ต่ำ | **ไม่แนะนำ** |
| EfficientNetV2-B0 | ImageNet efficiency/accuracy สูงกว่า B0; training-aware design | ใหญ่กว่า, ต้อง verify preprocessing และ memory ใหม่; ไม่แก้ data bias เอง | ปานกลาง; เริ่ม batch 8–16 + mixed precision | **P1 challenger / target candidate** |
| MobileNetV3-Large | เหมาะกับ mobile CPU, latency ต่ำ | Accuracy ceiling/feature capacity อาจต่ำกว่า; current runtime ไม่ได้ on-device | ต่ำ | ทดสอบเมื่อ on-device เป็น requirement |
| MobileNetV3-Small | เบาและเร็วมาก | เสี่ยง underfit morphology/leaf damage ที่ละเอียด | ต่ำมาก | P2 latency baseline เท่านั้น |
| MobileNetV2 | Stable และง่าย | เก่ากว่า V3/EfficientNet, ImageNet accuracy ต่ำกว่า B0 | ต่ำ | ไม่ใช่ตัวเลือกแรก |
| Pretrained embedding + linear head | วัด separability ได้เร็ว, diagnostic ดี | Integration/serving ใหม่, calibration/OOD ยังต้องออกแบบ | ต่ำสำหรับ linear probe | P2 research diagnostic |

Keras Applications ระบุ EfficientNet-B0 5.3M parameters/77.1% ImageNet top-1, EfficientNetV2-B0 7.2M/78.7%, MobileNetV2 3.5M/71.3%; MobileNetV3 paperออกแบบโดยเน้น mobile CPU โดยตรง ([Keras Applications](https://keras.io/applications/), [MobileNetV3 paper](https://arxiv.org/abs/1905.02244), [EfficientNet paper](https://arxiv.org/abs/1905.11946), [EfficientNetV2 paper](https://arxiv.org/abs/2104.00298)) ตัวเลข ImageNet ใช้เปรียบเทียบต้นทุน/ศักยภาพเท่านั้น ไม่ใช่หลักฐานว่า architecture ใดจะชนะบน PhytoScan

## 6. Recommended Target Architecture

### ข้อเสนอ

ใช้ **Fresh ImageNet EfficientNetV2-B0** เป็น target candidate แต่ต้องแข่งขันกับ **Fresh ImageNet EfficientNet-B0** ภายใต้ data/split/training protocol เดียวกัน ห้ามเริ่มจาก V5

โครงสร้างเป้าหมาย:

```text
RGB 224×224, float32 [0,255]
→ controlled augmentation
→ ImageNet pretrained backbone
→ GlobalAveragePooling2D
→ Dropout 0.3
→ Dense(6, softmax)
```

Training strategy:

1. Stage A: freeze backbone, train head
2. Stage B: unfreezeเฉพาะท้าย backbone; freeze BatchNorm
3. ใช้ class/source-balanced batches
4. ใช้ validation ที่ group-disjoint และครบ 6 คลาส
5. เลือก checkpointด้วย Macro-F1/worst-class recall ร่วมกับ loss ไม่ใช่ accuracy อย่างเดียว

เหตุผลที่แผนนี้มีโอกาสดีกว่า V1–V5:

- ตัด inherited representation จาก V2→V5
- แก้ source/domain balance ที่เป็น bottleneck หลัก
- เทียบ architecture แบบควบคุมตัวแปร
- ใช้ evaluation ครบ 6 คลาสและไม่ปะปน quality-invalid samples
- แยก development กับ locked test จริง
- ทำซ้ำจาก config/script ได้โดยไม่พึ่ง Notebook kernel state

## 7. Proposed Dataset & Evaluation Strategy

### Dataset roles ใหม่

1. **Training Pool** — Legacy ที่ผ่าน audit + natural/mobile development data
2. **Development Validation** — ครบ 6 คลาส, group-disjoint, ใช้เลือก hyperparameter/checkpoint
3. **Quality-Gate Challenge Set** — ใบไม่ชัด, หลายต้น, blur, extreme lighting; ไม่รวมใน species accuracy
4. **Known-Failure Regression Set** — กรณีลิ้นมังกร/ดาวเรืองเดิมและ failure ใหม่; ไม่ใช้เป็น aggregate metric
5. **Locked External Mobile Test** — เก็บใหม่หลัง freeze protocol; เปิดครั้งเดียวหลังเลือก model/config
6. **Unsupported/OOD Set** — พืชชนิดอื่นและ non-plant; ใช้พัฒนา rejection แยก ไม่ปะปนกับ 6-class metrics

### Collection priorities

- อย่างน้อย 50 ภาพต่อคลาสสำหรับ initial locked test; 100 ต่อคลาสจะให้ per-class estimate ที่น่าเชื่อถือกว่า
- หลายเครื่องโทรศัพท์, ผู้ถ่าย, ต้น, session, แสง, background และระยะถ่าย
- ทุกคลาสต้องมี healthy, diseased, insect-damaged และ partial/cropped leaves ตามการใช้งานจริง
- Rose ต้องมีใน development validation และ locked test
- Marigold ต้องเพิ่ม natural diseased foliage เป็น P0
- บันทึก `plant_id`, `observer_id`, `session_id`, `device`, `domain`, `health_state`, `source`, `license`, `attribution`

### Split rules

- Split ด้วย plant/session/observer group ก่อนแบ่งภาพ
- Near-duplicate cluster ต้องอยู่ split เดียวกัน
- ห้ามใช้ Locked Test เลือก architecture, augmentation, threshold หรือ calibration
- Legacy V1 Test ถูกเปิดประเมินหลายครั้งแล้ว ให้เปลี่ยนสถานะเป็น **legacy regression set** ไม่ใช่ final blind test
- External 20 ภาพเดิมให้เปลี่ยนสถานะเป็น **overused development/challenge set**

### Metrics

- Primary: Macro-F1
- Safety: minimum per-class recall และ per-class confusion
- Secondary: balanced accuracy, top-1 accuracy, NLL, ECE/Brier score
- Domain slices: natural/mobile vs studio/black/white background
- Health slices: healthy vs disease vs insect damage
- Quality gate: coverage และ accepted accuracy แยกจาก species classifier
- รายงาน 95% confidence intervals และ paired bootstrap/McNemar เมื่อเปรียบเทียบ model บนภาพชุดเดียวกัน

### Promotion rule

ต้อง freeze ก่อนเปิด locked test:

- candidate ชนะ V5 บน new development Macro-F1 อย่างมีนัยสำคัญเชิงปฏิบัติที่กำหนดล่วงหน้า
- ไม่มีคลาสใด recall ลดลงเกิน tolerance ที่กำหนดล่วงหน้า
- Known failures ต้องไม่ regress
- preprocessing parity, model hash, manifest hash และ config hash ต้องครบ
- locked test เปิดครั้งเดียวและห้ามแก้ model/threshold จากผลนั้น

## 8. Experiment Matrix

| ID | Priority | เป้าหมาย | ตัวแปรที่เปลี่ยน | Control | Evaluation | ค่าใช้จ่าย / ความคุ้มค่า |
|---|---|---|---|---|---|---|
| E0 | P0 | สร้าง baseline ที่ reproducible | ไม่มี training; โหลด V5 checkpoint ตรง | V5 current | New dev + known failures | ต่ำ / สูงมาก |
| E1 | P0 | ทดสอบผลของ inherited weights | Fresh ImageNet B0 vs V5-init B0 | data/sampler/seed เหมือนกัน | New dev Macro-F1, worst recall | ปานกลาง / สูงมาก |
| E2 | P0 | ทดสอบ source/class balance | source+class-balanced sampler | E1 winner with old sampler | domain/per-class metrics | ต่ำ / สูง |
| E3 | P0 | ลด background shortcut | targeted color/lighting, random erasing, crop; เปลี่ยนทีละชนิด | E2 | natural vs studio slices, known failures | ปานกลาง / สูง |
| E4 | P1 | เปรียบเทียบ backbone | Fresh EfficientNetV2-B0 | Fresh B0 with same pipeline | Macro-F1, recall, latency, VRAM | ปานกลาง / สูง |
| E5 | P1 | Hard-example mining | เพิ่มเฉพาะ dev-train errors ที่ review แล้ว | E4 winner | untouched dev-valid | ปานกลาง / ปานกลาง |
| E6 | P1 | Calibration | temperature scaling หลัง freeze weights | uncalibrated winner | NLL/ECE/Brier | ต่ำ / ปานกลาง |
| E7 | P2 | Mobile feasibility | MobileNetV3-Large | production winner | accuracy + device latency | ปานกลาง / ขึ้นกับ roadmap |
| E8 | P2 | Unsupported rejection | separate OOD/quality model or embedding distance | softmax threshold | OOD AUROC/FPR@TPR + coverage | สูง / ทำเมื่อมี OOD data |

หลักการ: screening ใช้ 1 seed; top 2 configurations ต้องทำซ้ำอย่างน้อย 3 seeds และรายงาน mean/std ห้ามเปลี่ยนหลายตัวแปรใน run เดียว

## 9. Prioritized Implementation Plan

### Phase P0-A — Repair Evaluation Foundation

งาน:

- Freeze hashes ของ V1–V5 artifacts ปัจจุบัน
- เปลี่ยนสถานะ External 20 เป็น overused development
- แยก 3 quality-invalid images ไป quality challenge
- Visual adjudication pHash candidates 12+ คู่ที่เกี่ยวข้อง
- แก้ schema governance ของ V5 review (`final_approval` vs `manual_decision`) ใน manifest รุ่นถัดไป โดยไม่เขียนทับของเดิม
- สร้าง license/attribution ledger โดยอ้างอิง source เดิม

Acceptance criteria:

- ทุก sample มี class, source, group, domain, license status
- Train/Dev/Locked Test ไม่มี path/SHA/group overlap
- ทุก class มี representation ใน Dev/Locked Test
- Test manifest hash ถูก freeze และไม่ถูกเปิดระหว่าง development

### Phase P0-B — Data Gap Closure

งาน:

- เก็บ natural/mobile images ครบ 6 คลาส
- เน้น Marigold natural diseased, Rose natural, disease/insect variations ทุกคลาส
- Manual review โดยอย่างน้อยสอง passes สำหรับ ambiguous/mixed-species images

Acceptance criteria:

- ไม่มีคลาสใดไม่มี natural/mobile examples
- ทุก class มี healthy + abnormal coverage
- session/observer/plant group metadata ครบ
- images ที่ไม่เห็น target ชัดถูกย้ายไป quality challenge

### Phase P0-C — Reproducible Fresh Baseline

งาน:

- ย้าย training logic จาก mutable Notebook ไป versioned script/config
- Train Fresh ImageNet EfficientNet-B0
- บันทึก environment lock, seed, config hash, manifest hashes, checkpoint hash และ row-level predictions

Acceptance criteria:

- rerun ให้ prediction/metrics ตรงภายใน numerical tolerance
- ไม่มี undefined notebook state
- ผ่าน known-failure regression และ preprocessing parity

### Phase P1 — Architecture and Robustness Experiments

- Run E2–E6 ตาม matrix
- Promote top configurationจาก new development เท่านั้น
- วัด VRAM, training time, backend latency

Acceptance criteria:

- Macro-F1 และ minimum per-class recall ดีขึ้นตาม promotion rule ที่ freeze ไว้
- ไม่แลก performance ของ class ใด class หนึ่งกับ average score
- calibration ไม่ถูกอ้างเป็น OOD detection

### Phase P2 — Locked Test and Deployment Decision

- Freeze model/config/threshold
- เปิด Locked External Mobile Test ครั้งเดียว
- เปรียบเทียบกับ V5 แบบ paired evaluation
- ตัดสิน Backend deployment หรือเริ่ม MobileNet/TFLite track แยก

Acceptance criteria:

- candidate ผ่าน promotion rule บน locked test
- runtime preprocessing และ class mapping ตรง artifact
- failure analysis และข้อจำกัดถูกรายงานครบ

## 10. Risks and Stop Conditions

| Risk | Stop condition |
|---|---|
| External validation ยังน้อย/ไม่ครบคลาส | หยุด architecture tuning จน Dev ครบ 6 คลาส |
| Locked test ถูกเปิดก่อน freeze | ยกเลิกสถานะ locked และเก็บชุดใหม่ |
| Label/plant identity ไม่แน่ชัด | ห้ามนำเข้า train/dev; ส่ง manual adjudication |
| License ไม่อนุญาตหรือ attribution ขาด | ห้ามใช้เพื่อเผยแพร่/deploy จนตรวจสิทธิ์ครบ |
| pHash candidate ยืนยันว่าเป็น near duplicate ข้าม split | regroup และสร้าง split ใหม่ก่อน training |
| Fresh B0 และ V2–V5 ให้ผลเหมือนกัน | หยุดเพิ่ม epochs; กลับไปแก้ data coverage/domain |
| Train >99% แต่ Dev ไม่ดีขึ้น 2–3 epochs | early stop; ห้ามเพิ่ม capacity โดยไม่มีหลักฐาน |
| EfficientNetV2-B0 OOM/unstable บน 3.5 GB | ลด batch/mixed precision; หากยังไม่เสถียรให้คง B0 |
| Known failure confidence สูงขึ้นแต่ยังผิด | ห้าม promote แม้ aggregate metric สูงขึ้น |
| Calibration ลด ECE แต่ accuracy/OOD ไม่ดีขึ้น | ห้ามอ้างว่าแก้ unsupported detection |

## 11. Immediate Next Actions

1. **P0 — Freeze audit baseline**: เก็บ SHA table, direct-checkpoint evaluation script และระบุ V4 stored metric ว่า Not Reproducible
2. **P0 — Repair external evaluation design**: จัด External 20 ภาพใหม่เป็น overused dev/quality challenge และกำหนด protocol สำหรับ new 6-class Dev + Locked Test
3. **P0 — Close natural data gaps**: เริ่มเก็บ Marigold/Rose natural mobile images พร้อม diseased/insect cases และ group metadata
4. **P0 — Complete governance review**: visual review near-duplicate candidates, label audit indoor 454 training images และสร้าง license/attribution ledger
5. **P0 — First real experiment**: หลัง Dev ใหม่พร้อม ให้รัน Fresh ImageNet B0 vs V5-initialized B0 ด้วย data/sampler/seed เดียวกัน

## Final Answers

### 1. ควรปรับ EfficientNet-B0 ต่อหรือเปลี่ยน Architecture?

อย่า fine-tune ต่อจาก V5 ควรสร้าง **Fresh EfficientNet-B0 baseline** ก่อน แล้วทดสอบ **EfficientNetV2-B0** เป็น challenger ภายใต้ protocol เดียวกัน การเปลี่ยน architecture ทันทีโดยไม่แก้ data/evaluation มีโอกาสทำซ้ำความล้มเหลวเดิม

### 2. สาเหตุใดน่าจะทำให้ Accuracy บนภาพจริงต่ำ?

สาเหตุที่มีหลักฐานสูงสุดคือ background/source shortcut, natural data ต่ำ, natural diseased coverage ขาด, repeated oversampling ของ natural images จำนวนน้อย, development set เล็ก/ไม่ครบคลาส และการสืบทอด weights จาก V2 ถึง V5 ส่วน preprocessing mismatch ไม่พบ

### 3. Dataset ปัจจุบันเพียงพอหรือไม่?

เพียงพอสำหรับ baseline และ regression research แต่ไม่พอสำหรับ real-world claim หรือ production promotion ต้องเพิ่ม natural/mobile data ที่ group/label/license ครบ และสร้าง locked external test ใหม่

### 4. การทดลองใดควรทำก่อน?

หลังแก้ Dev split แล้ว ให้ทำ **Fresh ImageNet EfficientNet-B0 vs V5-initialized EfficientNet-B0** ด้วย data, sampler, augmentation, seed และ evaluation เดียวกัน เพราะเป็นการทดสอบโดยตรงว่า inherited representation/shortcut เป็นปัจจัยสำคัญหรือไม่

### 5. จะพิสูจน์อย่างไรว่าโมเดลใหม่ดีกว่า V5 จริง?

เลือก model/config บน new group-disjoint development set เท่านั้น จากนั้น freeze ทุก artifact แล้วประเมินครั้งเดียวบน locked external mobile test ที่ครบ 6 คลาส เปรียบเทียบกับ V5 ด้วย row-level paired predictions, Macro-F1, per-class recall, confidence intervals, known failures และ domain slices โดยห้ามปรับโมเดลจากผล locked test

