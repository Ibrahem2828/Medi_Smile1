# MediSmile Backend – Full Endpoint Handbook

مبدأ ثابت: Authentication → Role Check → Ownership → University Scope → State Check. الردود القياسية تستخدم JSON، مع حقل `detail` للرسائل، و`data` أو `results` حسب الحاجة. المصادقة عبر JWT (access/refresh) مع إرسال الـaccess في `Authorization: Bearer <token>`.

النسخة التالية موجهة لفريق الفرونت وتحتوي على المسارات، الطلبات، والاستجابات المتوقعة لكل تطبيق.

---
## 1) Accounts
### Auth (منفصلة لكل دور)
- POST `/api/accounts/login/patient/`
- POST `/api/accounts/login/student/`
- POST `/api/accounts/login/supervisor/`
- POST `/api/accounts/login/university-admin/`
- POST `/api/accounts/login/tech-support/`

Request Body:
```json
{ "email": "user@example.com", "password": "StrongPassword123" }
```

Response – Success (200):
```json
{
  "detail": "Login successful.",
  "tokens": { "refresh": "jwt-refresh-token", "access": "jwt-access-token" },
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "first_name": "First",
    "last_name": "Last",
    "role": "patient",
    "role_id": "uuid",
    "fcm_token": null,
    "is_active": true,
    "created_at": "2025-12-20T10:15:30Z",
    "updated_at": "2025-12-26T18:42:10Z"
  }
}
```
Errors: `{"detail": "Invalid credentials."}` | `{"detail": "You are not allowed to login with this role."}` | `{"detail": "User account is inactive."}`

### إنشاء المستخدم
- POST `/api/accounts/register/patient/` (AllowAny)  
  Body: email, username, first_name, last_name, password, password_confirm  
  201 → `{ "id": "...", "email": "...", "role": "patient" }`

- POST `/api/accounts/create/student/` (university_admin)  
  Body: email, username, first_name, last_name, password, password_confirm  
  201 → user + ربط بالجامعة (تلقائياً)

- POST `/api/accounts/create/supervisor/` (university_admin)
- POST `/api/accounts/create/university-admin/` (tech_support) + `university_id`
- POST `/api/accounts/create/tech-support/` (tech_support أو superuser)

### الملف الشخصي (self only)
- GET/PATCH `/api/accounts/me/patient/`
- GET/PATCH `/api/accounts/me/student/`
- GET/PATCH `/api/accounts/me/supervisor/`
- GET/PATCH `/api/accounts/me/university-admin/`
- GET/PATCH `/api/accounts/me/tech-support/`
قيود: لا تغيير role/university من هذه المسارات.

### FCM Token
- POST `/api/accounts/me/token/` — `{ "fcm_token": "..." }` → 200 `{ "detail": "Token registered." }`
- DELETE `/api/accounts/me/token/` → 200 `{ "detail": "Token removed." }`

---
## 2) Universities
- GET `/api/universities/` (admin scoped) | POST `/api/universities/` (tech_support)
- GET/PATCH `/api/universities/<id>/`
- برامج/أعوام/مواد (أمثلة):
  - GET/POST `/api/universities/programs/`
  - GET/POST `/api/universities/academic-years/`
صلاحيات: tech_support شامل؛ university_admin في نطاق جامعته.

---
## 3) Cases
- GET/POST `/api/cases/`  
  - patient create: `{ "title": "...", "description": "..." }`
  - responses تتضمن حالة case (new/pending_assignment/assigned/in_progress/completed/closed)
- GET/PATCH `/api/cases/<id>/`
- GET `/api/cases/<id>/history/`
قيود: جلسة تتبع حالة؛ لا تعديل بعد closed؛ طالب يعمل فقط على assigned case.

### Case Sessions
- GET/POST `/api/cases/<case_id>/sessions/` (student على case مسند)  
  Body: notes, status (draft/completed/needs_review/approved/rejected)
- GET/PATCH `/api/case-sessions/<id>/`

---
## 4) Appointments
- GET/POST `/api/appointments/` (student ينشئ/يعدل؛ patient قراءة فقط)  
  Body: case_id, scheduled_at, notes
- GET/PATCH `/api/appointments/<id>/`
قيود: تعديل الموعد للطالب فقط؛ المشرف يمكنه إلغاء/مراجعة حسب السياسة.

---
## 5) Messaging (Case Chat)
- GET `/api/messaging/rooms/<uuid:pk>/` — قراءة غرفة
- POST `/api/messaging/rooms/` — إنشاء/جلب غرفة حالة واحدة  
  Body: `{ "case": "<case_uuid>" }`
