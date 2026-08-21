# حزمة عزم لسطح المكتب

تنتج هذه الوحدة ملفي Windows مستقلين:

- `Azm Setup <version>.exe`: مثبت Windows عادي مع اختصارات قائمة ابدأ وسطح المكتب.
- `Azm <version>.exe`: نسخة محمولة لا تحتاج إلى تثبيت.

كلاهما يضم محرك Electron وواجهة عزم؛ لا يحتاج الموظف إلى Node.js أو Python أو متصفح أو إضافة. عند أول تشغيل يضع مدير النظام عنوان API المركزي، مثل `https://api.example.com/api`، ويحفظ محلياً للمستخدم الحالي.

## إنشاء الحزمة

```powershell
Push-Location desktop
npm.cmd install
npm.cmd run dist:win
```

تظهر الملفات النهائية في `desktop/release/`. يلزم نشر API عزم المركزي عبر HTTPS وWebSocket عبر WSS قبل توزيع العميل على الموظفين. قبل التوزيع الخارجي، وقّع ملف المثبت بشهادة Windows Code Signing لتجنب تحذير SmartScreen.
