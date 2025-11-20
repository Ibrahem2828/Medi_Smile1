# دليل ربط Dashboard مع Backend - CRUD Operations

## 📋 نظرة عامة

هذا الدليل يوضح كيفية ربط Dashboard مع Backend للعمليات التالية:
- ✅ **Supervisors (المشرفين)**: إضافة، حذف، تعديل
- ✅ **Patients (المرضى)**: إضافة، حذف، تعديل
- ✅ **Students (الطلاب)**: إضافة، حذف، تعديل
- ✅ **Tech Support (الدعم التقني)**: إضافة، حذف، تعديل

---

## 🔗 Base URL

```
http://localhost:8000/api/v1/accounts/
```

---

## 📝 1. Supervisors (المشرفين)

### 1.1 جلب قائمة المشرفين
```javascript
GET /api/v1/accounts/supervisors/

// Response
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

### 1.2 إضافة مشرف جديد
```javascript
POST /api/v1/accounts/supervisors/create/

// Request Body
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

// Response
{
  "status": "success",
  "message": "تم إنشاء المشرف بنجاح.",
  "data": { /* تفاصيل المشرف الكاملة */ }
}
```

### 1.3 جلب تفاصيل مشرف
```javascript
GET /api/v1/accounts/supervisors/{user_id}/

// Response
{
  "status": "success",
  "message": "تم جلب بيانات المشرف بنجاح.",
  "data": { /* تفاصيل المشرف الكاملة */ }
}
```

### 1.4 تعديل مشرف
```javascript
PATCH /api/v1/accounts/supervisors/{user_id}/update/

// Request Body (يمكن إرسال الحقول التي تريد تحديثها فقط)
{
  "department": "الطب النفسي للأطفال",
  "position": "مشرف أول",
  "phone_number": "+966501234567",
  "address": "الرياض، حي النرجس"
}

// Response
{
  "status": "success",
  "message": "تم تحديث بيانات المشرف بنجاح.",
  "data": { /* بيانات المشرف المحدثة */ }
}
```

### 1.5 حذف مشرف
```javascript
DELETE /api/v1/accounts/supervisors/{user_id}/delete/

// Response
{
  "status": "success",
  "message": "تم حذف المشرف بنجاح.",
  "data": null
}
```

---

## 📝 2. Patients (المرضى)

### 2.1 جلب قائمة المرضى
```javascript
GET /api/v1/accounts/patients/
```

### 2.2 إضافة مريض جديد
```javascript
POST /api/v1/accounts/patients/create/

// Request Body
{
  "username": "patient1",
  "email": "patient@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "محمد",
  "last_name": "أحمد"
}

// Response
{
  "status": "success",
  "message": "تم إنشاء المريض بنجاح.",
  "data": { /* تفاصيل المريض الكاملة */ }
}
```

### 2.3 جلب تفاصيل مريض
```javascript
GET /api/v1/accounts/patients/{user_id}/
```

### 2.4 تعديل مريض
```javascript
PATCH /api/v1/accounts/patients/{user_id}/update/

// Request Body
{
  "phone_number": "+966501234567",
  "address": "الرياض",
  "date_of_birth": "1990-01-01",
  "gender": "male",
  "medical_history": "تاريخ طبي...",
  "allergies": "حساسية...",
  "medications": "أدوية...",
  "emergency_contact_name": "أحمد محمد",
  "emergency_contact_phone": "+966501234567"
}
```

### 2.5 حذف مريض
```javascript
DELETE /api/v1/accounts/patients/{user_id}/delete/
```

---

## 📝 3. Students (الطلاب)

### 3.1 جلب قائمة الطلاب
```javascript
GET /api/v1/accounts/students/
```

### 3.2 إضافة طالب جديد
```javascript
POST /api/v1/accounts/students/create/

// Request Body
{
  "username": "student1",
  "email": "student@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "علي",
  "last_name": "حسن",
  "university_id": "uuid-of-university",  // اختياري
  "student_id": "123456",  // اختياري
  "year_of_study": 3,  // اختياري
  "specialization": "الطب النفسي"  // اختياري
}
```

### 3.3 جلب تفاصيل طالب
```javascript
GET /api/v1/accounts/students/{user_id}/
```

### 3.4 تعديل طالب
```javascript
PATCH /api/v1/accounts/students/{user_id}/update/

// Request Body
{
  "phone_number": "+966501234567",
  "address": "الرياض",
  "university": "uuid-of-university",
  "student_id": "123456",
  "year_of_study": 4,
  "specialization": "الطب النفسي"
}
```

### 3.5 حذف طالب
```javascript
DELETE /api/v1/accounts/students/{user_id}/delete/
```

---

## 📝 4. Tech Support (الدعم التقني)

### 4.1 جلب قائمة الدعم التقني
```javascript
GET /api/v1/accounts/tech-support/
```

### 4.2 إضافة دعم تقني جديد
```javascript
POST /api/v1/accounts/tech-support/create/

