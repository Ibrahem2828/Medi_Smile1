# توثيق APIs الخاصة بـ Supervisors (المشرفين)

## 📋 نظرة عامة

قسم **Supervisors** في تطبيق **accounts** جاهز تماماً ومربوط بالباك إند. يحتوي على جميع العمليات الأساسية (CRUD) لإدارة المشرفين.

---

## 🗄️ بنية البيانات (Model Structure)

### SupervisorProfile Model
```python
- user (OneToOneField) - ربط مع جدول Users
- university (ForeignKey) - الجامعة المرتبطة
- department (CharField) - القسم
- position (CharField) - المنصب
- license_number (CharField) - رقم الرخصة
- phone_number (CharField) - رقم الهاتف
- address (TextField) - العنوان
- date_of_birth (DateField) - تاريخ الميلاد
- gender (CharField) - الجنس (male/female)
- profile_picture (ImageField) - صورة الملف الشخصي
- created_at (DateTimeField) - تاريخ الإنشاء
- updated_at (DateTimeField) - تاريخ التحديث
```

---

## 🔗 API Endpoints

**Base URL:** `/api/v1/accounts/`

---

### 1️⃣ جلب قائمة المشرفين (List Supervisors)

**Endpoint:** `GET /api/v1/accounts/supervisors/`

**Method:** `GET`

**Headers:**
```
Content-Type: application/json
```

**Query Parameters:** لا يوجد

**Response (Success - 200):**
```json
{
  "status": "success",
  "message": "تم جلب قائمة المشرفين بنجاح.",
  "data": [
    {
      "user_id": "uuid",
      "username": "supervisor1",
      "email": "supervisor@example.com",
      "first_name": "أحمد",
      "last_name": "محمد",
      "university_name": "جامعة الملك سعود",
      "department": "الطب النفسي",
      "position": "مشرف سريري",
      "license_number": "LIC123456"
    }
  ]
}
```

**Response (Error - 500):**
```json
{
  "status": "error",
  "message": "فشل جلب قائمة المشرفين.",
  "errors": "error details"
}
```

---

### 2️⃣ إنشاء مشرف جديد (Create Supervisor)

**Endpoint:** `POST /api/v1/accounts/supervisors/create/`

