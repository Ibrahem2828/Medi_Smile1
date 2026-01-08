# قسم الإشعارات (Notifications) — وصف شامل

## 1) الهدف
- إيصال التنبيهات الحرجة والمهام الإجرائية للمستخدمين (مريض/طالب/مشرف/أدمن جامعة/دعم تقني) مع سجل قابل للتتبع.
- دعم حالات قبول/رفض وتأكيد قراءة الإشعارات.
- ربط الإشعارات بسياق واضح (حالة/موعد/تقرير/محادثة) لسهولة المتابعة.

## 2) المكونات الرئيسة
- **النموذج (apps/notifications/models.py)**  
  - `Notification`: الحقول الأساسية تشمل `title`, `message`, `notification_type`, `priority`, `recipient`, `sender`, روابط اختيارية (`case`, `appointment`, `target_content_type/id`, `payload`)، وحالة `status` (`pending|accepted|rejected|info`) مع `is_read`, `response_message`, أزمنة الإنشاء والتحديث.
  - الأولويات: `low|normal|high|critical`.
- **الخدمات (apps/notifications/services.py)**  
  - دوال إنشاء إشعارات فردية وجماعية، مع إمكانية تمرير `payload` وسياقات الـContentType.
  - جسور تكامل مع سجل التدقيق (`audit_bridge.py`) لربط الأحداث النظامية بالإشعارات.
- **السيريالايزرز (apps/notifications/serializers.py)**  
  - `NotificationSerializer`: عرض كامل.
  - `NotificationCreateSerializer`: إنشاء إشعار مع تحقق من النوع/الأولوية والسياق.
  - `NotificationUpdateSerializer`: تحديث حالة القراءة أو قبول/رفض (status/response_message).
- **التصاريح (apps/notifications/permissions.py)**  
  - `IsAuthenticatedAndActive`: أساس الوصول.
  - `CanManageNotification`: يقيد القراءة/التحديث بالمتلقي الصحيح أو أدوار عليا عند الحاجة.
- **النقاط النهائية (apps/notifications/urls.py → views.py)**  
  - `GET /api/notifications/`: قائمة الإشعارات الخاصة بالمستخدم مع ترقيم.
  - `POST /api/notifications/`: إنشاء إشعار (يُستخدم من الخدمات أو أدوار مخولة).
  - `GET /api/notifications/<id>/`: عرض تفصيلي.
  - `PATCH /api/notifications/<id>/`: تحديث حالة القراءة أو قبول/رفض (status/response_message).

## 3) أنواع وسياقات الإشعارات
- أمثلة `notification_type`: `case_created`, `case_assigned`, `case_status_changed`, `appointment_created`, `appointment_rescheduled`, `appointment_cancelled`, `message_created`, `system_alert`.
- `payload` يسمح بنقل بيانات إضافية (مثل `room_id`, `request_id`, تغييرات مقترحة).
- ربط بالسياق عبر `target_content_type/id` يضمن تتبعاً دقيقاً للحدث.

## 4) الحوكمة والأمان
- كل إشعار مرتبط بمتلقي محدد؛ لا بثّ عام.
- احترام نطاق الجامعة عند الإنشاء (خصوصاً للأدمن/الدعم).
- دعم `is_read` مع طابع زمني، وقبول/رفض للمهام الإجرائية.
- إمكانية التتبع عبر `audit_bridge` وربط الأحداث النظامية بسجلات التدقيق.

## 5) تجربة المستخدم والأداء
- ترقيم (pagination) لعرض الإشعارات الحديثة أولاً.
- فلترة حسب `status`, `is_read`, `notification_type`, و/أو المرسل.
- الأولوية يمكن استخدامها لتسليط الضوء على الأحداث الحرجة (مثل `critical` للمواعيد أو الحالات الحرجة).

## 6) نقاط تكامل رئيسية
- **الحالات**: عند إنشاء/تعيين/تغيير حالة، إرسال إشعارات للمريض/الطالب/المشرف حسب الحدث.
  - مثال: خدمة `cases.services.create_case_from_proposal` يمكنها استدعاء إشعار `case_created`.
- **المواعيد**: إنشاء/إعادة جدولة/إلغاء/إكمال موعد → إشعارات للمشاركين.
- **المراسلة**: `message_created` عند ورود رسالة جديدة في غرفة الحالة.
- **الذكاء الاصطناعي**: إشعار عند اكتمال/فشل تحليل AI أو بعد مراجعة المشرف.
- **التدقيق**: أحداث حرجة يمكن دفعها إلى الدعم التقني أو الأدمن كـ `system_alert`.

## 7) توصيات تحسين
- تمكين عمليات bulk insert للإشعارات المتكررة لخفض الاستعلامات.
- إضافة WebSocket/FCM layer في طبقة عليا لإيصال فوري (مع بقاء السجل في DB).
- فرض سياسات حجم/طول للرسالة والعنوان.
- إضافة rate limit لأحداث الإشعار لمنع الضجيج.
