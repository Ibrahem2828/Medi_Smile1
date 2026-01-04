# MediSmile Backend — تطبيقات وخدمات

ملخص احترافي لكل التطبيقات وما تقدمه من واجهات وأدوار:

## accounts
- نماذج: Role, User + ملفات الأدوار (Patient/Student/Supervisor/University Admin/Tech Support).
- صلاحيات: IsAuthenticatedAndActive، إنشاء أدوار وحسابات حسب RBAC.
- إدارة: Admin محسّن بملفات Inlines لكل دور.
- مسارات بارزة: تسجيل الدخول حسب الدور، إنشاء المستخدمين، `me/*` لتحديث الملف الشخصي.

## ai
- خدمة التشخيص الثلاثي (نص/رؤية/Fusion) مع دمج النتائج.
- مسارات: `POST /api/ai/diagnosis/` تعيد diagnosis + primary/next/all_suggestions، مراجعة مشرف، health check.
- نماذج: AIDiagnosis مع حالات (pending/completed/failed/reviewed) والـ metadata.

## cases
- نماذج: Case, CaseHistory, CaseAssignmentRequest, CaseSession.
- تدفق AI حرِج: `POST /api/cases/ai/create/` (المريض) لإنشاء حالة حرجة بـ is_ai_critical و ai_metadata، `assign-supervisor`، طلبات الطلاب، قرار المشرف (decision)، جلسات العلاج.
- صلاحيات: CanManageCaseStatus، CanAssignSupervisor، CanRequestAssignment، إلخ.
- مخرجات أساسية: حالات عامة للطلاب داخل نفس الجامعة فقط.

## universities
- نماذج: University, Faculty, AcademicProgram, AcademicYear, Course.
- صلاحيات: Tech Support يدير الجميع، University Admin يدير جامعته فقط (مسار `universities/me/update/`).
- دور الطالب/المشرف محصور بجامعة واحدة لكل أدمن جامعة.
- مسارات: list/create/update/delete للكيانات داخل نطاق الجامعة.

## support
- تذاكر الدعم الفني: SupportTicket + SupportTicketResponse.
- صلاحيات: Tech Support يرى الكل؛ University Admin يرى تذاكر من نفس الجامعة (عبر ملفات المستخدم)؛ المالك يرى تذكرته.
- إشعارات: عند إنشاء تذكرة أو الردود بين المالك والدعم.

## notifications
- نموذج Notification عام مع ContentType للربط بأي كائن (حالة، موعد، محتوى مجتمع…).
- أنواع إشعارات جاهزة: case_created/case_assigned/case_status_changed، system_alert، وغيرها.

## appointments
- مواعيد مرتبطة بالحالات (patient/student/supervisor)، منع الحذف، إنشاء يتم عبر الـ API.

## attachments
- مرفقات طبية/أكاديمية مرتبطة بالحالات أو المواعيد، قراءة فقط من الـ admin، منع الحذف/الإضافة من الـ admin.

## audit
- سجل تدقيق مركزي لكل العمليات الحرجة (logs)، قراءة فقط من الـ admin.

## community
- محتوى المجتمع: إنشاء/موافقة/رفض، صلاحيات حسب الدور، حماية الحذف في الـ admin.

## evaluations
- تقييمات الطلاب على الكيانات (case/session/appointment) مع حالات draft/submitted/final.

## reports
- تقارير ناتجة عن النظام/الخدمات، قراءة فقط وإنشاء من الخدمة، منع الحذف في الـ admin.

## messaging
- غرف محادثة مرتبطة بالحالة (مريض/طالب) ورسائل، قراءة فقط من الـ admin، منع الحذف.

## backup
- مهام النسخ الاحتياطي (قراءة في الـ admin)، ألوان الحالة، منع التعديل/الحذف.

## تكامل AI مع الحالات
- عند تشخيص AI: تُعاد primary/next/all_suggestions. المريض يرسل `ai_report` إلى `/api/cases/ai/create/` لفتح حالة حرجة (pending_assignment, is_public=True) مرتبطة بجامعة مختارة.
- إشعارات للمشرفين في الجامعة عند إنشاء الحالة الحرجة، وقرارات المشرف/الطلاب موجودة.

## ملاحظات تشغيلية
- يلزم تشغيل الترقيات: الحقول الجديدة مثل `is_ai_critical`, `ai_metadata` في Case، وتعزيز صلاحيات الجامعة.
- تأكد من مزامنة الواجهة الأمامية مع الحقول/الاستجابات الجديدة (suggestions، AI case flow، إشعارات الدعم). 
