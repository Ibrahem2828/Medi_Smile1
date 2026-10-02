# MediSmile API contract

`openapi.yaml` (OpenAPI 3.0) is the **single source of truth** for the HTTP API.
It is generated from the code and committed, so every client (mobile app,
dashboards, tests) is checked against the same document.

```bash
# regenerate after an intentional API change
python manage.py spectacular --file docs/api/openapi.yaml --validate
```

Guards:

- `medismile/test_openapi_contract.py` fails when the code and the committed
  spec drift apart, and when an operation the mobile app depends on
  disappears.
- `mobile_app_flutter/tool/check_api_contract.py` fails when the app calls a
  path that is not in this spec. The app's paths live in
  `lib/core/network/api_endpoints.dart`.
- A staff-only live copy is served at `GET /api/schema/`.

## Patient AI diagnosis flow

1. `POST /api/ai/images/` (multipart, field `image`) — JPEG/PNG/WebP, ≤ 10 MB,
   ≤ 40 MP. The image is decoded, EXIF-rotated, downscaled to ≤ 2048 px and
   re-encoded, which strips all metadata (GPS and device data). Returns `id`.
2. `POST /api/ai/diagnose/` JSON `{symptoms_text, image_ids: [id]}`.
   - `201` returns the diagnosis and suggestions.
   - `503` means every AI engine failed. The body carries the persisted
     `failed` diagnosis plus a user-facing `detail`.
   - An image id can be used once, and only by its owner.
   - One-shot multipart (`symptoms_text` + `image`) is also accepted.
   - `image_urls` is legacy and only accepts hosts in
     `AI_IMAGE_URL_ALLOWED_HOSTS` (HTTPS), because the backend fetches them.
3. `POST /api/cases/ai/create/` `{university_id, ai_report, diagnosis_id?, title?, description?}`.
   This promotes the case auto-created in step 2 (or creates one), scoped to the
   chosen university. It then appears in `GET /api/cases/supervisor/new/` for
   that university only.
4. `GET /api/ai/images/{id}/file/` is an authenticated download for the owner,
   and for staff who can see the linked diagnosis.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `AI_IMAGE_MAX_BYTES` | 10485760 | Max upload size |
| `AI_IMAGE_MAX_PIXELS` | 40000000 | Max decoded resolution (decompression-bomb guard) |
| `AI_IMAGE_MAX_SIDE` | 2048 | Longest side after downscaling |
| `AI_IMAGE_URL_ALLOWED_HOSTS` | *(empty)* | Comma-separated HTTPS hosts for legacy `image_urls` |
| `AI_FUSION_URL` | – | Bare host, `…/fusion` or full `…/fusion/analyze-case`; all resolve to the fusion router |
