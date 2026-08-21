# تطبيق عزم للجوال

تطبيق Expo واحد يعمل على Android وiOS. يستخدم حسابات نظام عزم نفسها ويعرض البيانات بحسب الدور:

- الفني: بطاقات العمل المسندة إليه، تحديث الحالة إلى «قيد الإصلاح» أو «جاهزة»، إضافة نتيجة الفحص، وبدء/إكمال مهامه.
- المدير: عرض جميع البطاقات والمهام وتحديث حالات البطاقات.
- المحاسب: عرض تشغيلي مباشر للبطاقات والمهام من دون صلاحيات تعديل.

تصل التحديثات فوراً عبر WebSocket مؤمّن برمز JWT وRedis عند تعديل بطاقة أو مهمة، مع تحديث احتياطي كل 10 ثوانٍ وعند العودة للتطبيق إذا انقطع الاتصال.

## التشغيل على هاتف فعلي

1. ثبّت الحزم مرة واحدة:

   ```powershell
   Push-Location mobile
   npm.cmd install
   ```

2. انسخ `.env.example` إلى `.env`، ثم ضع عنوان IP المحلي للحاسب الذي يشغّل Django، مثال:

   ```env
   EXPO_PUBLIC_API_BASE_URL=http://192.168.1.50:8000/api
   ```

3. تأكد من أن الهاتف والحاسب على شبكة Wi-Fi نفسها. شغّل Django عبر ASGI ليستقبل اتصالات الشبكة، واضبط `DJANGO_ALLOWED_HOSTS` ليشمل عنوان الحاسب أو اسم النطاق. يجب أن يعمل Redis، وهو مستخدم أيضاً لتزامن WebSocket. في بيئة الإنتاج يجب استخدام API وWebSocket عبر HTTPS/WSS.

4. شغّل التطبيق ثم امسح QR عبر Expo Go:

   ```powershell
   npm.cmd start
   ```

## حزم مستقلة للمستخدمين

لا يحتاج المستخدم النهائي إلى Expo Go أو أي إضافة:

- Android للتجربة الداخلية: `npm.cmd run build:android:apk` وينتج ملف APK قابل للتثبيت مباشرة.
- Android للمتجر: `npm.cmd run build:android:store` وينتج AAB للنشر في Google Play.
- iPhone/iPad: `npm.cmd run build:ios:store` وينتج IPA للتوزيع عبر TestFlight أو App Store.

قبل البناء، استبدل معرّفات `android.package` و`ios.bundleIdentifier` في `app.json` بمعرّفات المؤسسة الفريدة وسجّل الدخول بحساب Expo. تقوم EAS بإدارة مفاتيح توقيع Android وشهادات iOS أو استخدام مفاتيح المؤسسة. يتطلب نشر iOS عضوية Apple Developer، ويتطلب النشر في Google Play حساب Google Play Console.