- GET/POST `/api/messaging/rooms/<uuid:room_id>/messages/`  
  Body (POST): `{ "content": "..." }`
- GET `/api/messaging/messages/<uuid:pk>/`
- WebSocket: `ws/chat/<room_id>/`
صلاحيات: إرسال للمريض/الطالب فقط وحالة ASSIGNED/IN_PROGRESS؛ مشرف/Admin جامعة/Tech Support قراءة فقط؛ غرفة واحدة لكل حالة؛ لا إرسال بعد إغلاق الحالة.  
رد إرسال رسالة (201): `{ "id": "uuid", "sender": {id,first_name,last_name}, "content": "...", "sent_at": "...", "is_system": false }`

---
## 6) Notifications
- GET `/api/notifications/` — Inbox للمستلم
- POST `/api/notifications/` — إنشاء إشعار  
  Body: notification_type, priority, recipient_id, (appointment_id أو target_type+target_id), title, message, proposed_changes?
- GET/PATCH `/api/notifications/<id>/` — تحديث (mark read/accept/reject)  
  Body (PATCH): `{ "status": "accepted|rejected|pending|info", "response_message": "...", "is_read": true }`
رد قراءة (200): Notification كامل مع sender/recipient مختصرين.

---
## 7) Community
- GET `/api/community/content/` — منشورات الجامعة
- POST `/api/community/content/` (student)  
  Body: title, body, attachments…
- POST `/api/community/content/<id>/approve/` (supervisor)
- POST `/api/community/content/<id>/reject/` (supervisor)
- POST `/api/community/content/<id>/like/` (patient react only)
- GET `/api/community/approvals/` (university_admin) — سجل الموافقات

---
## 8) Reports
- GET/POST `/api/reports/` (student draft)  
  Body: case_id, content, attachments…
- GET/PATCH `/api/reports/<id>/`
- POST `/api/reports/<id>/approve/` (supervisor)
- POST `/api/reports/<id>/reject/` (supervisor)
قيود: لا تعديل بعد الاعتماد.

---
## 9) Evaluations
- GET/POST `/api/evaluations/`  
  Body مثال: `{ "student_id": "...", "target_type": "case|session|appointment", "target_id": "...", "score": 85, "rubric": { ... }, "comment": "..." }`
- GET/PATCH `/api/evaluations/<id>/`
- POST `/api/evaluations/<id>/submit/`
- POST `/api/evaluations/<id>/finalize/`
- GET `/api/evaluations/students/<student_id>/statistics/`
حالات: draft → submitted → final (مغلق).

---
## 10) Support
- GET/POST `/api/support/tickets/`  
  Body: subject, body, priority (low/normal/high/critical), attachments[]
- GET/PATCH `/api/support/tickets/<id>/`
صلاحيات: المستخدم يرى تذاكره؛ Admin الجامعة يرى تذاكر جامعته؛ Tech Support يرى الجميع.

---
## 11) Backup
- GET `/api/backup/jobs/`
- POST `/api/backup/jobs/` (tech_support) — إنشاء مهمة نسخ
- POST `/api/backup/jobs/<id>/restore/`
صلاحيات: tech_support فقط.

---
## 12) AI
- POST `/api/ai/diagnosis/` (patient create/read حالته؛ student/supervisor read)  
  Body: images/text payload
- GET `/api/ai/diagnosis/<id>/`
Immutable بعد الإنشاء.

---
## 13) Audit
- GET `/api/audit/logs/` (tech_support كامل؛ admin الجامعة نطاق جامعته)
- GET `/api/audit/logs/<id>/`

---
## نماذج أخطاء عامة
- 400 Validation: `{ "field": ["error msg"] }`
- 401 Auth: `{ "detail": "Authentication credentials were not provided." }` أو `{"detail": "token_not_valid", ...}`
- 403 Permissions: `{ "detail": "permission_denied:role_forbidden" }`
- 404 Not Found: `{ "detail": "Not found." }`

---
## ملاحظات للفرونت
- استخدم access token في كل الطلبات المحمية.
- عند 401 مع `token_not_valid` قم بتحديث باستخدام refresh.
- احترم القيود: المريض لا يعدل مواعيد، الطالب لا يرسل/يعدل خارج الحالات المسندة، لا رسائل بعد إغلاق الحالة، لا تغيير role/university من مسارات “me”.
