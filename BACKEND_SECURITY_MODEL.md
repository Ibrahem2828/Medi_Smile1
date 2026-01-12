# نموذج الأمان في الباك إند

هذا الملف يوضح نموذج الأمان المعتمد في الباك إند حسب الكود والإعدادات الحالية.

## 1) المصادقة (Authentication)

### REST API
- الآلية: JWT عبر `djangorestframework-simplejwt`.
- كلاسّات المصادقة الافتراضية (`medismile/settings.py`):
  - `JWTAuthentication`
  - `SessionAuthentication`
  - `BasicAuthentication`
- استخدام التوكن: `Authorization: Bearer <access_token>`.
- إعدادات التوكن:
  - `ACCESS_TOKEN_LIFETIME`: 20 يوم
  - `REFRESH_TOKEN_LIFETIME`: 30 يوم
  - `ROTATE_REFRESH_TOKENS`: مفعّل
  - `BLACKLIST_AFTER_ROTATION`: مفعّل
  - `UPDATE_LAST_LOGIN`: مفعّل

### WebSocket
- البروتوكول: `ws://` أو `wss://` (Channels).
- المصادقة: `AuthMiddlewareStack` (يعتمد على الجلسة/الكوكيز).
- المسار: `/ws/chat/<room_id>/` (راجع `apps/messaging/routing.py`).
- ملاحظة: JWT غير مفعّل للـ WebSocket إلا بإضافة Middleware مخصص.

## 2) التفويض (Authorization)

### النموذج الأساسي
التفويض يمر بعدة طبقات:
1. **الدور** (RBAC): `patient`, `student`, `supervisor`, `university_admin`, `tech_support`.
2. **الملكية**: المستخدم يجب أن يكون مالكًا أو مشاركًا في المورد.
3. **نطاق الجامعة**: المستخدم يجب أن ينتمي لنفس الجامعة الخاصة بالمورد.
4. **حالة المورد**: يجب أن تكون الحالة مناسبة للإجراء.

### المصفوفة المركزية للصلاحيات
بعض الموارد تستخدم مصفوفة صلاحيات موحدة:
- المصفوفة: `medismile/permissions/matrix.py`
- المقيّم: `medismile/permissions/checker.py`
- التكامل مع DRF: `medismile/permissions/drf.py` عبر `MatrixPermission`

ترتيب التحقق:
- المستخدم مصادق
- المستخدم نشط
- الدور مسموح
- فحص الملكية (اختياري)
- فحص نطاق الجامعة (اختياري)
- فحص الحالة (اختياري)

### صلاحيات على مستوى التطبيقات
عدة تطبيقات تستخدم صلاحيات مخصصة في `permissions.py` أو داخل الـ views، مثل:
- `apps/cases/permissions.py`
- `apps/evaluations/permissions.py`
- `apps/messaging/permissions.py`
- `apps/appointments` (ضمن منطق الـ views)

هذه الصلاحيات تتحقق عادة من:
- أطراف الحالة المشاركين
- الصلاحيات حسب الدور
- نطاق الجامعة
- صحة الانتقال بين الحالات

## 3) الأدوار والملفات الشخصية

الأدوار معرفة في `accounts.User.role`.
ولكل دور ملف شخصي مربوط بالجامعة:
- `PatientProfile`
- `StudentProfile`
- `SupervisorProfile`
- `UniversityAdminProfile`
- `TechSupportProfile`

يتم استخدام هذه الملفات للتحقق من نطاق الجامعة والصلاحيات.

## 4) نطاق الجامعة

نطاق الجامعة يتم فرضه عبر:
- التحقق من جامعة الملف الشخصي (مثل `supervisorprofile_profile.university_id`)
- فلاتر في الاستعلامات والـ selectors
- التحقق داخل الـ serializers و`clean()` في الموديلات

## 5) التحقق من الحالة (State Guards)

التحقق من الحالة يمنع الإجراءات غير الصحيحة:
- انتقالات الحالة (`Case.ALLOWED_TRANSITIONS`)
- مراجعة الجلسات (`CaseSession`)
- صلاحية الدردشة (`is_room_chat_open`)
- سير التقييمات (`EvaluationStatus` و`is_locked`)

## 6) تحديد المعدّل (Throttling)

تم ضبطه في `medismile/settings.py`:
- `ai-diagnose`: 5/دقيقة
- `ai-review`: 30/ساعة
- `ai-health`: 120/ساعة
- `ai-my-analysis`: 30/ساعة
- `messaging`: 60/دقيقة

## 7) CORS و CSRF

- CORS: `CORS_ALLOW_ALL_ORIGINS = True`
- CSRF: ضبط `CSRF_TRUSTED_ORIGINS` حسب بيئة التشغيل

## 8) سجل التدقيق (Audit Logging)

الأحداث الحساسة يتم تسجيلها عبر `apps.audit.services.log_audit_event`:
- تغييرات الحالات
- رسائل المحادثات
- عمليات الذكاء الاصطناعي
- مراحل التقييمات

## 9) أعلام التطوير والاختبار

يوجد خيار `DISABLE_BUSINESS_RULES` في `medismile/utils/auth.py` لتجاوز
قواعد الأمان في بيئة التطوير فقط. يجب أن يكون معطّلًا في الإنتاج.

## 10) شكل الأخطاء القياسي

أخطاء الصلاحيات غالبًا تكون:
- `403` مع `permission_denied:<reason>`
- `401` عند غياب/انتهاء التوكن

صياغة الخطأ تتم عبر:
`medismile/utils/exceptions.custom_exception_handler`
