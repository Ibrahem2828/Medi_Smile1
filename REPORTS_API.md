# Reports API Reference

الواجهات التالية تغطي إنشاء/مراجعة/إدارة تقارير MediSmile، مع الصلاحيات والأجسام المتوقعة.

## صلاحيات الأدوار
- Student: إنشاء تقرير حالة/جلسة/صور عبر `/reports/submit/`، عرض تقاريره فقط.
- Supervisor: إنشاء تقرير (كل الأنواع)، مراجعة تقرير، عرض تقارير طلاب جامعته.
- University Admin: عرض كل تقارير جامعته، تبديل `is_active`.
- Tech Support: عرض كل التقارير، تبديل `is_active`.

## 1) إنشاء تقرير (Supervisors/Admin/Tech)
- Endpoint: `POST /reports/generate/`
- Auth: Bearer (role ∈ {supervisor, university_admin, tech_support})
- Body:
```json
{
  "student_id": "<uuid>",
  "report_type": "academic|evaluation|summary|media_report|supervisor_review|administrative|clinical_case|session_report|other",
  "case_id": "<uuid|null>",
  "session_id": "<uuid|null>",
  "title": "Semester Evaluation",
  "description": "Overall performance",
  "content": "Rich text / markdown",
  "file_url": "/media/reports/eval.pdf",
  "attachments": [{"type": "file", "url": "/media/reports/eval.pdf"}],
  "snapshot_data": {},
  "score": 92
}
```
- Response 201: تقرير كامل (انظر نموذج الاستجابة أدناه).

## 2) تقديم تقرير (Student)
- Endpoint: `POST /reports/submit/`
- Auth: Bearer (role = student)
- Body:
```json
{
  "report_type": "clinical_case|session_report|media_report",
  "case_id": "<uuid>",
  "session_id": "<uuid|null>",
  "title": "Root Canal – Final",
  "description": "تفاصيل مختصرة",
  "content": "تفاصيل إجرائية...",
  "attachments": [
    {"type": "before", "url": "/media/reports/before.jpg"},
    {"type": "after",  "url": "/media/reports/after.jpg"}
  ]
}
```
- Response 201: تقرير كامل.

## 3) مراجعة تقرير (Supervisor)
- Endpoint: `POST /reports/{id}/review/`
- Auth: Bearer (role = supervisor)
- Body:
```json
{
  "feedback": "Excellent diagnosis and execution",
  "score": 95
}
```
- Response 200: تقرير مع تحديث `feedback/score/reviewed_at/supervisor`.

## 4) تبديل ظهور تقرير (Admin/Tech)
- Endpoint: `PATCH /reports/{id}/`
- Auth: Bearer (role ∈ {university_admin, tech_support})
- Body:
```json
{ "is_active": false }
```
- Response 200: تقرير محدّث بحقل `is_active`.

## 5) قائمة التقارير (Scoped)
- Endpoint: `GET /reports/`
- Auth: Bearer
- Query (اختياري): `student_id`, `university_id`, `report_type`
- Response 200: قائمة تقارير ضمن نطاق الدور:
  - Student → تقاريره فقط (الفعالة)
  - Supervisor → تقارير طلاب جامعته
  - University Admin → تقارير جامعته
  - Tech Support → كل التقارير

## 6) تقارير الطالب (Scoped)
- Endpoint: `GET /reports/students/{student_id}/`
- Auth: Bearer
- Response 200: قائمة تقارير الطالب ضمن نطاق الدور.

## 7) تقارير الجامعة (Scoped)
- Endpoint: `GET /reports/universities/{university_id}/`
- Auth: Bearer
- Response 200: قائمة تقارير الجامعة ضمن نطاق الدور.

## 8) تقرير مفرد
- Endpoint: `GET /reports/{id}/`
- Auth: Bearer (حسب صلاحية العرض)
- Response 200: تقرير مفرد.

## نموذج استجابة التقرير (مثال عام)
```json
{
  "id": "<uuid>",
  "report_type": "clinical_case",
  "case_id": "<uuid|null>",
  "session_id": "<uuid|null>",
  "title": "Root Canal – Final Report",
  "description": "شرح موجز",
  "content": "تفاصيل كاملة ...",
  "file_url": "/media/reports/eval.pdf",
  "attachments": [
    {"type": "before", "url": "/media/reports/before.jpg"},
    {"type": "after",  "url": "/media/reports/after.jpg"}
  ],
  "snapshot_data": {},
  "score": 92,
  "feedback": "Excellent diagnosis",
  "reviewed_at": "2025-01-01T12:00:00Z",
  "student": "<uuid>",
  "student_name": "Student Name",
  "supervisor": "<uuid|null>",
  "supervisor_name": "Supervisor Name",
  "university": "<uuid>",
  "university_name": "University Name",
  "generated_by": "<uuid>",
  "generated_by_name": "Supervisor Name",
  "is_active": true,
  "generated_at": "2025-01-01T12:00:00Z",
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:05:00Z"
}
```

## ملاحظات على عدم التعديل (Immutability)
- الحقول الجوهرية (student/university/type/case/session/content/attachments/… إلخ) لا تتغير بعد الإنشاء.
- التعديلات المسموحة فقط: `is_active` (Admin/Tech) و `feedback/score/reviewed_at/supervisor` عبر مراجعة المشرف.

## Audit & Notifications
- Audit actions: `reports.report.submitted`, `reports.report.generated`, `reports.report.reviewed`, `reports.report.visibility_changed`, `reports.media.uploaded`.
- Notifications: إشعار المشرف عند تقرير جديد من الطالب، إشعار الطالب عند مراجعة المشرف.