// Request Body
{
  "username": "tech1",
  "email": "tech@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "خالد",
  "last_name": "سعيد",
  "department": "الدعم الفني",  // اختياري
  "position": "فني دعم"  // اختياري
}
```

### 4.3 جلب تفاصيل دعم تقني
```javascript
GET /api/v1/accounts/tech-support/{user_id}/
```

### 4.4 تعديل دعم تقني
```javascript
PATCH /api/v1/accounts/tech-support/{user_id}/update/

// Request Body
{
  "phone_number": "+966501234567",
  "address": "الرياض",
  "department": "الدعم الفني",
  "position": "فني دعم أول"
}
```

### 4.5 حذف دعم تقني
```javascript
DELETE /api/v1/accounts/tech-support/{user_id}/delete/
```

---

## 💻 كود JavaScript/React جاهز للاستخدام

### Service File
```javascript
// src/services/dashboardService.js

const API_BASE_URL = 'http://localhost:8000/api/v1/accounts';

// Helper function
const apiCall = async (endpoint, method = 'GET', body = null) => {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
  const data = await response.json();
  
  if (data.status === 'success') {
    return { success: true, data: data.data, message: data.message };
  } else {
    return { success: false, error: data.message || data.errors };
  }
};

// ==================== SUPERVISORS ==================== //
export const supervisorsService = {
  // جلب القائمة
  async getAll() {
    return apiCall('/supervisors/');
  },

  // جلب واحد
  async getById(userId) {
    return apiCall(`/supervisors/${userId}/`);
  },

  // إضافة
  async create(data) {
    return apiCall('/supervisors/create/', 'POST', data);
  },

  // تعديل
  async update(userId, data) {
    return apiCall(`/supervisors/${userId}/update/`, 'PATCH', data);
  },

  // حذف
  async delete(userId) {
    return apiCall(`/supervisors/${userId}/delete/`, 'DELETE');
  },
};

// ==================== PATIENTS ==================== //
export const patientsService = {
  async getAll() {
    return apiCall('/patients/');
  },

  async getById(userId) {
    return apiCall(`/patients/${userId}/`);
  },

  async create(data) {
    return apiCall('/patients/create/', 'POST', data);
  },

  async update(userId, data) {
    return apiCall(`/patients/${userId}/update/`, 'PATCH', data);
  },

  async delete(userId) {
    return apiCall(`/patients/${userId}/delete/`, 'DELETE');
  },
};

// ==================== STUDENTS ==================== //
export const studentsService = {
  async getAll() {
    return apiCall('/students/');
  },

  async getById(userId) {
    return apiCall(`/students/${userId}/`);
  },

  async create(data) {
    return apiCall('/students/create/', 'POST', data);
  },

  async update(userId, data) {
    return apiCall(`/students/${userId}/update/`, 'PATCH', data);
  },

  async delete(userId) {
    return apiCall(`/students/${userId}/delete/`, 'DELETE');
  },
};

// ==================== TECH SUPPORT ==================== //
export const techSupportService = {
  async getAll() {
    return apiCall('/tech-support/');
  },

  async getById(userId) {
    return apiCall(`/tech-support/${userId}/`);
  },

  async create(data) {
    return apiCall('/tech-support/create/', 'POST', data);
  },

  async update(userId, data) {
    return apiCall(`/tech-support/${userId}/update/`, 'PATCH', data);
  },

  async delete(userId) {
    return apiCall(`/tech-support/${userId}/delete/`, 'DELETE');
  },
};
```

---

## 🎨 مثال على استخدام في React Component

### Supervisors Component
```javascript
// src/components/SupervisorsManagement.js
import { useState, useEffect } from 'react';
import { supervisorsService } from '../services/dashboardService';

