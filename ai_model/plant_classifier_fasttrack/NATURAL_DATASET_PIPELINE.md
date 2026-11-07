# PhytoScan Natural Dataset Expansion

Pipeline นี้รับภาพธรรมชาติใหม่แบบ immutable batch, สร้าง contact sheets/manual-review manifest, ตรวจ SHA-256/pHash, แบ่งข้อมูลตาม observer/session/plant group และสร้าง Fresh B0 config แบบ data-only เมื่อผ่านทุก gate

## 1. Initialize

```powershell
wsl.exe -d Ubuntu --cd /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack -- /home/mind_hp/phytoscan/.venv/bin/python natural_dataset_pipeline.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/natural_dataset_expansion.json --workspace /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/natural_dataset/expansion_v1 init
```

คัดลอก `templates/intake_metadata_template.csv` เป็นไฟล์ใหม่ แล้วกรอก metadata ทุกช่อง ห้ามอนุมาน label จากชื่อโฟลเดอร์

## 2. Import an immutable batch

```powershell
wsl.exe -d Ubuntu --cd /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack -- /home/mind_hp/phytoscan/.venv/bin/python natural_dataset_pipeline.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/natural_dataset_expansion.json --workspace /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/natural_dataset/expansion_v1 import --metadata /absolute/path/new_images_metadata.csv --batch-id mobile_20261030_01
```

ภาพต้นฉบับไม่ถูกแก้ไข Pipeline คัดลอกเข้า batch staging พร้อม SHA-256, pHash, resolution และ semantic metadata

## 3. Generate review manifests and contact sheets

```powershell
wsl.exe -d Ubuntu --cd /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack -- /home/mind_hp/phytoscan/.venv/bin/python natural_dataset_pipeline.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/natural_dataset_expansion.json --workspace /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/natural_dataset/expansion_v1 review --review-id review_20261030_01
```

แก้เฉพาะสำเนา `manual_review_manifest.csv` และ `duplicate_review_manifest.csv` ใน review directory ตาม `templates/MANUAL_REVIEW.md`

## 4. Check coverage

```powershell
wsl.exe -d Ubuntu --cd /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack -- /home/mind_hp/phytoscan/.venv/bin/python natural_dataset_pipeline.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/natural_dataset_expansion.json --workspace /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/natural_dataset/expansion_v1 status --review-manifest /path/to/manual_review_manifest.csv --status-id status_20261030_01
```

เป้าหมายต่อคลาส: Training 50, Development 20, Locked Test 20; รวมทั้งระบบ 300/120/120 ภาพ โดย healthy 36, diseased 36 และ insect-damaged 18 ภาพต่อคลาส

## 5. Group-aware split

```powershell
wsl.exe -d Ubuntu --cd /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack -- /home/mind_hp/phytoscan/.venv/bin/python natural_dataset_pipeline.py --config /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/configs/natural_dataset_expansion.json --workspace /mnt/c/phytoscan/ai_model/plant_classifier_fasttrack/natural_dataset/expansion_v1 split --review-manifest /path/to/manual_review_manifest.csv --duplicate-manifest /path/to/duplicate_review_manifest.csv --split-id split_v1
```

คำสั่งนี้ fail-closed หาก label/license/quality/duplicate review ยังไม่ครบหรือจำนวน/health slice ไม่ถึงเป้า เมื่อผ่านแล้วจะสร้าง:

- `combined_training.csv`
- `development.csv`
- `duplicate_leakage_receipt.json`
- `fresh_b0_natural_data_only.ready.json`
- `protected_locked_test/locked_test_manifest.csv`

Training config ไม่มี path ของ Locked Test และ architecture/augmentation ต้องตรงกับ Fast Track base config เดิมทุกค่า Pipeline นี้ไม่เรียก training code
