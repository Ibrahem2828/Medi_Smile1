# MediSmile Backend Apps & APIs (Unified RBAC)

قاعدة ذهبية لكل Endpoint: Authentication → Role Check → Ownership → University Scope → State Check. الأدوار: tech_support > university_admin > supervisor > student > patient.

## 1) Accounts
تسجيل دخول منفصل لكل دور:
- POST `/api/accounts/login/patient/`
- POST `/api/accounts/login/student/`
- POST `/api/accounts/login/supervisor/`
- POST `/api/accounts/login/university-admin/`
- POST `/api/accounts/login/tech-support/`

إنشاء المستخدمين:
- POST `/api/accounts/register/patient/` — المريض يسجل نفسه فقط.
- POST `/api/accounts/create/student/` — university_admin فقط، يربط الطالب بجامعته.
- POST `/api/accounts/create/supervisor/` — university_admin فقط، ضمن جامعته.
- POST `/api/accounts/create/university-admin/` — tech_support فقط، مع university_id.
- POST `/api/accounts/create/tech-support/` — tech_support أو superuser فقط.

الملف الشخصي (self only؛ لا تغيير للدور/الجامعة من هنا):
- GET/PATCH `/api/accounts/me/patient/`
- GET/PATCH `/api/accounts/me/student/`
- GET/PATCH `/api/accounts/me/supervisor/`
- GET/PATCH `/api/accounts/me/university-admin/`
- GET/PATCH `/api/accounts/me/tech-support/`

FCM Token:
- POST `/api/accounts/me/token/` (تسجيل/تدوير)
- DELETE `/api/accounts/me/token/` (إزالة)

## 2) Universities
- CRUD جامعة: tech_support فقط.
- إدارة البرامج/الأعوام/المواد: university_admin داخل جامعته.
- ربط الطلاب/المشرفين بالجامعة إلزامي.
(راجع `apps/universities/` للحقول التفصيلية.)

## 3) Cases
- المريض: POST حالة واحدة نشطة، GET حالته فقط.
- الطالب: يعمل فقط على الحالات المسندة؛ لا يغير الحالة بعد إغلاق/اعتماد المشرف.
- المشرف: إسناد/اعتماد/إغلاق.
Endpoints النموذجية:
- GET/POST `/api/cases/` (حسب الدور)
- GET/PATCH `/api/cases/<case_id>/`
- تاريخ الحالة: GET `/api/cases/<case_id>/history/`

## 4) Appointments
- الطالب: إنشاء/تعديل/إلغاء ضمن حالته.
- المشرف: مراجعة/إلغاء حسب السياسة.
- المريض: قراءة فقط.
Endpoints:
- GET/POST `/api/appointments/`
- GET/PATCH `/api/appointments/<id>/`

## 5) Messaging (Case-scoped)
- غرفة واحدة لكل حالة.
- الإرسال: patient/student فقط وحالة ASSIGNED أو IN_PROGRESS.
- القراءة: patient/student/supervisor/university_admin (نطاق جامعته)/tech_support.
Endpoints:
- GET `/api/messaging/rooms/<uuid:pk>/`
- POST `/api/messaging/rooms/` (إنشاء/جلب غرفة حالة)
- GET/POST `/api/messaging/rooms/<uuid:room_id>/messages/`
- GET `/api/messaging/messages/<uuid:pk>/`
- WS: `ws/chat/<room_id>/` (نفس صلاحيات REST، المشرف/Admin قراءة فقط)

## 6) Notifications
- قراءة: المستلم فقط، Admin الجامعة لنفس الجامعة، Tech Support للكل (read).
- إنشاء: النظام/الطلاب/المشرفون/Admin الجامعة/الدعم الفني (مع تحقق النوع).
Endpoints:
- GET `/api/notifications/`
- POST `/api/notifications/`
- GET/PATCH `/api/notifications/<id>/` (mark as read, accept/reject)

## 7) Community
- الطالب ينشر، المشرف يوافق، يظهر ضمن الجامعة.
- المريض: إعجاب فقط.
- Admin الجامعة يرى سجلات الموافقات.
Endpoints (عينة):
- GET/POST `/api/community/content/` (إنشاء الطالب، موافقة المشرف)
- POST `/api/community/content/<id>/approve/` (supervisor)
- POST `/api/community/content/<id>/reject/` (supervisor)
- GET `/api/community/approvals/` (university_admin)

## 8) Reports
- الطالب: إنشاء مسودة.
- المشرف: اعتماد/رفض؛ التعديل مغلق بعد الاعتماد.
- Admin الجامعة: قراءة فقط.
Endpoints:
- GET/POST `/api/reports/`
- GET/PATCH `/api/reports/<id>/`
- POST `/api/reports/<id>/approve/` (supervisor)
- POST `/api/reports/<id>/reject/` (supervisor)

## 9) Evaluations
- المريض: تقييم الجلسة/الطالب.
- المشرف: تقييم الطالب.
- الجامعة: عرض مجمع.
- حالة التقييم: draft → submitted → final (لا تعديل بعد final).
Endpoints:
- GET/POST `/api/evaluations/`
- GET/PATCH `/api/evaluations/<id>/`
- POST `/api/evaluations/<id>/submit/`
- POST `/api/evaluations/<id>/finalize/`
- GET `/api/evaluations/students/<student_id>/statistics/`

## 10) Support
- الكل ينشئ تذاكر.
- Admin الجامعة يرى تذاكر جامعته؛ Tech Support يرى الجميع.
Endpoints:
- GET/POST `/api/support/tickets/`
- GET/PATCH `/api/support/tickets/<id>/`

## 11) Backup
- IT Support فقط: إنشاء/استعادة/جدولة نسخ.
Endpoints (مثال):
- POST `/api/backup/jobs/`
- GET `/api/backup/jobs/`
- POST `/api/backup/jobs/<id>/restore/`

## 12) AI
- المريض: إنشاء/قراءة تشخيصه.
- الطالب/المشرف: قراءة.
- لا تعديل بعد الإنشاء (immutable).
Endpoints:
- POST `/api/ai/diagnosis/`
- GET `/api/ai/diagnosis/<id>/`

## 13) Audit
- تسجيل كل الأحداث الحساسة.
- Tech Support يرى الكل؛ Admin الجامعة يرى نطاق جامعته.
Endpoints:
- GET `/api/audit/logs/`
- GET `/api/audit/logs/<id>/`

## ملاحظات تشغيل واختبار
- تأكد من ضبط متغيرات البيئة وقاعدة البيانات قبل الاختبارات.
- اختبارات سريعة:
  - `python manage.py test apps.accounts`
  - `python manage.py test apps.messaging`
  - `python manage.py test apps.notifications` (للتأكد من الصلاحيات والقراءة/التحديث)
- Throttling مقترحة:
  - messaging: `30/min`
  - fcm token: `5/min`
  - login: طبق معدلات مناسبة لحماية من الهجمات.
