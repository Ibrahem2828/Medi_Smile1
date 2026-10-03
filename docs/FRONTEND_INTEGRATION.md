# ربط الفرونت بالباك أثناء التطوير (localhost)

> ## ⚠️ استخدم `https://` دائماً — وإلا سيظهر خطأ CORS
> ```
> Access to XMLHttpRequest at 'http://api.medismile...' from origin 'http://localhost:3000' has been blocked by CORS policy:
> Response to preflight request doesn't pass access control check: Redirect is not allowed for a preflight request.
> ```
> هذا ليس خطأ في إعدادات CORS. الرابط `http://` (بدون `s`) يُحوَّل من السيرفر إلى `https://` (التحويل 307)، والمتصفح **يمنع أي تحويل أثناء الـ preflight**، فيفشل الطلب قبل أن يصل إلى الباك.
> **الحل: غيّر عنوان الـ API في الفرونت إلى `https://api.medismile.xn--mgbaab0cxheq.tech`** (انظر الأمثلة أدناه). لا يمكن ولا يجب السماح بـ http: كلمة المرور في طلب الدخول ستسير نصاً واضحاً.
>
> | الإطار | أين تغيّره |
> |---|---|
> | Vite | `.env`: `VITE_API_URL=https://api.medismile.xn--mgbaab0cxheq.tech` |
> | Create React App | `.env`: `REACT_APP_API_URL=https://api.medismile.xn--mgbaab0cxheq.tech` |
> | Next.js | `.env.local`: `NEXT_PUBLIC_API_URL=https://api.medismile.xn--mgbaab0cxheq.tech` |
> | Angular | `environment.ts`: `apiUrl: 'https://api.medismile.xn--mgbaab0cxheq.tech'` |
> | axios / fetch | `baseURL` / أول جزء من الرابط |
>
> بعد تغيير ملف `.env` **أعد تشغيل خادم التطوير** (`npm run dev` / `npm start`) لأن المتغيرات تُقرأ عند البدء فقط، وامسح كاش المتصفح (Ctrl+Shift+R).
> اختبار سريع من الـ Console داخل صفحة localhost:
> ```js
> fetch('https://api.medismile.xn--mgbaab0cxheq.tech/health/').then(r => r.json()).then(console.log)   // {status:'ok',...}
> ```


> ## ⚠️ وضع http المؤقت على السيرفر (للتطوير فقط)
> بطلب من صاحب المشروع، `http://api.medismile.xn--mgbaab0cxheq.tech` يعمل **بلا تحويل إلى https** لتفادي خطأ `Redirect is not allowed for a preflight request`.
> **لكن كلمات المرور وتوكنات JWT تسير نصاً واضحاً عبر http، فاستخدم حسابات الاختبار فقط ولا تُدخل بيانات حقيقية.** الأفضل دائماً `https://` أو الـ dev proxy أدناه.
> **يجب إيقافه قبل الإطلاق الرسمي:** على السيرفر `sh /root/disable_api_http.sh` (يعيد التحويل إلى https ويضبط `SECURE_SSL_REDIRECT=true`).

## الحل الأسهل للمطورين: وكيل التطوير (Dev Proxy) — لا CORS ولا تحويلات أصلاً
بدل أن يتصل المتصفح بالـ API مباشرة من `localhost:3000` (طلب من أصل آخر)، يُرسل الفرونت الطلبات إلى **خادم التطوير نفسه** ويمرّرها هو إلى الـ API عبر `https`.
فيرى المتصفح أن الطلب من نفس الأصل، فلا يوجد preflight ولا CORS ولا خطأ تحويل. وهو يعمل حتى لو بقي الرابط القديم في أجزاء من الكود. اجعل `baseURL` فارغاً (مسارات نسبية مثل `/api/accounts/login/patient/`).

**Vite** (`vite.config.js`):
```js
export default {
  server: { proxy: { '/api': { target: 'https://api.medismile.xn--mgbaab0cxheq.tech', changeOrigin: true, secure: true } } },
};
```
**Create React App** (ملف `src/setupProxy.js`، بعد `npm i http-proxy-middleware`):
```js
const { createProxyMiddleware } = require('http-proxy-middleware');
module.exports = app => app.use('/api', createProxyMiddleware({ target: 'https://api.medismile.xn--mgbaab0cxheq.tech', changeOrigin: true }));
```
**Next.js** (`next.config.js`):
```js
module.exports = { async rewrites() { return [{ source: '/api/:path*', destination: 'https://api.medismile.xn--mgbaab0cxheq.tech/api/:path*' }]; } };
```
**Angular** (`proxy.conf.json`، ثم `ng serve --proxy-config proxy.conf.json`):
```json
{ "/api": { "target": "https://api.medismile.xn--mgbaab0cxheq.tech", "secure": true, "changeOrigin": true } }
```
بعد التعديل أعد تشغيل خادم التطوير. هذا للتطوير فقط؛ في الإنتاج يُستخدم الرابط الكامل `https://` ونطاق الموقع المسموح في CORS.

---
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
