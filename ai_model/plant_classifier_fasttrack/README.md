# PhytoScan Plant Classifier Fast Track

แพ็กเกจนี้เป็น pipeline แยกจาก Notebook สำหรับทดลอง Fresh ImageNet EfficientNet-B0 โดยไม่แก้ checkpoint, manifest, threshold หรือ runtime model เดิม และไม่ deploy โมเดลอัตโนมัติ

## สถานะข้อมูลปัจจุบัน

Training ถูกออกแบบให้ **fail-closed** หาก Development Validation ไม่ผ่านทุกเงื่อนไขต่อไปนี้:

- สถานะชุดข้อมูลเป็น `eligible_group_disjoint_development`
- ครบ 6 คลาสตาม class order ที่ล็อกไว้
- มีอย่างน้อย 20 ภาพต่อคลาส (ปรับได้ใน config แต่ห้ามลดเพื่อหลบ validation gate)
- ทุกภาพผ่าน quality review
- ไม่ overlap กับ train ทาง path และเมื่อ metadata มีให้ตรวจ จะตรวจ SHA-256 และ group ด้วย
- duplicate-audit receipt ต้องอ้าง manifest hashes ตรงกันและยืนยันว่า near-duplicate review เสร็จแล้ว
- ไม่มี Legacy Test หรือ Locked Test อยู่ใน training config

Config ที่ให้มาชี้ไปยัง External Development เดิม 20 ภาพเพื่อให้ preflight ตรวจสภาพจริง ชุดนี้มีสถานะ `overused_incomplete`, ไม่มี Rose และมีภาพไม่ผ่าน quality gate จึงต้องหยุดก่อน training ตามข้อกำหนดงาน

## คำสั่งเดียว

รันจาก Windows PowerShell:

```powershell
wsl.exe -d Ubuntu -- /home/mind_hp/phytoscan/.venv/bin/python /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/run_fasttrack.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/fresh_b0_fasttrack.json
```

คำสั่งนี้ทำ preflight, ประเมิน V5 โดยตรงบนชุด diagnostic เดิมพร้อม row-level predictions และจะฝึก/ประเมิน Fresh B0 ต่อเมื่อ validation gate ผ่านเท่านั้น ขณะข้อมูลปัจจุบันคำสั่งต้องจบด้วย exit code `3` และข้อความ `TRAINING_BLOCKED`; นี่เป็นพฤติกรรมที่ตั้งใจไว้ ไม่ใช่ training error

เมื่อมี Development Validation ใหม่ที่ผ่าน review และ group-disjoint แล้ว ให้แก้เฉพาะสำเนา config ใหม่ โดยเปลี่ยน path และ `status` เป็น `eligible_group_disjoint_development` จากนั้นใช้คำสั่งเดิมกับ config ใหม่นั้น ห้ามเปลี่ยนสถานะชุดเดิมเพื่อบังคับให้ผ่าน

## Standalone checkpoint evaluation

```powershell
wsl.exe -d Ubuntu -- /home/mind_hp/phytoscan/.venv/bin/python /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/evaluate_checkpoint.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/fresh_b0_fasttrack.json --model /path/to/model.keras --manifest /path/to/manifest.csv --dataset-role diagnostic --output /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/artifacts/manual_eval
```

Evaluator โหลด `.keras` checkpoint โดยตรง ใช้ TensorFlow RGB decode, float32, bilinear resize 224×224, `antialias=False`, pixel range 0–255 และบันทึก Accuracy, Macro-F1, per-class recall, confusion matrix, model/manifest SHA-256 และ probabilities ครบ 6 คลาสของแต่ละภาพ

## Training contract

- Fresh `tf.keras.applications.EfficientNetB0(weights="imagenet")`; ไม่โหลด V2–V5
- Stage 1: freeze backbone และ train head
- Stage 2: unfreeze 40 layers ท้ายโดย freeze BatchNorm
- checkpoint selection ใช้ Development Macro-F1; tie-break ด้วย minimum per-class recall และ accuracy
- class/source-aware finite-pool schedule จำกัดการใช้ภาพเดิมไม่เกิน 2 ครั้งต่อ epoch
- augmentation เฉพาะ flip/rotation/zoom/brightness/contrast ช่วงแคบ ไม่มี background replacement
- batch size 16 และ mixed precision เมื่อพบ GPU เพื่อเหมาะกับ RTX 4050 ที่ VRAM จำกัด
- ทุก run ใช้ directory ใหม่และปฏิเสธการ overwrite

## Artifact สำคัญ

- `preflight.json` — validation gate, counts, overlap และ manifest hashes
- `v5_overused_development_diagnostic/evaluation.json`
- `v5_overused_development_diagnostic/row_predictions.csv`
- `fresh_b0_training/training_receipt.json` (สร้างเฉพาะเมื่อ gate ผ่าน)
- `v5_vs_fresh_b0.csv` (สร้างเฉพาะเมื่อฝึกและประเมินได้อย่างถูกต้อง)

ไม่มีโค้ดส่วนใดอ่าน Legacy Test/Locked Test, ปรับ threshold หรือ deploy checkpoint

## P0 Development Validation Recovery

สแกน candidate sources, ตรวจ path/SHA-256/pHash/group leakage และสร้าง contact sheets โดยไม่อนุมัติ label อัตโนมัติ:

```powershell
wsl.exe -d Ubuntu -- /home/mind_hp/phytoscan/.venv/bin/python /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/recover_development_validation.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/recovery_p0.json --output /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/recovery/<new-run-id>
```

Recovery output มี `candidate_audit_all.csv`, `development_validation_manual_review.csv`, contact sheets, pending duplicate receipt และสำเนา Fast Track config ที่ต้องคงสถานะ `pending_manual_review` จนกว่าจะมีภาพผ่าน manual review อย่างน้อย 20 ภาพต่อคลาส พร้อมยืนยัน natural/mobile likeness และ license แล้วเท่านั้น
