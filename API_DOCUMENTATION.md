# 📚 توثيق شامل لنظام MediSmile Backend API

## 📋 جدول المحتويات
1. [قسم CASES (الحالات الطبية)](#قسم-cases-الحالات-الطبية)
2. [قسم APPOINTMENTS (المواعيد)](#قسم-appointments-المواعيد)
3. [قسم NOTIFICATIONS (الإشعارات)](#قسم-notifications-الإشعارات)

---

# قسم CASES (الحالات الطبية)

## 📦 محتوى القسم

### النماذج (Models):

#### 1. Case - الحالة الطبية
- **الحقول:**
  - `id` (UUID): معرف فريد للحالة
  - `title` (String): عنوان الحالة
  - `description` (Text): وصف تفصيلي للحالة
  - `patient` (ForeignKey): المريض صاحب الحالة
  - `student` (ForeignKey, nullable): الطالب المسند للحالة
  - `supervisor` (ForeignKey, nullable): المشرف على الحالة
  - `status` (Choice): حالة الحالة
  - `priority` (Choice): أولوية الحالة
  - `is_public` (Boolean): هل الحالة عامة؟
  - `created_at`, `updated_at` (DateTime): تواريخ الإنشاء والتحديث

- **حالات الحالة (Status):**
  - `open`: مفتوحة (قابلة للإسناد)
  - `assigned`: مسندة لطالب
  - `in_progress`: قيد العمل
  - `completed`: مكتملة
  - `cancelled`: ملغاة

- **الأولويات (Priority):**
  - `low`: منخفضة
  - `medium`: متوسطة
  - `high`: عالية
  - `urgent`: عاجلة

#### 2. CaseHistory - سجل تغييرات الحالة
- **الحقول:**
  - `case`: الحالة المرتبطة
  - `action`: نوع الإجراء
  - `description`: وصف الإجراء
  - `performed_by`: من قام بالإجراء
  - `created_at`: تاريخ الإجراء

- **أنواع الإجراءات:**
  - `created`: تم الإنشاء
  - `updated`: تم التحديث
  - `assigned`: تم الإسناد
  - `status_changed`: تغيرت الحالة
  - `completed`: تم الإكمال
  - `cancelled`: تم الإلغاء

#### 3. CaseAssignmentRequest - طلبات إسناد الحالة
- **الحقول:**
  - `case`: الحالة المطلوبة
  - `student`: الطالب طالب الإسناد
  - `message`: رسالة الطلب
  - `status`: حالة الطلب
  - `supervisor_response`: رد المشرف
  - `created_at`, `updated_at`: التواريخ

- **حالات الطلب:**
  - `pending`: قيد الانتظار
  - `accepted`: مقبول
  - `rejected`: مرفوض
  - `cancelled`: ملغي

---

## 🔗 نقاط النهاية (Endpoints)

### 1. **GET/POST** `/api/v1/cases/`

#### GET - جلب قائمة الحالات
**الوصف:** جلب قائمة الحالات حسب دور المستخدم

**الصلاحيات:** 
- المريض: يرى حالاته فقط
- الطالب: يرى حالاته المسندة + الحالات العامة (`is_public=True`)
- المشرف: يرى حالاته المشرف عليها
- الإداري/الدعم: يرى جميع الحالات

**Response Example:**
```json
[
  {
    "id": "uuid",
    "title": "مشكلة في الأسنان",
    "description": "ألم شديد في الضرس",
    "patient": {...},
    "student": {...},
    "supervisor": {...},
    "status": "open",
    "priority": "high",
    "is_public": false,
    "history": [...],
    "assignment_requests": [...],
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
]
```

#### POST - إنشاء حالة جديدة
**الوصف:** إنشاء حالة طبية جديدة

**Request Body:**
```json
{
  "title": "مشكلة في الأسنان",
  "description": "ألم شديد في الضرس",
  "priority": "high",
  "is_public": false
}
```

**الوظيفة:**
- يعيّن المريض تلقائياً من المستخدم الحالي
- ينشئ سجل في `CaseHistory` (action: `created`)

**Response:** حالة جديدة مع جميع التفاصيل

---

### 2. **GET/PUT/PATCH/DELETE** `/api/v1/cases/<uuid:pk>/`

#### GET - جلب تفاصيل حالة
**الوصف:** جلب تفاصيل حالة معينة مع التاريخ وطلبات الإسناد

**Response:** كائن Case كامل مع جميع العلاقات

#### PUT/PATCH - تحديث الحالة
**الوصف:** تحديث بيانات الحالة

**Request Body (PATCH):**
```json
{
  "title": "مشكلة في الأسنان - محدث",
  "status": "in_progress",
  "priority": "urgent"
}
```

**الوظيفة:**
- يتحقق من تغيير الحالة ويضيف سجل في `CaseHistory`
- إذا تغيرت الحالة: `status_changed`
- إذا لم تتغير: `updated`

#### DELETE - حذف الحالة
**الوصف:** حذف الحالة (للمريض فقط)

**Response:** رسالة نجاح

---

### 3. **GET/POST** `/api/v1/cases/<uuid:case_id>/assignment-requests/`

#### GET - جلب طلبات الإسناد
**الوصف:** جلب طلبات الإسناد لحالة معينة

**الصلاحيات:**
- الطالب: طلباته فقط
- المشرف: طلبات الحالات المشرف عليها
- الإداري/الدعم: جميع الطلبات

**Response:** قائمة طلبات الإسناد

#### POST - إنشاء طلب إسناد
**الوصف:** إنشاء طلب إسناد جديد للحالة

**Request Body:**
```json
{
  "message": "أريد العمل على هذه الحالة"
}
```

**الوظيفة:**
- يتحقق أن الحالة `open`
- يعيّن الطالب تلقائياً من المستخدم الحالي
- يمنع إنشاء طلب مكرر (unique_together: case, student)

**Response:** طلب إسناد جديد

---

### 4. **GET/PUT/PATCH** `/api/v1/cases/assignment-requests/<uuid:pk>/`

#### GET - جلب تفاصيل طلب إسناد
**الوصف:** جلب تفاصيل طلب إسناد معين

**Response:** كائن CaseAssignmentRequest كامل

#### PUT/PATCH - تحديث طلب الإسناد
**الوصف:** تحديث طلب الإسناد (للمشرف)

**Request Body:**
```json
{
  "status": "accepted",
  "supervisor_response": "موافق على الإسناد"
}
```

**الوظيفة:**
- إذا تم القبول (`status: 'accepted'`):
  - يعيّن الطالب للحالة
  - يغير حالة الحالة إلى `assigned`
  - يضيف سجل في `CaseHistory` (action: `assigned`)

**Response:** طلب محدث

---

### 5. **POST** `/api/v1/cases/<uuid:case_id>/request-assign/`

**الوصف:** طلب إسناد الحالة للطالب (بديل لـ POST على `/assignment-requests/`)

**Request Body:**
```json
{
  "message": "أريد العمل على هذه الحالة"
}
```

**الوظيفة:**
- يتحقق أن الحالة موجودة و`open`
- يتحقق من عدم وجود طلب سابق
- ينشئ طلب إسناد جديد

**Response:**
```json
{
  "message": "Assignment request created successfully",
  "assignment_request": {
    "id": "uuid",
    "case": "uuid",
    "student": "uuid",
    "status": "pending",
    "message": "أريد العمل على هذه الحالة",
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

---

### 6. **POST** `/api/v1/cases/<uuid:case_id>/supervisor-action/`

**الوصف:** قبول/رفض طلب إسناد (للمشرف)

**Request Body:**
```json
{
  "action": "accept",
  "student_id": "uuid-here",
  "message": "موافق على الإسناد"
}
```

**الوظيفة:**
- يتحقق أن المشرف مسند للحالة
- يأخذ: `action` (`accept` أو `reject`), `student_id`, `message` (اختياري)
- إذا `accept`:
  - يعيّن الطالب للحالة
  - يغير حالة الحالة إلى `assigned`
  - يحدث طلب الإسناد إلى `accepted`
  - يضيف سجل في `CaseHistory`
- إذا `reject`:
  - يحدث طلب الإسناد إلى `rejected`

**Response:**
```json
{
  "message": "Student assigned to case successfully"
}
```

---

# قسم APPOINTMENTS (المواعيد)

## 📦 محتوى القسم

### النموذج (Model):

#### Appointment - الموعد
- **الحقول:**
  - `id` (UUID): معرف فريد للموعد
  - `title` (String): عنوان الموعد
  - `description` (Text): وصف الموعد
  - `case` (ForeignKey): الحالة المرتبطة
  - `patient` (ForeignKey): المريض
  - `student` (ForeignKey): الطالب
  - `appointment_type` (Choice): نوع الموعد
  - `start_datetime` (DateTime): وقت البداية
  - `end_datetime` (DateTime): وقت النهاية
  - `status` (Choice): حالة الموعد
  - `location` (String): الموقع
  - `notes` (Text): ملاحظات
  - `created_at`, `updated_at` (DateTime): التواريخ

- **حالات الموعد (Status):**
  - `scheduled`: مجدول
  - `confirmed`: مؤكد
  - `in_progress`: قيد التنفيذ
  - `completed`: مكتمل
  - `cancelled`: ملغي
  - `no_show`: لم يحضر

- **أنواع الموعد (Type):**
  - `consultation`: استشارة
  - `follow_up`: متابعة
  - `examination`: فحص
  - `treatment`: علاج

**ملاحظة مهمة:** تم إزالة المشرف من المواعيد - المواعيد الآن فقط بين المريض والطالب

---

## 🔗 نقاط النهاية (Endpoints)

### 1. **GET/POST** `/api/v1/appointments/`

#### GET - جلب قائمة المواعيد
**الوصف:** جلب قائمة المواعيد حسب دور المستخدم

**الصلاحيات:**
- المريض: مواعيده فقط
- الطالب: مواعيده فقط
- الإداري/الدعم: جميع المواعيد

**Query Parameters:**
- `status`: فلترة حسب الحالة (مثال: `?status=scheduled`)

**Response:** قائمة المواعيد

#### POST - إنشاء موعد جديد
**الوصف:** إنشاء موعد جديد

**Request Body:**
```json
{
  "title": "فحص دوري",
  "description": "فحص الأسنان",
  "case_id": "uuid-here",
  "student_id": "uuid-here",
  "appointment_type": "examination",
  "start_datetime": "2024-01-15T10:00:00Z",
  "end_datetime": "2024-01-15T11:00:00Z",
  "location": "العيادة 1",
  "notes": "ملاحظات"
}
```

**الوظيفة:**
- يتحقق أن `end_datetime` بعد `start_datetime`
- يعيّن المريض تلقائياً من `case.patient`

**Response:** موعد جديد مع جميع التفاصيل

---

### 2. **GET/PUT/PATCH/DELETE** `/api/v1/appointments/<uuid:pk>/`

#### GET - جلب تفاصيل موعد
**الوصف:** جلب تفاصيل موعد معين

**Response:** كائن Appointment كامل

#### PUT/PATCH - تحديث الموعد
**الوصف:** تحديث بيانات الموعد

**Request Body:**
```json
{
  "title": "فحص دوري - محدث",
  "status": "confirmed",
  "location": "العيادة 2"
}
```

**الحقول القابلة للتحديث:**
- `title`, `description`, `appointment_type`
- `start_datetime`, `end_datetime`
- `status`, `location`, `notes`

**الوظيفة:** يتحقق من صحة التواريخ

#### DELETE - حذف الموعد
**الوصف:** حذف الموعد (للمريض فقط)

**Response:** رسالة نجاح

---

### 3. **POST** `/api/v1/appointments/<uuid:appointment_id>/confirm/`

**الوصف:** تأكيد الموعد

**الوظيفة:**
- يتحقق أن المستخدم طرف في الموعد (مريض أو طالب)
- يتحقق أن الحالة `scheduled`
- يغير الحالة إلى `confirmed`

**Response:**
```json
{
  "message": "Appointment confirmed successfully",
  "appointment": {
    "id": "uuid",
    "status": "confirmed",
    ...
  }
}
```

---

### 4. **POST** `/api/v1/appointments/<uuid:appointment_id>/start/`

**الوصف:** بدء الموعد (تغيير الحالة إلى `in_progress`)

**الوظيفة:**
- للطالب فقط
- يتحقق أن الحالة `confirmed`
- يغير الحالة إلى `in_progress`

**Response:**
```json
{
  "message": "Appointment started successfully",
  "appointment": {
    "id": "uuid",
    "status": "in_progress",
    ...
  }
}
```

---

### 5. **POST** `/api/v1/appointments/<uuid:appointment_id>/complete/`

**الوصف:** إتمام الموعد

**الوظيفة:**
- للطالب فقط
- يتحقق أن الحالة `confirmed` أو `in_progress`
- يغير الحالة إلى `completed`

**Response:**
```json
{
  "message": "Appointment completed successfully",
  "appointment": {
    "id": "uuid",
    "status": "completed",
    ...
  }
}
```

---

### 6. **POST** `/api/v1/appointments/<uuid:appointment_id>/cancel/`

**الوصف:** إلغاء الموعد

**الوظيفة:**
- يتحقق أن المستخدم طرف في الموعد (مريض أو طالب)
- يتحقق أن الحالة `scheduled` أو `confirmed`
- يغير الحالة إلى `cancelled`

**Response:**
```json
{
  "message": "Appointment cancelled successfully",
  "appointment": {
    "id": "uuid",
    "status": "cancelled",
    ...
  }
}
```

---

### 7. **POST** `/api/v1/appointments/<uuid:appointment_id>/no-show/`

**الوصف:** تعيين الموعد كـ "لم يحضر"

**الوظيفة:**
- للطالب فقط
- يتحقق أن الحالة `confirmed` أو `in_progress`
- يغير الحالة إلى `no_show`

**Response:**
```json
{
  "message": "Appointment marked as no show successfully",
  "appointment": {
    "id": "uuid",
    "status": "no_show",
    ...
  }
}
```

---

## 🔄 تدفق حالات الموعد (Status Flow)

```
scheduled → confirmed → in_progress → completed
    ↓                        ↓
cancelled                 no_show
```

---

# قسم NOTIFICATIONS (الإشعارات)

## 📦 محتوى القسم

### النموذج (Model):

#### Notification - الإشعار
- **الحقول:**
  - `id` (UUID): معرف فريد للإشعار
  - `sender` (ForeignKey): المرسل
  - `recipient` (ForeignKey): المستقبل
  - `notification_type` (Choice): نوع الإشعار
  - `appointment` (ForeignKey): الموعد المرتبط
  - `title` (String): عنوان الإشعار
  - `message` (Text): رسالة الإشعار
  - `status` (Choice): حالة الإشعار
  - `response_message` (Text): رسالة الرد
  - `proposed_changes` (JSON): التغييرات المقترحة (لطلبات التعديل)
  - `is_read` (Boolean): هل تم القراءة؟
  - `created_at`, `updated_at` (DateTime): التواريخ

- **أنواع الإشعارات:**
  - `appointment_update_request`: طلب تعديل موعد
  - `appointment_cancel_request`: طلب إلغاء موعد
  - `appointment_confirmed`: تأكيد الموعد
  - `appointment_cancelled`: إلغاء الموعد
  - `appointment_completed`: إتمام الموعد

- **حالات الإشعار:**
  - `pending`: قيد الانتظار
  - `accepted`: مقبول
  - `rejected`: مرفوض

---

## 🔗 نقاط النهاية (Endpoints)

### 1. **GET/POST** `/api/v1/notifications/`

#### GET - جلب قائمة الإشعارات
**الوصف:** جلب إشعارات المستخدم الحالي

**Query Parameters:**
- `type`: فلترة حسب النوع (مثال: `?type=appointment_update_request`)
- `status`: فلترة حسب الحالة (مثال: `?status=pending`)
- `is_read`: فلترة حسب القراءة (مثال: `?is_read=false`)

**Response:** قائمة الإشعارات

#### POST - إنشاء إشعار جديد
**الوصف:** إنشاء إشعار جديد

**Request Body:**
```json
{
  "notification_type": "appointment_update_request",
  "appointment_id": "uuid-here",
  "recipient_id": "uuid-here",
  "title": "طلب تعديل موعد",
  "message": "أريد تعديل وقت الموعد",
  "proposed_changes": {
    "start_datetime": "2024-01-16T10:00:00Z",
    "end_datetime": "2024-01-16T11:00:00Z"
  }
}
```

**الوظيفة:**
- يعيّن المرسل تلقائياً من المستخدم الحالي

**Response:** إشعار جديد

---

### 2. **GET/PUT/PATCH** `/api/v1/notifications/<uuid:pk>/`

#### GET - جلب تفاصيل إشعار
**الوصف:** جلب تفاصيل إشعار معين

**الوظيفة:**
- يتحقق أن المستخدم هو المستقبل
- يضع علامة `is_read = True` تلقائياً

**Response:** كائن Notification كامل

#### PUT/PATCH - الرد على الإشعار
**الوصف:** قبول أو رفض الإشعار

**Request Body:**
```json
{
  "status": "accepted",
  "response_message": "موافق على التعديل"
}
```

**الوظيفة:**
- إذا كان `status: 'accepted'` ونوع الإشعار `appointment_update_request`:
  - يطبق التغييرات المقترحة على الموعد
  - ينشئ إشعار تأكيد للمرسل
- إذا كان `status: 'accepted'` ونوع الإشعار `appointment_cancel_request`:
  - يغير حالة الموعد إلى `cancelled`
  - ينشئ إشعار تأكيد للمرسل

**Response:** إشعار محدث

---

### 3. **POST** `/api/v1/notifications/appointments/<uuid:appointment_id>/request-update/`

**الوصف:** طلب تعديل موعد من المريض أو الطالب

**Request Body:**
```json
{
  "title": "طلب تعديل موعد",
  "message": "أريد تغيير وقت الموعد",
  "proposed_changes": {
    "start_datetime": "2024-01-16T10:00:00Z",
    "end_datetime": "2024-01-16T11:00:00Z",
    "location": "العيادة 2"
  }
}
```

**الوظيفة:**
- يتحقق أن المستخدم مريض أو طالب
- يتحقق أن المستخدم طرف في الموعد
- يحدد المستقبل تلقائياً (الطرف الآخر)
- ينشئ إشعار `appointment_update_request`

**Response:**
```json
{
  "message": "Appointment update request sent successfully",
  "notification": {
    "id": "uuid",
    "notification_type": "appointment_update_request",
    "status": "pending",
    ...
  }
}
```

---

### 4. **GET** `/api/v1/notifications/unread-count/`

**الوصف:** جلب عدد الإشعارات غير المقروءة

**Response:**
```json
{
  "unread_count": 5
}
```

---

### 5. **POST** `/api/v1/notifications/mark-all-read/`

**الوصف:** وضع علامة مقروء على جميع الإشعارات

**Response:**
```json
{
  "message": "All notifications marked as read"
}
```

---

## 🔄 تدفق الإشعارات

### سيناريو: طلب تعديل موعد

1. **الطالب يطلب تعديل:**
   - POST `/api/v1/notifications/appointments/<id>/request-update/`
   - ينشئ إشعار `appointment_update_request` للمريض

2. **المريض يرى الإشعار:**
   - GET `/api/v1/notifications/`
   - يرى الإشعار مع التغييرات المقترحة

3. **المريض يرد:**
   - PATCH `/api/v1/notifications/<id>/`
   - `status: "accepted"` أو `"rejected"`

4. **إذا قبل:**
   - يتم تطبيق التغييرات على الموعد تلقائياً
   - ينشئ إشعار تأكيد للطالب

---

## 📝 ملاحظات مهمة

### العلاقة بين الأقسام:
- كل موعد مرتبط بحالة (`case`)
- عند إنشاء موعد، يُؤخذ المريض تلقائياً من الحالة المرتبطة
- الإشعارات تربط بين المريض والطالب فقط (لا مشرف)

### حالات الحالة (Case Status Flow):
```
open → assigned → in_progress → completed
  ↓
cancelled
```

### حالات الموعد (Appointment Status Flow):
```
scheduled → confirmed → in_progress → completed
    ↓                        ↓
cancelled                 no_show
```

### حالات الإشعار (Notification Status Flow):
```
pending → accepted/rejected
```

---

## 🔐 الصلاحيات الحالية

**ملاحظة:** جميع الصلاحيات معلقة مؤقتاً (`AllowAny`) - يمكن الوصول لجميع الـ APIs بدون مصادقة.

عند إعادة تفعيل المصادقة:
- **Cases:** المريض ينشئ/يعدل/يحذف، الطالب يطلب إسناد، المشرف يقبل/يرفض
- **Appointments:** المريض والطالب فقط (لا مشرف)
- **Notifications:** المريض والطالب فقط

---

## 📞 أمثلة على الاستخدام

### مثال 1: إنشاء حالة وموعد
```bash
# 1. إنشاء حالة
POST /api/v1/cases/
{
  "title": "مشكلة في الأسنان",
  "description": "ألم شديد",
  "priority": "high"
}

# 2. إنشاء موعد
POST /api/v1/appointments/
{
  "title": "فحص",
  "case_id": "case-uuid",
  "student_id": "student-uuid",
  "start_datetime": "2024-01-15T10:00:00Z",
  "end_datetime": "2024-01-15T11:00:00Z"
}
```

### مثال 2: طلب تعديل موعد
```bash
# الطالب يطلب تعديل
POST /api/v1/notifications/appointments/appointment-uuid/request-update/
{
  "title": "طلب تعديل",
  "message": "أريد تغيير الوقت",
  "proposed_changes": {
    "start_datetime": "2024-01-16T10:00:00Z",
    "end_datetime": "2024-01-16T11:00:00Z"
  }
}

# المريض يرد
PATCH /api/v1/notifications/notification-uuid/
{
  "status": "accepted",
  "response_message": "موافق"
}
```

---

**تم إنشاء هذا التوثيق بتاريخ:** 2024-01-15  
**آخر تحديث:** بعد إزالة المشرف من المواعيد وإضافة نظام الإشعارات






