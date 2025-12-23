# 📚 MediSmile Backend - توثيق شامل للمشروع

## 📋 جدول المحتويات

1. [نظرة عامة على المشروع](#نظرة-عامة-على-المشروع)
2. [المتطلبات والتقنيات المستخدمة](#المتطلبات-والتقنيات-المستخدمة)
3. [البنية الأساسية للمشروع](#البنية-الأساسية-للمشروع)
4. [التطبيقات والوحدات](#التطبيقات-والوحدات)
5. [نظام المصادقة والصلاحيات](#نظام-المصادقة-والصلاحيات)
6. [APIs والواجهات](#apis-والواجهات)
7. [سيناريو عمل المشروع](#سيناريو-عمل-المشروع)
8. [الإعداد والتشغيل](#الإعداد-والتشغيل)
9. [أمثلة عملية](#أمثلة-عملية)

---

## 📖 نظرة عامة على المشروع

**MediSmile Backend** هو نظام إدارة شامل لمنصة طبية تعليمية تربط بين المرضى والطلاب والمشرفين في الجامعات. يوفر النظام بيئة متكاملة لإدارة الحالات الطبية، المواعيد، التقييمات، والمحتوى التعليمي.

### الهدف من المشروع

- توفير منصة تعليمية طبية متكاملة
- إدارة الحالات السريرية للطلاب
- تنسيق المواعيد بين المرضى والمشرفين والطلاب
- تتبع وتقييم أداء الطلاب
- بناء مجتمع تعليمي طبي تفاعلي
- نظام دعم تقني متكامل

### المميزات الرئيسية

✅ **إدارة متعددة المستخدمين**: مرضى، طلاب، مشرفين، إداريي جامعات، دعم تقني  
✅ **نظام الحالات السريرية**: إدارة كاملة لدورة حياة الحالات الطبية  
✅ **إدارة المواعيد**: جدولة وتتبع المواعيد الطبية  
✅ **نظام التقييمات**: تقييم شامل للمرضى والطلاب والمشرفين  
✅ **المحتوى المجتمعي**: مقالات ومصادر تعليمية  
✅ **نظام الرسائل**: محادثات مباشرة بين المستخدمين  
✅ **الذكاء الاصطناعي**: تحليل الأعراض والتشخيص المساعد  
✅ **نظام الإشعارات**: إشعارات فورية للمستخدمين  
✅ **نظام النسخ الاحتياطي**: نسخ احتياطية تلقائية  
✅ **نظام الدعم التقني**: إدارة طلبات الدعم والمشاكل التقنية  
✅ **التدقيق والأمان**: تتبع جميع العمليات والتحسينات الأمنية

---

## 🛠 المتطلبات والتقنيات المستخدمة

### التقنيات الأساسية

- **Python 3.8+**
- **Django 4.2.11** - إطار العمل الرئيسي
- **Django REST Framework 3.15.2** - بناء APIs
- **PostgreSQL** - قاعدة البيانات الرئيسية
- **Redis** - للتخزين المؤقت وCelery
- **Celery 5.3.4** - للمهام غير المتزامنة
- **Channels 4.0.0** - للـ WebSocket (المحادثات المباشرة)
- **Firebase Admin** - للإشعارات الفورية

### المكتبات الأساسية

```txt
djangorestframework==3.15.2
djangorestframework-simplejwt==5.3.1  # JWT Authentication
django-cors-headers==4.3.1            # CORS
django-filter==23.5                   # Filtering
celery==5.3.4                         # Async tasks
channels==4.0.0                       # WebSockets
channels-redis==4.2.0                 # Redis channel layer
firebase-admin                        # Push notifications
psycopg2-binary                      # PostgreSQL adapter
python-dotenv==1.0.1                  # Environment variables
pillow                               # Image processing
boto3==1.34.131                      # AWS S3 (for backups)
django-storages==1.14.2              # Storage backends
```

---

## 🏗 البنية الأساسية للمشروع

### هيكل المجلدات

```
medismileBackend/
├── apps/                          # جميع التطبيقات
│   ├── accounts/                  # إدارة المستخدمين والمصادقة
│   ├── universities/              # إدارة الجامعات والكورسات
│   ├── cases/                     # إدارة الحالات السريرية
│   ├── appointments/              # إدارة المواعيد
│   ├── evaluations/               # نظام التقييمات
│   ├── community/                 # المحتوى المجتمعي
│   ├── messaging/                 # نظام الرسائل
│   ├── ai/                        # الذكاء الاصطناعي
│   ├── notifications/             # نظام الإشعارات
│   ├── attachments/               # إدارة الملفات
│   ├── audit/                     # نظام التدقيق
│   ├── reports/                   # التقارير
│   ├── backup/                    # النسخ الاحتياطية
│   └── support/                   # الدعم التقني
├── medismile/                     # إعدادات المشروع الرئيسية
│   ├── settings.py               # الإعدادات
│   ├── urls.py                   # URLs الرئيسية
│   ├── wsgi.py                   # WSGI config
│   ├── asgi.py                   # ASGI config
│   └── celery.py                 # Celery config
├── media/                         # الملفات المرفوعة
├── static/                        # الملفات الثابتة
├── logs/                          # ملفات السجلات
├── manage.py                      # Django management script
├── requirements.txt               # المتطلبات
└── README.md                      # هذا الملف
```

---

## 📦 التطبيقات والوحدات

### 1. Accounts (الحسابات) - `apps.accounts`

**الوظيفة**: إدارة جميع أنواع المستخدمين والمصادقة

#### النماذج (Models):
- **User**: المستخدم الرئيسي (UUID كـ primary key)
- **PatientProfile**: ملفات المرضى
- **StudentProfile**: ملفات الطلاب
- **SupervisorProfile**: ملفات المشرفين
- **UniversityAdminProfile**: ملفات إداريي الجامعات
- **TechSupportProfile**: ملفات فريق الدعم التقني

#### الأدوار (Roles):
- `patient` - المريض
- `student` - الطالب
- `supervisor` - المشرف
- `university_admin` - مسؤول الجامعة
- `tech_support` - الدعم التقني

---

### 2. Universities (الجامعات) - `apps.universities`

**الوظيفة**: إدارة الجامعات والكورسات

#### النماذج:
- **University**: معلومات الجامعة
- **Course**: الكورسات والبرامج الدراسية

---

### 3. Cases (الحالات السريرية) - `apps.cases`

**الوظيفة**: إدارة الحالات الطبية والسريرية

#### النماذج:
- **Case**: الحالة الطبية
  - الحالات: `open`, `assigned`, `in_progress`, `completed`, `cancelled`
  - الأولويات: `low`, `medium`, `high`, `urgent`
- **CaseHistory**: سجل تغييرات الحالة
- **CaseAssignmentRequest**: طلبات إسناد الحالات للطلاب

---

### 4. Appointments (المواعيد) - `apps.appointments`

**الوظيفة**: إدارة المواعيد الطبية

#### النماذج:
- **Appointment**: الموعد الطبي
  - الحالات: `scheduled`, `confirmed`, `in_progress`, `completed`, `cancelled`, `no_show`

---

### 5. Evaluations (التقييمات) - `apps.evaluations`

**الوظيفة**: نظام تقييم شامل

#### النماذج:
- **Evaluation**: التقييم
  - أنواع المقيمين: `patient`, `supervisor`, `student`, `university`, `admin`

---

### 6. Community (المجتمع) - `apps.community`

**الوظيفة**: المحتوى المجتمعي التعليمي

#### النماذج:
- **Content**: المحتوى (مقالات، فيديوهات، مستندات)
  - الأنواع: `article`, `video`, `document`, `image`, `link`
  - الفئات: `medical`, `educational`, `research`, `news`, `general`

---

### 7. Messaging (الرسائل) - `apps.messaging`

**الوظيفة**: نظام محادثات مباشرة (WebSocket)

#### النماذج:
- **Room**: غرفة المحادثة (بين مستخدمين)
- **Message**: الرسائل

---

### 8. AI (الذكاء الاصطناعي) - `apps.ai`

**الوظيفة**: تحليل الأعراض والتشخيص المساعد

#### النماذج:
- **AIDiagnosis**: تشخيص AI
  - مستويات الثقة: `low`, `medium`, `high`

---

### 9. Notifications (الإشعارات) - `apps.notifications`

**الوظيفة**: نظام إشعارات شامل

#### النماذج:
- **Notification**: الإشعار
  - الأنواع: طلبات تحديث/إلغاء المواعيد، تأكيد المواعيد، طلبات الموافقة على المحتوى

---

### 10. Support (الدعم التقني) - `apps.support`

**الوظيفة**: إدارة طلبات الدعم التقني

#### النماذج:
- **SupportTicket**: طلب الدعم
  - الفئات: `technical`, `account`, `feature`, `bug`, `other`
  - الأولويات: `urgent`, `medium`, `low`
  - الحالات: `open`, `in_progress`, `resolved`, `closed`
- **SupportTicketResponse**: الردود على الطلبات

---

### 11. Attachments (المرفقات) - `apps.attachments`

**الوظيفة**: إدارة الملفات المرفوعة

---

### 12. Audit (التدقيق) - `apps.audit`

**الوظيفة**: تتبع وتدقيق جميع العمليات

---

### 13. Reports (التقارير) - `apps.reports`

**الوظيفة**: إنشاء وتوليد التقارير

---

### 14. Backup (النسخ الاحتياطية) - `apps.backup`

**الوظيفة**: النسخ الاحتياطية التلقائية واليدوية

---

## 🔐 نظام المصادقة والصلاحيات

### JWT Authentication

النظام يستخدم **JWT (JSON Web Tokens)** للمصادقة:

#### Endpoints:
- `POST /api/v1/token/` - الحصول على Access Token و Refresh Token
- `POST /api/v1/token/refresh/` - تحديث Access Token
- `POST /api/v1/token/verify/` - التحقق من صحة Token
- `POST /api/v1/accounts/login/` - تسجيل الدخول (مع JWT)
- `POST /api/v1/accounts/logout/` - تسجيل الخروج (Blacklist Token)

#### إعدادات JWT:
```python
ACCESS_TOKEN_LIFETIME: 60 minutes
REFRESH_TOKEN_LIFETIME: 7 days
ROTATE_REFRESH_TOKENS: True
BLACKLIST_AFTER_ROTATION: True
```

### الصلاحيات (Permissions)

كل تطبيق لديه صلاحيات مخصصة:
- **IsPatient**: للمرضى فقط
- **IsStudent**: للطلاب فقط
- **IsSupervisor**: للمشرفين فقط
- **IsUniversityAdmin**: لإداريي الجامعات فقط
- **IsTechSupport**: لفريق الدعم التقني فقط

---

## 🌐 APIs والواجهات

### Base URL
```
http://localhost:8000/api/v1/
```

### تنسيق الاستجابة الموحد

جميع APIs ترجع استجابة موحدة:

**نجاح**:
```json
{
  "status": "success",
  "message": "رسالة النجاح",
  "data": { ... }
}
```

**خطأ**:
```json
{
  "status": "error",
  "message": "رسالة الخطأ",
  "errors": { ... }
}
```

### Headers المطلوبة

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

### 1. Accounts APIs - `/api/v1/accounts/`

#### المصادقة (Authentication)

**تسجيل الدخول**
```http
POST /api/v1/accounts/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "status": "success",
  "message": "تم تسجيل الدخول بنجاح.",
  "data": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": { ... }
  }
}
```

**تسجيل الخروج**
```http
POST /api/v1/accounts/logout/
Authorization: Bearer <token>

{
  "refresh": "refresh_token_here"
}
```

#### المرضى (Patients)

- `GET /api/v1/accounts/patients/` - قائمة المرضى
- `POST /api/v1/accounts/patients/create/` - إنشاء مريض
- `GET /api/v1/accounts/patients/<user_id>/` - تفاصيل مريض
- `PATCH /api/v1/accounts/patients/<user_id>/update/` - تحديث مريض
- `DELETE /api/v1/accounts/patients/<user_id>/delete/` - حذف مريض

#### الطلاب (Students)

- `GET /api/v1/accounts/students/` - قائمة الطلاب
- `POST /api/v1/accounts/students/create/` - إنشاء طالب
- `GET /api/v1/accounts/students/<user_id>/` - تفاصيل طالب
- `PATCH /api/v1/accounts/students/<user_id>/update/` - تحديث طالب
- `DELETE /api/v1/accounts/students/<user_id>/delete/` - حذف طالب

#### المشرفين (Supervisors)

- `GET /api/v1/accounts/supervisors/` - قائمة المشرفين
- `POST /api/v1/accounts/supervisors/create/` - إنشاء مشرف
- `GET /api/v1/accounts/supervisors/<user_id>/` - تفاصيل مشرف
- `PATCH /api/v1/accounts/supervisors/<user_id>/update/` - تحديث مشرف
- `DELETE /api/v1/accounts/supervisors/<user_id>/delete/` - حذف مشرف

#### إداريو الجامعات (University Admins)

- `GET /api/v1/accounts/university-admins/` - قائمة الإداريين
- `POST /api/v1/accounts/university-admins/create/` - إنشاء إداري
- `GET /api/v1/accounts/university-admins/<user_id>/` - تفاصيل إداري
- `PATCH /api/v1/accounts/university-admins/<user_id>/update/` - تحديث إداري
- `DELETE /api/v1/accounts/university-admins/<user_id>/delete/` - حذف إداري

#### الدعم التقني (Tech Support)

- `GET /api/v1/accounts/tech-support/` - قائمة فريق الدعم
- `POST /api/v1/accounts/tech-support/create/` - إنشاء عضو دعم
- `GET /api/v1/accounts/tech-support/<user_id>/` - تفاصيل عضو دعم
- `PATCH /api/v1/accounts/tech-support/<user_id>/update/` - تحديث عضو دعم
- `DELETE /api/v1/accounts/tech-support/<user_id>/delete/` - حذف عضو دعم

---

### 2. Cases APIs - `/api/v1/cases/`

**قائمة الحالات**
```http
GET /api/v1/cases/
Query Parameters:
  - patient_id: UUID (فلترة حسب المريض)
  - student_id: UUID (فلترة حسب الطالب)
  - supervisor_id: UUID (فلترة حسب المشرف)
  - status: open|assigned|in_progress|completed|cancelled
  - priority: low|medium|high|urgent
  - is_public: true|false
```

**إنشاء حالة**
```http
POST /api/v1/cases/
{
  "title": "عنوان الحالة",
  "description": "وصف تفصيلي للحالة",
  "priority": "medium",
  "is_public": false
}
```

**تفاصيل حالة**
```http
GET /api/v1/cases/<case_id>/
```

**تحديث حالة**
```http
PATCH /api/v1/cases/<case_id>/
{
  "status": "in_progress",
  "priority": "high"
}
```

**طلب إسناد حالة**
```http
POST /api/v1/cases/<case_id>/request-assign/
{
  "message": "رسالة الطلب"
}
```

**إجراءات المشرف**
```http
POST /api/v1/cases/<case_id>/supervisor-action/
{
  "action": "assign|approve|reject",
  "student_id": "uuid",
  "message": "رسالة"
}
```

---

### 3. Appointments APIs - `/api/v1/appointments/`

**قائمة المواعيد**
```http
GET /api/v1/appointments/
Query Parameters:
  - status: scheduled|confirmed|in_progress|completed|cancelled|no_show
  - patient_id: UUID
  - user_id: UUID (الطبيب/المشرف)
  - case_id: UUID
```

**إنشاء موعد**
```http
POST /api/v1/appointments/
{
  "patient_id": "uuid",
  "user_id": "uuid",
  "appointment_date": "2025-12-20T10:00:00Z",
  "case_id": "uuid"  // اختياري
}
```

**تأكيد موعد**
```http
POST /api/v1/appointments/<appointment_id>/confirm/
```

**بدء موعد**
```http
POST /api/v1/appointments/<appointment_id>/start/
```

**إكمال موعد**
```http
POST /api/v1/appointments/<appointment_id>/complete/
```

**إلغاء موعد**
```http
POST /api/v1/appointments/<appointment_id>/cancel/
{
  "reason": "سبب الإلغاء"
}
```

**تعليم عدم الحضور**
```http
POST /api/v1/appointments/<appointment_id>/no-show/
```

---

### 4. Support APIs - `/api/v1/support/`

**إنشاء طلب دعم**
```http
POST /api/v1/support/tickets/
{
  "category": "technical",
  "subject": "مشكلة في تسجيل الدخول",
  "message": "لا أستطيع تسجيل الدخول إلى حسابي",
  "priority": "urgent"
}
```

**قائمة طلبات الدعم**
```http
GET /api/v1/support/tickets/
Query Parameters:
  - status: open|in_progress|resolved|closed
  - priority: urgent|medium|low
  - category: technical|account|feature|bug|other
```

**تفاصيل طلب**
```http
GET /api/v1/support/tickets/<ticket_id>/
```

**تحديث طلب (للدعم التقني)**
```http
PATCH /api/v1/support/tickets/<ticket_id>/
{
  "status": "in_progress",
  "assigned_to": "uuid",
  "resolution": "تم حل المشكلة"
}
```

**إضافة رد**
```http
POST /api/v1/support/tickets/<ticket_id>/responses/
{
  "message": "ردي على المشكلة",
  "is_internal": false  // للدعم التقني فقط
}
```

**إحصائيات (للدعم التقني فقط)**
```http
GET /api/v1/support/stats/
```

---

### 5. Notifications APIs - `/api/v1/notifications/`

**قائمة الإشعارات**
```http
GET /api/v1/notifications/
Query Parameters:
  - recipient_id: UUID
  - type: appointment_update_request|appointment_cancel_request|...
  - status: pending|accepted|rejected
  - is_read: true|false
```

**تفاصيل إشعار**
```http
GET /api/v1/notifications/<notification_id>/
```

**تحديث حالة الإشعار**
```http
PATCH /api/v1/notifications/<notification_id>/
{
  "is_read": true,
  "status": "accepted"  // للطلبات
}
```

**تحديث FCM Token**
```http
POST /api/v1/notifications/fcm-token/
{
  "fcm_token": "firebase_token_here"
}
```

---

### 6. Evaluations APIs - `/api/v1/evaluations/`

**قائمة التقييمات**
```http
GET /api/v1/evaluations/
Query Parameters:
  - patient_id: UUID
  - student_id: UUID
  - appointment_id: UUID
  - evaluator_type: patient|supervisor|student|university|admin
```

**إنشاء تقييم**
```http
POST /api/v1/evaluations/
{
  "patient_id": "uuid",
  "student_id": "uuid",
  "appointment_id": "uuid",
  "evaluator_type": "patient",
  "rating": 5,
  "comments": "تعليقات التقييم"
}
```

---

### 7. Community APIs - `/api/v1/community/`

**قائمة المحتوى**
```http
GET /api/v1/community/
Query Parameters:
  - content_type: article|video|document|image|link
  - category: medical|educational|research|news|general
  - is_public: true|false
  - is_featured: true|false
  - university_id: UUID
```

**إنشاء محتوى**
```http
POST /api/v1/community/
Content-Type: multipart/form-data

{
  "title": "عنوان المقال",
  "description": "وصف المحتوى",
  "content_type": "article",
  "category": "medical",
  "file": <file>,  // اختياري
  "url": "https://...",  // اختياري
  "tags": "tag1, tag2",
  "is_public": true
}
```

---

### 8. Messaging APIs - `/api/v1/messaging/`

**قائمة الغرف**
```http
GET /api/v1/messaging/rooms/
```

**إنشاء/الحصول على غرفة**
```http
POST /api/v1/messaging/rooms/
{
  "participant_id": "uuid"
}
```

**الرسائل**
```http
GET /api/v1/messaging/rooms/<room_id>/messages/
POST /api/v1/messaging/rooms/<room_id>/messages/
{
  "content": "نص الرسالة"
}
```

---

### 9. AI APIs - `/api/v1/ai/`

**تحليل الأعراض**
```http
POST /api/v1/ai/analyze-symptoms/
{
  "case_id": "uuid",
  "symptoms": "وصف الأعراض"
}
```

**التشخيصات**
```http
GET /api/v1/ai/diagnoses/
GET /api/v1/ai/diagnoses/<diagnosis_id>/
```

---

### 10. Universities APIs - `/api/v1/universities/`

**قائمة الجامعات**
```http
GET /api/v1/universities/
```

**إنشاء جامعة**
```http
POST /api/v1/universities/
{
  "name": "اسم الجامعة",
  "description": "الوصف",
  "address": "العنوان",
  "city": "المدينة",
  "country": "الدولة"
}
```

**الكورسات**
```http
GET /api/v1/universities/<university_id>/courses/
POST /api/v1/universities/<university_id>/courses/
{
  "name": "اسم الكورس",
  "code": "CS101",
  "description": "الوصف",
  "level": "bachelor",
  "duration_years": 4
}
```

---

## 🎬 سيناريو عمل المشروع

### السيناريو الكامل: من تسجيل المريض حتى تقييم الطالب

#### الخطوة 1: إعداد النظام الأساسي

1. **إنشاء جامعة**
   ```http
   POST /api/v1/universities/
   {
     "name": "جامعة الملك سعود",
     "description": "جامعة طبية رائدة",
     "address": "الرياض",
     "city": "الرياض",
     "country": "السعودية"
   }
   ```

2. **إنشاء مشرف**
   ```http
   POST /api/v1/accounts/supervisors/create/
   {
     "username": "dr_ahmed",
     "email": "ahmed@university.edu",
     "password": "SecurePass123!",
     "password_confirm": "SecurePass123!",
     "first_name": "أحمد",
     "last_name": "محمد",
     "university": "university_uuid",
     "department": "الطب النفسي",
     "position": "أستاذ"
   }
   ```

3. **إنشاء طالب**
   ```http
   POST /api/v1/accounts/students/create/
   {
     "username": "student_ali",
     "email": "ali@university.edu",
     "password": "SecurePass123!",
     "password_confirm": "SecurePass123!",
     "first_name": "علي",
     "last_name": "حسن",
     "university_id": "university_uuid",
     "student_id": "123456",
     "year_of_study": 4,
     "specialization": "الطب النفسي"
   }
   ```

#### الخطوة 2: المريض يسجل في النظام

1. **تسجيل مريض جديد**
   ```http
   POST /api/v1/accounts/patients/create/
   {
     "username": "patient_sara",
     "email": "sara@example.com",
     "password": "SecurePass123!",
     "password_confirm": "SecurePass123!",
     "first_name": "سارة",
     "last_name": "أحمد"
   }
   ```

2. **تسجيل الدخول**
   ```http
   POST /api/v1/accounts/login/
   {
     "email": "sara@example.com",
     "password": "SecurePass123!"
   }
   ```
   
   **الاستجابة**:
   ```json
   {
     "status": "success",
     "message": "تم تسجيل الدخول بنجاح.",
     "data": {
       "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
       "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
       "user": {
         "id": "uuid",
         "email": "sara@example.com",
         "role": "patient",
         ...
       }
     }
   }
   ```

#### الخطوة 3: المريض ينشئ حالة طبية

```http
POST /api/v1/cases/
Authorization: Bearer <access_token>

{
  "title": "حالة اكتئاب حاد",
  "description": "المريض يعاني من أعراض اكتئاب حاد مع قلق وتوتر",
  "priority": "high",
  "is_public": false
}
```

**الاستجابة**: يتم إنشاء حالة بحالة `open` (مفتوحة)

#### الخطوة 4: الطالب يطلب إسناد الحالة

1. **الطالب يطلع على الحالات المتاحة**
   ```http
   GET /api/v1/cases/?status=open&is_public=true
   Authorization: Bearer <student_token>
   ```

2. **الطالب يطلب إسناد الحالة**
   ```http
   POST /api/v1/cases/<case_id>/request-assign/
   Authorization: Bearer <student_token>

   {
     "message": "أرغب في العمل على هذه الحالة كجزء من مشروع التخرج"
   }
   ```

#### الخطوة 5: المشرف يراجع الطلب ويوافق

```http
POST /api/v1/cases/<case_id>/supervisor-action/
Authorization: Bearer <supervisor_token>

{
  "action": "assign",
  "student_id": "student_uuid",
  "message": "تمت الموافقة على إسناد الحالة للطالب"
}
```

**النتيجة**: 
- الحالة تُنقل إلى حالة `assigned`
- الطالب يُربط بالحالة
- يتم إرسال إشعار للطالب

#### الخطوة 6: إنشاء موعد للمتابعة

```http
POST /api/v1/appointments/
Authorization: Bearer <supervisor_token>

{
  "patient_id": "patient_uuid",
  "user_id": "supervisor_uuid",
  "appointment_date": "2025-12-25T10:00:00Z",
  "case_id": "case_uuid"
}
```

**النتيجة**: موعد جديد بحالة `scheduled`

#### الخطوة 7: تأكيد الموعد

```http
POST /api/v1/appointments/<appointment_id>/confirm/
Authorization: Bearer <supervisor_token>
```

**النتيجة**: الموعد يُنتقل إلى حالة `confirmed` + إشعار للمريض

#### الخطوة 8: بدء الموعد

```http
POST /api/v1/appointments/<appointment_id>/start/
Authorization: Bearer <supervisor_token>
```

**النتيجة**: الموعد يُنتقل إلى حالة `in_progress`

#### الخطوة 9: إكمال الموعد

```http
POST /api/v1/appointments/<appointment_id>/complete/
Authorization: Bearer <supervisor_token>

{
  "notes": "تمت الجلسة بنجاح، المريض في تحسن"
}
```

**النتيجة**: الموعد يُنتقل إلى حالة `completed` + إشعار للمريض

#### الخطوة 10: المريض يقيم الطالب

```http
POST /api/v1/evaluations/
Authorization: Bearer <patient_token>

{
  "patient_id": "patient_uuid",
  "student_id": "student_uuid",
  "appointment_id": "appointment_uuid",
  "evaluator_type": "patient",
  "rating": 5,
  "comments": "الطالب كان محترفاً ومتعاوناً جداً"
}
```

#### الخطوة 11: الطالب يحدث حالة الحالة

```http
PATCH /api/v1/cases/<case_id>/
Authorization: Bearer <student_token>

{
  "status": "in_progress",
  "description": "تم إجراء جلسة مع المريض، التحسن ملحوظ"
}
```

#### الخطوة 12: إغلاق الحالة

```http
PATCH /api/v1/cases/<case_id>/
Authorization: Bearer <supervisor_token>

{
  "status": "completed",
  "description": "تم إكمال العلاج بنجاح"
}
```

---

### سيناريو إضافي: نظام الدعم التقني

#### المستخدم يواجه مشكلة تقنية

1. **إنشاء طلب دعم**
   ```http
   POST /api/v1/support/tickets/
   Authorization: Bearer <user_token>

   {
     "category": "technical",
     "subject": "لا أستطيع تسجيل الدخول",
     "message": "عند محاولة تسجيل الدخول، أحصل على خطأ 500",
     "priority": "urgent"
   }
   ```

2. **فريق الدعم يطلع على الطلبات**
   ```http
   GET /api/v1/support/tickets/?status=open&priority=urgent
   Authorization: Bearer <tech_support_token>
   ```

3. **فريق الدعم يعين الطلب لنفسه**
   ```http
   PATCH /api/v1/support/tickets/<ticket_id>/
   Authorization: Bearer <tech_support_token>

   {
     "status": "in_progress",
     "assigned_to": "tech_support_uuid"
   }
   ```

4. **فريق الدعم يرد على المستخدم**
   ```http
   POST /api/v1/support/tickets/<ticket_id>/responses/
   Authorization: Bearer <tech_support_token>

   {
     "message": "تم حل المشكلة. الرجاء المحاولة مرة أخرى. إذا استمرت المشكلة، أبلغونا."
   }
   ```

5. **حل الطلب**
   ```http
   PATCH /api/v1/support/tickets/<ticket_id>/
   Authorization: Bearer <tech_support_token>

   {
     "status": "resolved",
     "resolution": "كانت المشكلة في قاعدة البيانات، تم إصلاحها"
   }
   ```

---

## ⚙️ الإعداد والتشغيل

### المتطلبات الأساسية

1. **Python 3.8+**
2. **PostgreSQL 12+**
3. **Redis**
4. **Git**

### خطوات الإعداد

#### 1. استنساخ المشروع

```bash
git clone <repository_url>
cd medismileBackend
```

#### 2. إنشاء بيئة افتراضية

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 3. تثبيت المتطلبات

```bash
pip install -r requirements.txt
```

#### 4. إعداد قاعدة البيانات

```bash
# إنشاء قاعدة البيانات في PostgreSQL
createdb medismile_db

# أو عبر psql
psql -U postgres
CREATE DATABASE medismile_db;
```

#### 5. إعداد متغيرات البيئة

أنشئ ملف `.env` في المجلد الرئيسي:

```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=medismile_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Backup
BACKUP_STORAGE_TYPE=local
BACKUP_RETENTION_DAYS=30
```

#### 6. تطبيق Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 7. إنشاء مستخدم إداري

```bash
python manage.py createsuperuser
```

#### 8. تشغيل الخادم

```bash
# تشغيل Django
python manage.py runserver

# تشغيل Redis (في terminal منفصل)
redis-server

# تشغيل Celery Worker (في terminal منفصل)
celery -A medismile worker -l info

# تشغيل Celery Beat (للمهام المجدولة)
celery -A medismile beat -l info
```

### الوصول إلى النظام

- **API**: http://localhost:8000/api/v1/
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: يمكن إضافة drf-yasg أو drf-spectacular

---

## 💡 أمثلة عملية

### مثال 1: إنشاء مستخدم مريض كامل

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. إنشاء مريض
response = requests.post(
    f"{BASE_URL}/accounts/patients/create/",
    json={
        "username": "patient1",
        "email": "patient1@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "first_name": "محمد",
        "last_name": "أحمد"
    }
)
patient_data = response.json()["data"]

# 2. تسجيل الدخول
login_response = requests.post(
    f"{BASE_URL}/accounts/login/",
    json={
        "email": "patient1@example.com",
        "password": "SecurePass123!"
    }
)
tokens = login_response.json()["data"]
access_token = tokens["access"]

# 3. إنشاء حالة
headers = {"Authorization": f"Bearer {access_token}"}
case_response = requests.post(
    f"{BASE_URL}/cases/",
    headers=headers,
    json={
        "title": "حالة نفسية",
        "description": "وصف الحالة",
        "priority": "medium"
    }
)
case = case_response.json()["data"]
print(f"تم إنشاء الحالة: {case['id']}")
```

### مثال 2: تدفق كامل لموعد

```python
# 1. إنشاء موعد
appointment = requests.post(
    f"{BASE_URL}/appointments/",
    headers=headers,
    json={
        "patient_id": "patient_uuid",
        "user_id": "supervisor_uuid",
        "appointment_date": "2025-12-25T10:00:00Z"
    }
).json()["data"]

appointment_id = appointment["id"]

# 2. تأكيد الموعد
requests.post(
    f"{BASE_URL}/appointments/{appointment_id}/confirm/",
    headers=headers
)

# 3. بدء الموعد
requests.post(
    f"{BASE_URL}/appointments/{appointment_id}/start/",
    headers=headers
)

# 4. إكمال الموعد
requests.post(
    f"{BASE_URL}/appointments/{appointment_id}/complete/",
    headers=headers
)
```

### مثال 3: استخدام WebSocket للرسائل

```javascript
// JavaScript Example
const ws = new WebSocket('ws://localhost:8000/ws/chat/<room_id>/');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('رسالة جديدة:', data);
};

// إرسال رسالة
ws.send(JSON.stringify({
    'message': 'مرحباً، كيف حالك؟'
}));
```

---

## 📝 ملاحظات مهمة

### الأمان

1. **في الإنتاج**: تأكد من تغيير `SECRET_KEY` و `DEBUG=False`
2. **HTTPS**: استخدم HTTPS في الإنتاج دائماً
3. **CORS**: قم بتحديد `ALLOWED_HOSTS` بشكل دقيق
4. **Database**: استخدم كلمات مرور قوية لقاعدة البيانات

### الأداء

1. **Redis**: استخدم Redis للتخزين المؤقت
2. **Celery**: استخدم Celery للمهام الثقيلة
3. **Database Indexing**: تأكد من وجود indexes على الحقول المستخدمة كثيراً
4. **Pagination**: استخدم pagination للقوائم الكبيرة

### الصيانة

1. **Backups**: قم بجدولة نسخ احتياطية منتظمة
2. **Logs**: راقب ملفات السجلات بانتظام
3. **Updates**: قم بتحديث المكتبات بانتظام
4. **Monitoring**: استخدم أدوات مراقبة للأداء

---

## 📞 الدعم والمساعدة

للمساعدة والدعم التقني:
- افتح طلب دعم عبر `/api/v1/support/tickets/`
- راجع ملفات السجلات في `/logs/`
- تحقق من حالة النظام عبر `/api/v1/support/stats/`

---

## 📄 الترخيص

[أضف معلومات الترخيص هنا]

---

**آخر تحديث**: ديسمبر 2025
