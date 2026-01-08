# قسم المرفقات (Attachments) — وصف شامل

## 1) الهدف
- حفظ الملفات الطبية/التعليمية المرتبطة بالحالات والمواعيد (صور قبل/بعد، تقارير، وثائق داعمة).
- ضمان سلامة البيانات والتوافق مع صلاحيات الأدوار والجامعة.
- إبقاء سجل تدقيق قابل للتتبع دون السماح بحذف غير مصرح.

## 2) المكونات الرئيسة
- **النموذج (apps/attachments/models.py)**  
  - `Attachment`: يرتبط بـ `Case` و`Appointment` محددين.  
    - الحقول: `file`, `original_filename`, `file_size`, `mime_type`, `file_category (image/document/video/other)`, `attachment_type (before_image/after_image/report/other)`, `is_visible_to_patient`, علاقات (`case`, `appointment`, `uploaded_by` طالب)، أزمنة الإنشاء.
    - قواعد: الطالب فقط يرفع؛ الموعد يجب أن يتبع الحالة نفسها؛ صورة بعد تتطلب وجود صورة قبل.
- **التصاريح (apps/attachments/permissions.py)**  
  - `CanViewAttachment`:  
    - طالب: مرفقاته فقط.  
    - مريض: مرفقات حالته المسموح بها `is_visible_to_patient`.  
    - مشرف: مرفقات الحالات التي يشرف عليها.  
    - أدمن جامعة: ضمن جامعته.  
    - Tech Support: قراءة كاملة.  
  - `CanCreateAttachment`: الطلاب فقط.  
  - `CanDeleteAttachment`: الطالب يحذف مرفقه فقط (سياسة صارمة).
- **السيريالايزرز (apps/attachments/serializers.py)**  
  - `AttachmentSerializer`: عرض المرفقات + `file_url` عبر `storage_backends`.  
  - `AttachmentCreateSerializer`: تحقق من المالك (طالب)، صحة الموعد، يحدد الفئة (صورة/وثيقة) تلقائيًا، ويحفظ عبر backend التخزين مع تنظيف في حال الفشل.
- **التخزين (apps/attachments/storage_backends.py)**  
  - دوال `get_storage_backend` و`generate_attachment_path` لمرونة اختيار التخزين (محلي/سحابي) ومسارات منظمة.
- **واجهات API (apps/attachments/urls.py → views.py)**  
  - `GET /api/attachments/` و`POST /api/attachments/`  
    - القائمة: حسب دور المستخدم كما في `CanViewAttachment`.  
    - الإنشاء: الطالب فقط عبر `AttachmentCreateSerializer`.  
  - `GET /api/attachments/<id>/` عرض مرفق واحد (مع صلاحيات).  
  - لا يوجد تحديث/حذف عام (حذف محدود للطالب وفق السياسة).

## 3) دورة العمل
1) الطالب المعيّن على الموعد يرفع ملفًا (صورة/وثيقة) → إنشاء Attachment مربوط بالموعد والحالة.
2) الملف يُخزن عبر backend ويُسجل الميتاداتا (اسم، حجم، mime).
3) صلاحيات العرض تحدد من يرى المرفق (المريض مشروط بـ `is_visible_to_patient`).
4) المشرف/الأدمن/الدعم التقني يمكنهم القراءة ضمن نطاق الجامعة (حسب الدور).

## 4) الحوكمة والأمان
- لا يسمح برفع مرفقات خارج سياق موعد/حالة صحيحة.  
- سياسات صارمة للطالب (مالك فقط) في الرفع والحذف؛ المريض لا يرفع.  
- تمييز صورة بعد يتطلب صورة قبل لتفادي فقدان التسلسل السريري.  
- تخزين آمن عبر backend موحّد مع إمكانية التبديل إلى سحابي.  
- سجلات التدقيق يمكن تفعيلها على الأحداث (إنشاء/حذف) عبر إشعارات أو audit services إن لزم.

## 5) الاختبارات والضبط
- اختبارات تغطي رفع الطالب، منع غير المالك، تطابق الموعد/الحالة، وإخفاء المرفقات عن المريض عند `is_visible_to_patient=False` (راجع `apps/attachments/tests.py`).  
- يُنصح بتفعيل قيود حجم ونوع الملف في إعدادات المشروع (limit upload size + allowed content types) عبر DRF/Storage middleware.
