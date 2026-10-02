# نشر MediSmile Backend على Coolify

هذا المستودع جاهز للنشر كـ Docker Compose Application في Coolify عبر الملف
`docker-compose.coolify.yml`. التصميم المقصود للإنتاج هو:

```text
Internet -> Coolify proxy -> web (Daphne/ASGI)
                              |-> PostgreSQL resource
                              |-> Redis resource
                              `-> worker (Celery)
```

لا تشغّل PostgreSQL أو Redis داخل ملف التطبيق الإنتاجي. أنشئهما كـ Resources
مدارة في Coolify، وخذ عناوين الاتصال **الداخلية** الخاصة بهما. هذا يجعل
الترقية والنسخ والاستعادة مستقلة عن دورة نشر التطبيق.

## 1. إنشاء الموارد

1. أنشئ PostgreSQL 16 في Coolify، ثم Redis 7 في المشروع نفسه.
2. احتفظ بهما على الشبكة الداخلية؛ لا تمنح قاعدة البيانات أو Redis نطاقًا
   عامًا.
3. أنشئ Docker Compose Application من مستودع الباك إند، واجعل Compose file
   هو `docker-compose.coolify.yml` وBase directory هو `/`.
4. اربط النطاق العام بخدمة `web` فقط، واختر المنفذ الداخلي `8000`. لا تضف
   نطاقًا إلى `worker`.

## 2. أمر ما قبل النشر وفحص الصحة

اضبط في Coolify **Pre-deployment Command** التالي مرة واحدة لكل نشر:

```sh
python manage.py migrate --noinput
```

لا تشغّل `migrate` تلقائيًا عند إقلاع كل نسخة web أو worker؛ ذلك يسبب سباقًا
عند إعادة التشغيل أو التوسع الأفقي. يجمع web ملفات static عند الإقلاع
(`COLLECT_STATIC=true`) ويخدمها WhiteNoise.

اضبط Health Check للخدمة `web` كالآتي:

```text
Path: /readyz/
Port: 8000
```

`/health/` هو فحص liveness فقط. أما `/readyz/` فيتحقق من اتصال PostgreSQL،
ولا ينتظر خدمات الذكاء حتى لا يحجب الوظائف الأساسية عند بطء نموذج خارجي.

## 3. متغيرات البيئة في Coolify

أدخلها في واجهة Coolify، لا في Git ولا في ملف `.env` مرفوع:

```dotenv
DEBUG=false
DJANGO_SECRET_KEY=<secret عشوائي بطول 48 بايت أو أكثر>
ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com

# من موارد Coolify الداخلية
DATABASE_URL=postgresql://USER:PASSWORD@POSTGRES_INTERNAL_HOST:5432/DATABASE
DATABASE_SSL_REQUIRE=false
DATABASE_CONN_MAX_AGE=600
REDIS_URL=redis://:PASSWORD@REDIS_INTERNAL_HOST:6379/0
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# عناوين داخلية خاصة لخدمات الذكاء، وليست نطاقات عامة
AI_SYMPTOMS_URL=http://nlp:8000/analyze-symptoms
AI_VISION_URL=http://vision:8000/vision/analyze
AI_FUSION_URL=http://fusion:8000/fusion/analyze-case
AI_ENGINE_TIMEOUT=30

PRIVATE_MEDIA_ROOT=/app/private_media
BACKUP_DIRECTORY=/app/backups
BACKUP_STORAGE_TYPE=local
BACKUP_RESTORE_ENABLED=false
```

لا تضع `${REDIS_URL}` حرفيًا إذا لم تكن واجهة Coolify توسّع متغيرات البيئة
المتداخلة في هذا السياق؛ انسخ قيمة Redis الداخلية نفسها إلى المتغيرات الثلاثة.
استخدم `DATABASE_SSL_REQUIRE=true` فقط عندما تتصل بقاعدة خارج الشبكة الخاصة
وتتطلب TLS فعليًا.

## 4. التخزين والنسخ الاحتياطي

- الـvolumes في Compose تحفظ المرفقات الخاصة ومساحة عمل النسخ محليًا على
  خادم Coolify. لا تجعلها بديلًا لنسخة مستقلة عن الخادم.
- لا تركّب `PRIVATE_MEDIA_ROOT` أو `backups` كمسار عام في proxy.
- محرك النسخ الحالي يرفض نوع تخزين غير مدعوم بدل الإبلاغ عن نجاح كاذب. قبل
  التعامل مع بيانات حقيقية، اضبط وجهة backup خارجية موثقة ونفّذ restore drill
  إلى قاعدة وvolume منفصلين.

## 5. بوابة ما بعد النشر

نفّذ من خارج الشبكة الخاصة:

```sh
curl -fsS https://api.example.com/health/
curl -fsS https://api.example.com/readyz/
```

ثم راجع سجلات `web` و`worker` في Coolify وتأكد من ظهور worker متصلًا بـRedis.
تحقق كذلك من WebSocket عبر النطاق HTTPS نفسه، ومن CORS باستخدام نطاق الواجهة
الحقيقي فقط.

## ملاحظات تشغيلية

- لا تُنشر أسرار النسخة القديمة أو `DATABASE_URL` المرفق سابقًا؛ دوّرها قبل
  النشر إن كانت حقيقية.
- لا يعني نجاح Docker أو الاختبارات المحلية اعتمادًا سريريًا للذكاء. تبقى
  خدمات AI بحاجة إلى شبكة خاصة ومصادقة خدمة واختبارات سريرية مستقلة.
- عند التوسع إلى أكثر من نسخة web، أبقِ أمر migration في مرحلة ما قبل النشر
  فقط، واجعل Redis وPostgreSQL خارجيين مشتركين بين النسخ.
