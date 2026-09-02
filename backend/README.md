# PhytoScan Backend MVP

FastAPI backend สำหรับรับภาพพืช 1-3 ภาพ ตรวจสอบไฟล์ และส่งผลวิเคราะห์จำลองกลับในรูปแบบ JSON โครงสร้างแยก API, image validation และ AI service เพื่อเปลี่ยนไปใช้โมเดลจริงภายหลังโดยไม่เปลี่ยน API contract ฝั่ง Flutter

## Requirements

- Python 3.12
- Windows PowerShell

## Setup

เปิด PowerShell ที่ `C:\phytoscan\backend` แล้วรัน:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`.env.example` แสดง configuration ที่รองรับ ได้แก่ `CORS_ORIGINS`, `MAX_IMAGES` และ `MAX_IMAGE_SIZE_BYTES` สำหรับ PowerShell ให้กำหนดค่าที่ต้องการก่อนเปิด server เช่น:

```powershell
$env:CORS_ORIGINS="http://localhost:8080"
$env:MAX_IMAGE_SIZE_BYTES="10485760"
```

## Run

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

## API

### `GET /health`

```json
{
  "status": "ok",
  "service": "PhytoScan API"
}
```

### `POST /api/v1/analyze`

ส่ง `multipart/form-data` โดยใช้ field ชื่อ `images` ซ้ำกัน 1-3 ครั้ง รองรับ JPG, JPEG และ PNG ขนาดสูงสุดต่อไฟล์เริ่มต้น 10 MB

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/analyze" `
  -F "images=@C:\path\to\leaf-1.jpg" `
  -F "images=@C:\path\to\leaf-2.jpg"
```

Success response:

```json
{
  "success": true,
  "image_count": 2,
  "plant": {
    "code": "eggplant",
    "name_th": "มะเขือยาว",
    "name_en": "Eggplant",
    "confidence": 0.94
  },
  "disease": {
    "code": "leaf_spot",
    "name_th": "โรคใบจุด",
    "name_en": "Leaf Spot",
    "confidence": 0.84
  },
  "symptoms": ["..."],
  "care": ["..."],
  "prevention": ["..."]
}
```

## Error Codes

Error response ใช้รูปแบบเดียวกันทุกกรณี:

```json
{
  "success": false,
  "error_code": "INVALID_IMAGE",
  "message": "ไฟล์ภาพไม่ถูกต้องหรือไฟล์เสีย"
}
```

รหัสที่ใช้งานแล้ว: `INVALID_IMAGE`, `UNSUPPORTED_FILE_TYPE`, `TOO_MANY_IMAGES`, `NO_IMAGES`, `FILE_TOO_LARGE`

รหัสที่เตรียมไว้สำหรับ AI จริง: `LOW_CONFIDENCE`, `UNSUPPORTED_PLANT`, `MULTIPLE_PLANT_TYPES`

## Tests

```powershell
pytest -q
```

## Flutter Integration

Flutter ต้องส่ง multipart request โดยใช้ key `images` สำหรับแต่ละไฟล์ Android Emulator เข้าถึง server บนเครื่องผ่าน `http://10.0.2.2:8000` แทน `localhost` ส่วนอุปกรณ์จริงต้องใช้ IP ในเครือข่ายของเครื่องที่เปิด backend

## MVP Limitations

- ผลวิเคราะห์ยังเป็น Mock: มะเขือยาวและโรคใบจุด
- ไม่มีการ train หรือเรียกโมเดล AI จริง
- ไม่มีฐานข้อมูล, authentication หรือ history API
- ข้อความอาการ การดูแล และการป้องกันใน `app/data/diseases.json` เป็น Mock Content ต้องตรวจสอบกับแหล่งวิชาการหรือผู้เชี่ยวชาญก่อนใช้จริง
- CORS ค่าเริ่มต้นอนุญาตเฉพาะ development origins ที่ระบุไว้ ห้ามใช้ wildcard ใน production