const SupervisorsManagement = () => {
  const [supervisors, setSupervisors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    department: '',
    position: '',
    license_number: '',
  });

  // جلب القائمة
  useEffect(() => {
    loadSupervisors();
  }, []);

  const loadSupervisors = async () => {
    setLoading(true);
    const result = await supervisorsService.getAll();
    if (result.success) {
      setSupervisors(result.data);
    }
    setLoading(false);
  };

  // إضافة مشرف
  const handleCreate = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const result = await supervisorsService.create(formData);
    
    if (result.success) {
      alert('تم إضافة المشرف بنجاح!');
      setFormData({
        username: '',
        email: '',
        password: '',
        password_confirm: '',
        first_name: '',
        last_name: '',
        department: '',
        position: '',
        license_number: '',
      });
      loadSupervisors(); // إعادة تحميل القائمة
    } else {
      alert(`خطأ: ${result.error}`);
    }
    
    setLoading(false);
  };

  // حذف مشرف
  const handleDelete = async (userId) => {
    if (!window.confirm('هل أنت متأكد من حذف هذا المشرف؟')) {
      return;
    }

    const result = await supervisorsService.delete(userId);
    
    if (result.success) {
      alert('تم حذف المشرف بنجاح!');
      loadSupervisors();
    } else {
      alert(`خطأ: ${result.error}`);
    }
  };

  // تعديل مشرف
  const handleUpdate = async (userId, updateData) => {
    const result = await supervisorsService.update(userId, updateData);
    
    if (result.success) {
      alert('تم تحديث المشرف بنجاح!');
      loadSupervisors();
    } else {
      alert(`خطأ: ${result.error}`);
    }
  };

  return (
    <div>
      <h2>إدارة المشرفين</h2>

      {/* نموذج الإضافة */}
      <form onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="اسم المستخدم"
          value={formData.username}
          onChange={(e) => setFormData({ ...formData, username: e.target.value })}
          required
        />
        <input
          type="email"
          placeholder="البريد الإلكتروني"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          required
        />
        <input
          type="password"
          placeholder="كلمة المرور"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          required
        />
        <input
          type="password"
          placeholder="تأكيد كلمة المرور"
          value={formData.password_confirm}
          onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="الاسم الأول"
          value={formData.first_name}
          onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="اسم العائلة"
          value={formData.last_name}
          onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="القسم"
          value={formData.department}
          onChange={(e) => setFormData({ ...formData, department: e.target.value })}
        />
        <input
          type="text"
          placeholder="المنصب"
          value={formData.position}
          onChange={(e) => setFormData({ ...formData, position: e.target.value })}
        />
        <input
          type="text"
          placeholder="رقم الرخصة"
          value={formData.license_number}
          onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'جاري الإضافة...' : 'إضافة مشرف'}
        </button>
      </form>

      {/* قائمة المشرفين */}
      <div>
        <h3>قائمة المشرفين</h3>
        {loading ? (
          <p>جاري التحميل...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>الاسم</th>
                <th>البريد الإلكتروني</th>
                <th>القسم</th>
                <th>المنصب</th>
                <th>الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {supervisors.map((supervisor) => (
                <tr key={supervisor.user_id}>
                  <td>{supervisor.first_name} {supervisor.last_name}</td>
                  <td>{supervisor.email}</td>
                  <td>{supervisor.department}</td>
                  <td>{supervisor.position}</td>
                  <td>
                    <button onClick={() => handleDelete(supervisor.user_id)}>
                      حذف
                    </button>
                    <button onClick={() => {/* فتح نموذج التعديل */}}>
                      تعديل
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default SupervisorsManagement;
```

---

## ✅ Checklist للربط

- [ ] إنشاء `dashboardService.js` مع جميع الـ Services
- [ ] إنشاء Component للمشرفين (Supervisors)
- [ ] إنشاء Component للمرضى (Patients)
- [ ] إنشاء Component للطلاب (Students)
- [ ] إنشاء Component للدعم التقني (Tech Support)
- [ ] اختبار جميع العمليات (Create, Read, Update, Delete)
- [ ] إضافة معالجة الأخطاء
- [ ] إضافة Loading States
- [ ] إضافة Confirmations للحذف

---

## 🎯 ملخص الـ APIs

| العملية | Supervisors | Patients | Students | Tech Support |
|---------|-------------|----------|----------|--------------|
| **القائمة** | `GET /supervisors/` | `GET /patients/` | `GET /students/` | `GET /tech-support/` |
| **إضافة** | `POST /supervisors/create/` | `POST /patients/create/` | `POST /students/create/` | `POST /tech-support/create/` |
| **تفاصيل** | `GET /supervisors/{id}/` | `GET /patients/{id}/` | `GET /students/{id}/` | `GET /tech-support/{id}/` |
| **تعديل** | `PATCH /supervisors/{id}/update/` | `PATCH /patients/{id}/update/` | `PATCH /students/{id}/update/` | `PATCH /tech-support/{id}/update/` |
| **حذف** | `DELETE /supervisors/{id}/delete/` | `DELETE /patients/{id}/delete/` | `DELETE /students/{id}/delete/` | `DELETE /tech-support/{id}/delete/` |

---

## 🚀 جاهز للاستخدام!

جميع الـ APIs جاهزة وموثقة. يمكنك البدء بالربط مباشرة! 🎉


