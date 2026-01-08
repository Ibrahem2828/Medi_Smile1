# قسم الذكاء الاصطناعي (AI Backend) — الوصف الاحترافي المثالي

## 1) الهدف العام
- محرك دعم قرار طبي/تعليمي لتحليل الحالات السنية مبدئيًا (صور + أعراض نصية).
- مساعدة المريض والطالب والمشرف على الفهم قبل التدخل البشري، دون استبدال القرار الطبي.
- ضمان الشفافية، الحوكمة، والتتبع الكامل لمخرجات الذكاء.
- ⚠️ الذكاء الاصطناعي لا يُنشئ حالة طبية ولا يصدر تشخيصًا نهائيًا؛ بل يقدم مقترحات خاضعة لموافقة الإنسان.

## 2) المبدأ المعماري (AI proposes — Humans decide — System records)
- مخرجات الذكاء = Proposals.
- القرار النهائي = المريض + المشرف.
- كل خطوة مسجّلة وقابلة للتدقيق.

## 3) البنية الداخلية
- **AIDiagnosis (apps/ai/models.py)**  
  - يمثل طلب تحليل واحد. حقول رئيسية: `patient`, `requested_by`, `case`, `status (pending/completed/failed/reviewed)`, `confidence_level`, `severity_level`, `urgency_level`, `ai_metadata` (نسخة كاملة), `diagnosis_label`, `primary_diagnosis`, `detected_findings`, `patient_explanation`, `report_text`, `recommendations`, `error_message`, `reviewed_by/at`.
  - `risk_flags` تحفظ ضمن `ai_metadata` (ترميز حر) عند توفرها من المزود.
- **فصل الذكاء عن الحالات (AI ≠ Case)**  
  - قسم الذكاء لا ينشئ Case. بعد موافقة المريض تُحوّل المخرجات إلى `AIAnalysisSession` و`AIProposedCase` في قسم الحالات، وهناك فقط يمكن أن تنشأ الحالة الطبية.
- **التصاريح**  
  - `CanRequestAIDiagnosis`, `CanAccessAIDiagnosis`, `CanReviewAIDiagnosis`, `CanViewAIHealth`: تضبط الوصول حسب الدور والجامعة.
- **الخدمات (apps/ai/services.py)**  
  - `request_ai_diagnosis`: يستقبل المدخلات، يستدعي Vision/NLP/Fusion، يوحّد النتائج، يخزن الخام والمنظّم، يسجل في Audit.
  - `review_ai_diagnosis`: اعتماد/رفض من المشرف، تحديث الحالة إلى `reviewed` وتوثيق القرار البشري.
- **التكاملات**  
  - `apps/ai/integrations/...`: إعدادات مزودي Vision/Text/Fusion مع timeouts وbase_url (health-ready).
- **الانتقاء (selectors.py)**  
  - `get_ai_diagnosis_queryset_for_user`: كل الاستعلامات تمر عبره لضمان نطاق الجامعة والدور.

## 4) دورة حياة التحليل
1) **طلب التحليل**: المريض يرسل أعراض نصية + صور → إنشاء `AIDiagnosis` بحالة `pending`.
2) **تنفيذ النماذج**: استدعاء Vision/Text/Fusion → `completed` أو `failed` مع سبب.
3) **عرض النتيجة**: متاحة للمريض/الطالب/المشرف وفق النطاق.
4) **مراجعة المشرف**: اعتماد/رفض → الحالة `reviewed` وتسجيل القرار.
5) **التوريد للحالات**: بعد موافقة المريض تُحوّل النتائج إلى Proposals في قسم الحالات؛ لا تُنشأ Case مباشرة هنا.

## 5) نقاط النهاية (apps/ai/urls.py)
- `POST /api/ai/diagnose/` (طلب تحليل) — throttled.
- `GET /api/ai/diagnoses/` (قائمة ضمن النطاق).
- `GET /api/ai/diagnoses/<id>/` (تفاصيل ضمن النطاق).
- `POST /api/ai/diagnoses/<id>/review/` (مراجعة مشرف).
- `GET /api/ai/health/` (جاهزية مزودي النماذج).
- `GET /api/ai/my-analysis/` (آخر تحليل للمريض).

## 6) الصلاحيات
- **Patient**: طلب تحليل، عرض تحليلاته فقط.
- **Student**: عرض التحليلات المرتبطة بحالاته التعليمية.
- **Supervisor**: عرض تحليلات الجامعة، مراجعة/اعتماد النتائج.
- **Tech Support**: مراقبة، تدقيق، health checks.
- ⚠️ جميع الاستعلامات مقيّدة بالجامعة والدور عبر selectors.

## 7) الحوكمة والأمان
- حفظ جميع ردود AI في `ai_metadata`، عدم الحذف (سجل تدقيق).
- توثيق الفرق بين قرار AI والقرار البشري (حالة `reviewed` + من اعتمد/رفض).
- Throttling لمنع إساءة الاستخدام.
- Health endpoint لمراقبة جاهزية المزودات.

## 8) التكامل مع بقية النظام
- **الحالات**: AI → Proposals → موافقة المريض → Case (داخل قسم الحالات فقط).
- **الإشعارات**: عند اكتمال/فشل/مراجعة يمكن تشغيل إشعارات (موصى بتفعيلها في الخدمات).
- **التقارير**: تحليل جودة الذكاء، مقارنة AI بالمشرف، تحسين النماذج مستقبلًا.

## 9) لماذا هذا التصميم مناسب
- أخلاقي (يفصل الآلة عن التشخيص النهائي).
- تعليمي (teaching-first).
- قابل للتوسع ومحكوم بالحواجز القانونية.
- واضح في فصل الأدوار والحوكمة (AI proposes — Humans decide — System records).
