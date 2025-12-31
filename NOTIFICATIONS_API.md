# Notifications API (MediSmile)

نظام الإشعارات مركزي، مرتبط بأحداث حقيقية (Appointments, Reports, AI, Community, Audit). لا تُنشأ إشعارات عشوائياً.

## الأنواع (notification_type)
- مواعيد: `appointment_reminder`, `appointment_update_request`, `appointment_cancel_request`, `appointment_status_update`
- تقارير/تقييم/ذكاء اصطناعي: `report_submitted`, `report_reviewed`, `evaluation_submitted`, `ai_analysis_ready`
- مجتمع: `community_content_pending`, `community_content_approved`, `community_content_rejected`
- حالات/جلسات/رسائل: `case_created`, `case_assigned`, `case_status_changed`, `session_created`, `session_needs_review`, `session_reviewed`, `new_message`
- نظام/نسخ احتياطي/أمن: `system_alert`, `backup_status`, `security_event`

## النموذج (ملخص)
```json
{
  "id": "uuid",
  "sender": {"id": "uuid", "name": "System/User"},
  "recipient": {"id": "uuid", "name": "Target User"},
  "notification_type": "report_submitted",
  "priority": "low|normal|high|critical",
  "title": "New Report Submitted",
  "message": "A new report has been submitted by the student.",
  "status": "pending|accepted|rejected|info",
  "is_read": false,
  "proposed_changes": {},
  "payload": {},
  "target_type": "report",
  "target_object_id": "uuid",
  "appointment": {"id": "uuid"},
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z",
  "read_at": null
}
```

## الصلاحيات حسب الدور (مختصر)
- Patient: يستقبل إشعارات مواعيد/رسائل/AI جاهز؛ ينشئ فقط طلبات تعديل/إلغاء موعد.
- Student: يستقبل مراجعات التقارير، محتوى المجتمع، المواعيد؛ يمكنه إشعار المريض/المشرف المرتبط بحالة/موعد.
- Supervisor: يستقبل تقارير جديدة ومحتوى بانتظار المراجعة؛ يمكنه إشعارات مراجعة/إدارية.
- University Admin: يشاهد إشعارات جامعته (إدارية/دورية)؛ لا يرسل للمريض مباشرة.
- Tech Support: إشعارات النظام/النسخ الاحتياطي؛ وصول شامل.

## Endpoints

### 1) صندوق الإشعارات (Inbox)
- `GET /notifications/`
- Auth: Bearer
- يعيد إشعارات المستخدم الحالي فقط (مع Pagination).
- 200 OK: قائمة `Notification`.

### 2) تفاصيل إشعار
- `GET /notifications/{id}/`
- Auth: Bearer (مالك الإشعار أو ضمن نطاق الجامعة بحسب MatrixPermission)
- 200 OK: كائن الإشعار.

### 3) إنشاء إشعار (داخلي/نظامي)
- `POST /notifications/`
- Auth: Bearer (التحقق حسب الدور)
- Body:
```json
{
  "notification_type": "report_submitted",
  "priority": "normal",
  "recipient_id": "<uuid>",
  "sender_id": "<uuid|null>",
  "appointment_id": "<uuid|null>",
  "target_type": "report",          // case, report, message, ...
  "target_id": "<uuid>",
  "title": "New Report",
  "message": "A new report was submitted.",
  "proposed_changes": {},           // لطلبات التعديل/الإلغاء
  "payload": {}                     // بيانات إضافية للواجهة
}
```
- 201 Created: كائن الإشعار.

### 4) تحديث حالة/قراءة إشعار
- `PATCH /notifications/{id}/`
- Auth: Bearer (المستلم أو ضمن نطاق الجامعة)
- Body:
```json
{
  "is_read": true,
  "status": "accepted",
  "response_message": "Noted"
}
```
- 200 OK: كائن الإشعار بعد التحديث.

## Audit
- `notifications.created`
- `notifications.read`
- `notifications.status.changed`

## إرشادات Frontend
- لا تفترض نوع الإشعار: اعتمد على `notification_type` و `payload`.
- لا تحذف إشعارات: استخدم mark-as-read/status.
- استخدم Pagination للعرض.
- اعرض الأولوية بوضوح.
- النظام جاهز للتوسعة Real-Time (WebSocket لاحقاً).
