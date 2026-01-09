# Community & Support – Quick Test Guide

مسارات للتحقق بعد التعديلات الأخيرة.

## Community (Approvals & Moderation)

- **List pending approvals**  
  `GET /community/approvals/`  
  Auth: Bearer (moderator/supervisor/admin as per your RBAC)  
  Expect: 200 + قائمة المحتوى pending للمراجعة.

- **Approve content**  
  `POST /community/content/{id}/approve/`  
  Auth: Bearer (moderator/supervisor/admin)  
  Body: فارغ  
  Expect: 200 + المحتوى بعد الموافقة.

- **Reject content**  
  `POST /community/content/{id}/reject/`  
  Auth: Bearer (moderator/supervisor/admin)  
  Body:
  ```json
  {
    "reason": "غير مناسب للمنصة"
  }
  ```
  Expect: 200 + المحتوى بعد الرفض.

ملاحظات:
- استخدم `ContentViewSet` permissions: create/view/moderate/like/comment كما هو معمول به.
- تعتمد على `resolve_request_user` للتحقق من هوية المستخدم وصلاحيته.

## Support (Close Ticket)

- **Close ticket**  
  `POST /support/tickets/{id}/close/`  
  Auth: Bearer (creator of ticket OR university_admin OR tech_support)  
  Body: فارغ  
  Expect: 200 + تفاصيل التذكرة مع status = `closed` و `closed_at` محدثة.

ملاحظات:
- غير المالك يُرفض إلا إذا كان دوره tech_support أو university_admin ضمن النطاق.
- APIResponse يستخدم هيكل: `{status, message, data}` مع رسائل واضحة عند الرفض.


