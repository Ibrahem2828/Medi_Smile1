# قسم الإشعارات (Notifications Backend) — الوصف الاحترافي الشامل

## 1) الهدف
- محرك التنبيه غير المتزامن لتحويل أحداث النظام إلى رسائل مفهومة للمستخدمين (مريض/طالب/مشرف/أدمن جامعة/دعم تقني).
- دعم القرارات الإجرائية (قبول/رفض/متابعة) مع سجل تدقيق قابل للتتبع.
- الإشعار نتيجة حدث (Event-driven)، وليس محتوى ينشئه المستخدم يدويًا.

## 2) الفلسفة المعمارية
- Notifications are system-triggered, not user-generated.
- Action → Service → Audit → Notification: الإنشاء يتم من الخدمات/الإشارات/المهام المجدولة (Celery)، لا من واجهة المستخدم مباشرة.
- إشعار واحد لمتلقي واحد، مرتبط بسياق واضح.

## 3) الكيان الأساسي: Notification
- الحقول الأساسية: `title`, `message`, `notification_type`, `priority (low|normal|high|critical)`, `recipient`, `sender`, `status (pending|accepted|rejected|info)`, `is_read`, `response_message`, `payload (JSON مرن)`.
- العلاقات: `case`, `appointment`, أو `target_content_type/id` لسياقات أخرى، مع `created_at`, `updated_at`.
- التصميم الحالي مرن ويدعم جميع السيناريوهات.

## 4) أنواع الإشعارات (أمثلة)
- الحالات: `case_created`, `case_accepted`, `case_rejected`, `case_assignment_requested`, `case_assigned`.
- المواعيد: `appointment_created`, `appointment_rescheduled`, `appointment_cancelled`, `appointment_reminder`, `appointment_started`.
- الذكاء الاصطناعي: `ai_analysis_completed`, `ai_analysis_failed`, `ai_review_required`, `ai_review_completed`.
- المراسلة: `message_created`.
- النظام: `system_alert`, `security_event`.
- `payload` يحمل بيانات إضافية دون تعديل قاعدة البيانات.

## 5) دورة الحياة
1) الإنشاء: من Service/Signal/Task يحدد المتلقي والسياق والأولوية؛ الإشعار يظهر للمتلقي فقط ضمن نطاق الجامعة/الملكية.
2) التفاعل: القراءة (`is_read=true`)، القبول/الرفض للإشعارات الإجرائية (`status`).
3) التتبع: محفوظ، غير قابل للحذف، قابل للتدقيق.

## 6) الصلاحيات
- LIST/RETRIEVE/UPDATE: Patient/Student/Supervisor/University Admin/Tech Support وفق مصفوفة الصلاحيات المركزية ونطاق الجامعة.
- CREATE: غير مسموح يدويًا للمستخدمين؛ يتم فقط عبر النظام (الخدمات/الإشارات/المهام المجدولة).

## 7) التكامل مع النظام
- الحالات: إشعارات عند إنشاء/مراجعة/إسناد حالة.
- المواعيد: تذكيرات قبل الموعد، تحديثات إعادة الجدولة/الإلغاء/البدء.
- الذكاء الاصطناعي: اكتمال/فشل التحليل، طلب/اعتماد مراجعة المشرف.
- المراسلة: إشعار برسالة جديدة في غرفة الحالة.
- التدقيق: كل إشعار مهم مرتبط بحدث مدون في Audit لبيان السبب والسياق.

## 8) تحسينات اختيارية (لا تكسر الكود)
- توحيد الإنشاء عبر خدمة واحدة `notifications.services.send_notification(...)`.
- دعم Bulk notifications للأحداث الجماعية (reminders/system_alerts).
- تكامل أعمق مع Celery لجدولة التذكيرات والمتابعات.
- ضبط استخدام `status` للإشعارات الإجرائية فقط، والمعلوماتية تعتمد على `is_read`.
- إضافة طبقة WebSocket/FCM للتوصيل الفوري مع بقاء السجل في DB.

## 9) الأمان والأداء
- Pagination مفعّل؛ لا بثّ عام؛ scoping حسب الجامعة والملكية؛ حفظ دائم دون حذف.
- يمكن فرض طول/حجم للعنوان/الرسالة وإضافة rate limit لمنع الضجيج.

## 10) الحكم النهائي
- التصميم الحالي احترافي، متوافق مع الحالات/المواعيد/الذكاء الاصطناعي/الصلاحيات/التدقيق، وجاهز للإنتاج.
