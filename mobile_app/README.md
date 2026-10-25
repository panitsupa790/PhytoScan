# PhytoScan Mobile

Flutter client for selecting a supported plant, capturing or uploading one to
three leaf images, and displaying one diagnosis per image from the FastAPI
backend. The interface uses an iOS-inspired botanical design system and keeps
future My Plants, history, and account areas as honest empty states.

## Run

Start the backend on port 8000, then run:

```powershell
cd C:\phytoscan\mobile_app
flutter pub get
flutter run
```

The default API URL is `http://10.0.2.2:8000`, which reaches the host machine
from an Android emulator. Override it in one place with a Dart define:

```powershell
flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000
```

Use the computer's LAN IP for a physical device. The backend must be started
with `--host 0.0.0.0` and the device and computer must be on the same network.

## Checks

```powershell
flutter analyze --no-pub
flutter test --no-pub
flutter build apk --debug --no-pub
```
