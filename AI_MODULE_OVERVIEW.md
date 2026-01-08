# قسم الذكاء الاصطناعي (AI Backend) — وصف شامل عملي

## 1) الهدف والدور
- تقديم تحليل أولي ذكي للحالات السنية (نص + صور) لدعم القرار الطبي والتعليم السريري.
- الحفاظ على فصل واضح بين مخرجات الـAI (مقترحات) والقرارات البشرية (المريض/المشرف).
- تسجيل كل خطوة ومخرجات النماذج لأغراض التدقيق والحوكمة.

## 2) المكونات البرمجية
- **النماذج (apps/ai/models.py)**  
  - `AIDiagnosis`: تخزين نتيجة تحليل AI لحالة محددة. يتضمن الحالة، المريض، طالب/مشرف الطلب، مدخلات النص/الصور، المخرجات (diagnosis_label/primary_diagnosis/findings)، مستويات الثقة/الخطورة/الإلحاح، ونسخة كاملة `ai_metadata`. حالات التشغيل: `pending | completed | failed | reviewed`.
  - Enums: `DiagnosisStatus`, `ConfidenceLevel`, `SeverityLevel`, `UrgencyLevel`.
- **التصاريح (apps/ai/permissions.py)**  
  - `CanRequestAIDiagnosis`: يضبط من يمكنه طلب التحليل (المريض افتراضيًا، وأدوار أخرى وفق السياسة).
  - `CanAccessAIDiagnosis`: وصول مضبوط بالسياق (مريض/طالب/مشرف/دعم تقني).
  - `CanReviewAIDiagnosis`: للمشرفين فقط، على الحالات ضمن جامعتهم.
  - `CanViewAIHealth`: للتحقق من صحة مزودي النماذج.
- **السيريالايزرز (apps/ai/serializers.py)**  
  - `AIDiagnosisRequestSerializer`: استلام الأعراض والنصوص والصور لطلب جديد.
  - `AIDiagnosisSerializer`: إخراج قراءة كاملة للـAIDiagnosis.
  - `AIDiagnosisReviewSerializer`: اعتماد/رفض المشرف للنتيجة.
- **الخدمات (apps/ai/services.py)**  
  - `request_ai_diagnosis`: ينسق استدعاء محركات الـAI (نص/رؤية/دمج) عبر `integrations`، ينشئ سجل AIDiagnosis، ويعيد مقترحات (primary/next/all).
  - `review_ai_diagnosis`: يعتمد أو يرفض النتيجة، ويحدث حالة `reviewed`.
  - طبقة تدقيق: تستدعي `apps.audit.services.log_audit_event` لتوثيق كل عملية.
- **التكاملات (apps/ai/integrations/...)**  
  - تعريف نقاط الاتصال مع محركات الـAI الخارجية (FastAPI أو غيره) مع إعدادات الوقت والـbase_url في `integrations/endpoints.py` و `constants.py`.
- **الانتقاء (apps/ai/selectors.py)**  
  - `get_ai_diagnosis_queryset_for_user`: يعيد QuerySet مرشحًا حسب الدور والملكية والجامعة.

## 3) نقاط النهاية (apps/ai/urls.py → views.py)
- `POST /api/ai/diagnose/` → `create_ai_diagnosis`  
  - صلاحيات: `IsAuthenticated + CanRequestAIDiagnosis` + throttling.  
  - المدخلات: `symptoms_text`, `patient_id?`, `image_urls?[]`.  
  - المخرجات: diagnosis + `primary_suggestion`, `next_suggestion`, `all_suggestions`.
- `GET /api/ai/diagnoses/` → `AIDiagnosisListView`  
  - يعرض نتائج ضمن نطاق الدور (مريض/طالب/مشرف/جامعة/دعم).
- `GET /api/ai/diagnoses/<id>/` → `AIDiagnosisDetailView`  
  - صلاحيات كائنية عبر `CanAccessAIDiagnosis`.
- `POST /api/ai/diagnoses/<id>/review/` → `review_ai_diagnosis_view`  
  - صلاحيات: مشرف فقط (مع جامعات). يعتمد/يرفض ويحدّث الحالة إلى `reviewed`.
- `GET /api/ai/health/` → `ai_health_view`  
  - يعرض إعدادات مزودي الـAI (vision/text/fusion) للتحقق الصحي.
- `GET /api/ai/my-analysis/` → `my_ai_analysis`  
  - للمريض: يعيد أحدث تحليل مكتمل/مراجع مرتبط بآخر حالة، أو حالة “processing”.

## 4) دورة العمل
1) **طلب التحليل**: المريض (أو المفوض) يرسل أعراض/صور → `create_ai_diagnosis` → استدعاء محركات النص/الرؤية/الدمج → تخزين `AIDiagnosis` بحالة `pending/completed/failed`.
2) **عرض النتيجة**: قائمة/تفاصيل ضمن نطاق الصلاحيات.
3) **مراجعة المشرف**: `review_ai_diagnosis_view` يعتمد/يرفض → الحالة `reviewed`.
4) **التوريد للحالات**: النتائج تغذي `AIAnalysisSession` و `AIProposedCase` في قسم الحالات (انفصال تام: AI ≠ Case).

## 5) الحوكمة والأمان
- كل الطلبات تخضع لـ throttling ScopedRateThrottle.
- حفظ الـmetadata الخام في `ai_metadata` للتدقيق.
- مراجعات المشرف إلزامية قبل اعتبار النتيجة “مقبولة تعليميًا”.
- انتقاء QuerySets دائماً عبر `get_ai_diagnosis_queryset_for_user` لمنع تسرب البيانات بين الجامعات/الأدوار.

## 6) نقاط الربط مع بقية النظام
- **الحالات (cases)**: يتم إنشاء مقترحات حالات عبر `AIAnalysisSession`/`AIProposedCase` في قسم الحالات بعد قبول المريض، مع نقل `ai_metadata`.
- **الإشعارات**: يمكن توصيل إشعارات عند اكتمال/فشل التحليل أو بعد مراجعة المشرف (يُفعّل عبر طبقة الخدمات/الـsignals عند الحاجة).
- **التدقيق (audit)**: كل طلب/مراجعة يسجل في سجلات التدقيق.

## 7) للتطوير والتحسين
- إضافة Hooks للإشعارات الفورية عند `completed/failed/reviewed`.
- دعم تتبع الإصدارات للنماذج (model version) داخل `ai_metadata`.
- إضافة اختبارات تكامل مع مزودي الـAI (mocks) لتحسين الاستقرار.
- مراقبة SLA لمحركات النص/الرؤية/الدمج عبر health endpoint.