**Method:** `POST`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "supervisor1",
  "email": "supervisor@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "أحمد",
  "last_name": "محمد",
  "university_id": "uuid-of-university",  // اختياري
  "department": "الطب النفسي",  // اختياري
  "position": "مشرف سريري",  // اختياري
  "license_number": "LIC123456"  // اختياري
}
```

**الحقول المطلوبة:**
- `username` (string) - اسم المستخدم
- `email` (string) - البريد الإلكتروني (يجب أن يكون فريد)
- `password` (string) - كلمة المرور
- `password_confirm` (string) - تأكيد كلمة المرور
- `first_name` (string) - الاسم الأول
- `last_name` (string) - اسم العائلة

**الحقول الاختيارية:**
- `university_id` (UUID) - معرف الجامعة
- `department` (string) - القسم
- `position` (string) - المنصب
- `license_number` (string) - رقم الرخصة

**Response (Success - 201):**
```json
{
  "status": "success",
  "message": "تم إنشاء المشرف بنجاح.",
  "data": {
    "user_id": "uuid",
    "username": "supervisor1",
    "email": "supervisor@example.com",
    "first_name": "أحمد",
    "last_name": "محمد",
    "role": "supervisor",
    "is_active": true,
    "date_joined": "2024-01-01T00:00:00Z",
    "last_login": null,
    "university_name": "جامعة الملك سعود",
    "university": "uuid",
    "department": "الطب النفسي",
    "position": "مشرف سريري",
    "license_number": "LIC123456",
    "phone_number": null,
    "address": null,
    "date_of_birth": null,
    "gender": null,
    "profile_picture": null,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

**Response (Error - 400):**
```json
{
  "status": "error",
  "message": "بيانات المشرف غير صالحة.",
  "errors": {
    "email": ["user with this email already exists."],
    "password": ["Passwords don't match."]
  }
}
```

---

### 3️⃣ جلب تفاصيل مشرف (Get Supervisor Details)

**Endpoint:** `GET /api/v1/accounts/supervisors/<user_id>/`

**Method:** `GET`

**URL Parameters:**
- `user_id` (UUID) - معرف المستخدم (المشرف)

**Headers:**
```
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
  "status": "success",
  "message": "تم جلب بيانات المشرف بنجاح.",
  "data": {
    "user_id": "uuid",
    "username": "supervisor1",
    "email": "supervisor@example.com",
    "first_name": "أحمد",
    "last_name": "محمد",
    "role": "supervisor",
    "is_active": true,
    "date_joined": "2024-01-01T00:00:00Z",
    "last_login": "2024-01-15T10:30:00Z",
    "university_name": "جامعة الملك سعود",
    "university": "uuid",
    "department": "الطب النفسي",
    "position": "مشرف سريري",
    "license_number": "LIC123456",
    "phone_number": "+966501234567",
    "address": "الرياض، المملكة العربية السعودية",
    "date_of_birth": "1980-05-15",
    "gender": "male",
    "profile_picture": "/media/profile_pictures/supervisor.jpg",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Response (Error - 404):**
```json
{
  "status": "error",
  "message": "المشرف غير موجود.",
  "errors": "error details"
}
```

---

### 4️⃣ تحديث بيانات مشرف (Update Supervisor)

**Endpoint:** `PATCH /api/v1/accounts/supervisors/<user_id>/update/`

**Method:** `PATCH` (للتحديث الجزئي) أو `PUT` (للتحديث الكامل)

**URL Parameters:**
- `user_id` (UUID) - معرف المستخدم (المشرف)

**Headers:**
```
Content-Type: application/json
```

**Request Body (PATCH - تحديث جزئي):**
```json
{
  "department": "الطب النفسي للأطفال",
  "position": "مشرف أول",
  "phone_number": "+966501234567",
  "address": "الرياض، حي النرجس"
}
```

**الحقول القابلة للتحديث:**
- `phone_number` (string) - رقم الهاتف
- `address` (string) - العنوان
- `date_of_birth` (date) - تاريخ الميلاد (YYYY-MM-DD)
- `gender` (string) - الجنس (male/female)
- `profile_picture` (file) - صورة الملف الشخصي
- `university` (UUID) - الجامعة
- `department` (string) - القسم
- `position` (string) - المنصب
- `license_number` (string) - رقم الرخصة

**ملاحظة:** لا يمكن تحديث بيانات المستخدم الأساسية (username, email, first_name, last_name) من هذا الـ endpoint.

**Response (Success - 200):**
```json
{
  "status": "success",
  "message": "تم تحديث بيانات المشرف بنجاح.",
  "data": {
    "user_id": "uuid",
    "username": "supervisor1",
    "email": "supervisor@example.com",
    "first_name": "أحمد",
    "last_name": "محمد",
    "role": "supervisor",
    "is_active": true,
    "date_joined": "2024-01-01T00:00:00Z",
    "last_login": "2024-01-15T10:30:00Z",
    "university_name": "جامعة الملك سعود",
    "university": "uuid",
    "department": "الطب النفسي للأطفال",
    "position": "مشرف أول",
    "license_number": "LIC123456",
    "phone_number": "+966501234567",
    "address": "الرياض، حي النرجس",
    "date_of_birth": "1980-05-15",
    "gender": "male",
    "profile_picture": "/media/profile_pictures/supervisor.jpg",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

**Response (Error - 400):**
```json
{
  "status": "error",
  "message": "بيانات التحديث غير صالحة.",
  "errors": {
    "gender": ["Invalid choice"]
  }
}
```

---

### 5️⃣ حذف مشرف (Delete Supervisor)

**Endpoint:** `DELETE /api/v1/accounts/supervisors/<user_id>/delete/`

**Method:** `DELETE`

**URL Parameters:**
- `user_id` (UUID) - معرف المستخدم (المشرف)

**Headers:**
```
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
  "status": "success",
  "message": "تم حذف المشرف بنجاح.",
  "data": null
}
```

**Response (Error - 500):**
```json
{
  "status": "error",
  "message": "فشل حذف المشرف.",
  "errors": "error details"
}
```

**⚠️ تحذير:** هذه العملية تحذف المشرف والملف الشخصي بشكل دائم!

---

## 🔗 العلاقات (Relationships)

### العلاقة مع Universities
- كل مشرف يمكن أن يكون مرتبط بجامعة واحدة (اختياري)
- الحقل: `university` (ForeignKey)
- يمكن جلب اسم الجامعة من خلال `university_name` في الـ response

---

## 📝 ملاحظات مهمة

1. **المصادقة (Authentication):**
   - حالياً جميع الـ endpoints تستخدم `AllowAny` permission
   - يُنصح بإضافة نظام مصادقة في الإنتاج

2. **التحقق من البيانات (Validation):**
   - كلمة المرور يجب أن تطابق `password_confirm`
   - البريد الإلكتروني يجب أن يكون فريد
   - كلمة المرور يجب أن تتبع قواعد Django password validation

3. **الصور (Images):**
   - عند رفع صورة الملف الشخصي، استخدم `multipart/form-data` بدلاً من `application/json`

4. **UUID Format:**
   - جميع معرفات المستخدمين (user_id) هي UUIDs
   - مثال: `550e8400-e29b-41d4-a716-446655440000`

---

## ✅ الحالة الحالية

✅ **جاهز للاستخدام:**
- جميع الـ CRUD operations جاهزة
- الربط مع جدول Universities موجود
- Serializers جاهزة
- Views جاهزة
- URLs مُعرّفة
- Error handling موجود

---

## 🧪 أمثلة على الاستخدام

### مثال 1: إنشاء مشرف جديد
```bash
curl -X POST http://localhost:8000/api/v1/accounts/supervisors/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "dr_ahmed",
    "email": "ahmed@university.edu.sa",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "أحمد",
    "last_name": "محمد",
    "university_id": "550e8400-e29b-41d4-a716-446655440000",
    "department": "الطب النفسي",
    "position": "مشرف سريري",
    "license_number": "PSY-2024-001"
  }'
```

### مثال 2: جلب قائمة المشرفين
```bash
curl -X GET http://localhost:8000/api/v1/accounts/supervisors/ \
  -H "Content-Type: application/json"
```

### مثال 3: تحديث بيانات مشرف
```bash
curl -X PATCH http://localhost:8000/api/v1/accounts/supervisors/550e8400-e29b-41d4-a716-446655440000/update/ \
  -H "Content-Type: application/json" \
  -d '{
    "department": "الطب النفسي للأطفال",
    "phone_number": "+966501234567"
  }'
```

---

## 📞 الدعم

إذا واجهت أي مشاكل أو تحتاج إلى إضافة ميزات جديدة، يمكنك التواصل مع فريق التطوير.



