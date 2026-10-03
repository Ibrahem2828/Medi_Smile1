# ربط الفرونت بالباك أثناء التطوير (localhost)

## الخيار 1 — اتصال الفرونت المحلي بالـ API المنشور (الأسرع)
- **Base URL:** `https://api.medismile.xn--mgbaab0cxheq.tech`
- الـ API يسمح بالأصول `http(s)://localhost[:port]` و`http(s)://127.0.0.1[:port]` و`http://[::1][:port]` (أي منفذ: 3000، 5173، 4200، 5500 ...). غير ذلك يُرفض.
- الترويسات المسموحة: `Authorization`, `Content-Type`, `Accept`, `Accept-Language`, `X-Request-Id`, `X-Requested-With`.
- الطرق المسموحة: `GET POST PUT PATCH DELETE OPTIONS`. الـ preflight يُخزَّن 24 ساعة.
- ترويسة `Content-Disposition` مكشوفة للمتصفح (أسماء ملفات التقارير والمرفقات).
- **لا تُرسل الكوكيز** (`withCredentials` / `credentials: "include"` غير مفعّل): المصادقة بـ JWT في الترويسة.

```js
// axios
const api = axios.create({ baseURL: "https://api.medismile.xn--mgbaab0cxheq.tech" });
api.interceptors.request.use(cfg => {
  const t = localStorage.getItem("access");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// تسجيل الدخول (المسار حسب الدور: patient | student | supervisor | university-admin | tech-support)
const { data } = await api.post("/api/accounts/login/patient/", { email, password });
localStorage.setItem("access", data.tokens.access);
localStorage.setItem("refresh", data.tokens.refresh);
```
> الـ access token عمره 15 دقيقة؛ جدّده بالـ refresh token (يُدوَّر عند كل استخدام ويُلغى القديم). مسارات الـ API كلها تحت `/api/`.

حسابات الاختبار موجودة في ملف `medismile_accounts.txt` عند صاحب المشروع (لا تُرفع إلى git).

## الخيار 2 — تشغيل الباك على جهازك
1) أنشئ ملف `.env` (غير مرفوع إلى git) بجانب `manage.py`:
```env
DEBUG=True
DJANGO_SECRET_KEY=dev-only-change-me
DATABASE_URL=sqlite:///db.sqlite3
# مع DEBUG=True يُسمح بكل أصول CORS تلقائياً (للباك المحلي فقط)
```
2) ثم:
```bash
python -m venv venv && venv\Scripts\activate     # ويندوز؛ على لينكس/ماك: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```
3) الفرونت يشير إلى `http://localhost:8000`.
- خدمات الذكاء (`AI_*_URL`) غير لازمة عند `DEBUG=True`؛ ضع روابط الإنتاج إن أردت اختبار التحليل:
  `AI_SYMPTOMS_URL=https://nlp.medismile.xn--mgbaab0cxheq.tech`، `AI_FUSION_URL=https://fusion.medismile.xn--mgbaab0cxheq.tech`، `AI_VISION_URL=https://ibrahim28-medismile-vision-ai.hf.space`.
- WebSocket يحتاج Redis؛ بدونه تعمل واجهات HTTP فقط.

## متغيرات CORS (للمسؤول عن الخادم)
| المتغير | الوظيفة |
|---|---|
| `CORS_ALLOWED_ORIGINS` | قائمة أصول الإنتاج مفصولة بفواصل (مطلوبة عند `DEBUG=False`) |
| `CORS_ALLOW_LOCALHOST` | `true` يسمح بأصول localhost (الافتراضي: `true` فقط عند `DEBUG=True`). **اجعله `false` عند الإطلاق الرسمي** |
| `CORS_ALLOW_CREDENTIALS` | `false` افتراضياً (JWT بلا كوكيز) |
| `CORS_PREFLIGHT_MAX_AGE` | ثواني تخزين الـ preflight (86400) |

## استكشاف الأخطاء
| العرض في المتصفح | السبب | الحل |
|---|---|---|
| `blocked by CORS policy: No 'Access-Control-Allow-Origin'` | أصل الفرونت غير مسموح | تأكد من `localhost`/`127.0.0.1` ومن أنك لا تفتح الصفحة من `file://` (الأصل `null` مرفوض) أو من عنوان الشبكة `192.168.x.x` (غير مسموح؛ اطلب إضافته) |
| `Request header field authorization is not allowed` | ترويسة غير مسموحة | استخدم فقط الترويسات المذكورة أعلاه |
| `Response to preflight request doesn't pass ... redirect` | طلب إلى `http://` يُحوَّل إلى `https` | استخدم عنوان `https://` |
| `401` بعد 15 دقيقة | انتهى الـ access token | جدّد بالـ refresh token |
| طلبات من `127.0.0.1` ترفضها `CSRF`/`403` | الـ API لا يستخدم كوكيز | أزل `withCredentials` |
