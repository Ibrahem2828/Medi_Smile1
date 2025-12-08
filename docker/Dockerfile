# # استخدم Python الرسمي
# FROM python:3.11-slim

# # منع Python من إنشاء ملفات pyc
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # إنشاء مجلد العمل
# WORKDIR /app

# # تثبيت المتطلبات
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # نسخ المشروع بالكامل
# COPY . .

# # Expose port (اختياري — Railway يحدد تلقائيًا)
# EXPOSE 8080

# # تشغيل التطبيق عبر Gunicorn
# CMD ["gunicorn", "medismile.wsgi", "--bind", "0.0.0.0:8000"]
