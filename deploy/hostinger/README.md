# نشر خادم عزم المركزي على Hostinger VPS

هذا النشر يشغّل الواجهة وDjango وPostgreSQL وRedis وCelery وWebSocket في الخادم نفسه. لا تتعرض PostgreSQL أو Redis للإنترنت؛ المنافذ العامة الوحيدة هي `80` و`443`.

## المتطلبات قبل النشر

1. في مدير DNS لدى Hostinger، غيّر سجل `A` للنطاق `tidesight.cloud` ليشير إلى عنوان VPS الظاهر في صفحة الخادم. لا تطلب شهادة HTTPS قبل اكتمال انتشار DNS.
2. افتح في جدار الحماية المنافذ `22` و`80` و`443` فقط.
3. من لوحة Hostinger أو SSH ثبّت Docker Engine مع Docker Compose plugin على Ubuntu 24.04.
4. انسخ المشروع إلى الخادم عبر Git أو SFTP. لا ترفع ملفات `.env` أو مفاتيح خاصة إلى مستودع عام.

## التشغيل الأولي

```bash
cd /opt/azm/deploy/hostinger
cp .env.example .env
nano .env
docker compose up -d --build
docker compose ps
```

خدمة `api` تنفذ `migrate --noinput` تلقائيًا بعد سلامة PostgreSQL وقبل بدء Daphne. راجع سجلات الخدمة عند أول نشر للتأكد من نجاح الترحيلات قبل فتح النظام للمستخدمين.

للتحقق من بنية Compose محلياً دون إنشاء ملف أسرار، نفّذ:

```bash
AZM_ENV_FILE=.env.example docker compose --env-file .env.example config -q
```

بعد صدور شهادة HTTPS تلقائياً من Caddy، يفتح النظام على `https://AZM_DOMAIN`. تؤدي واجهة `https://AZM_DOMAIN/api/...` وWebSocket `wss://AZM_DOMAIN/ws/...` إلى الخادم نفسه.

## النسخ الاحتياطي والاستعادة

يوفّر المشروع سكربتين جاهزين في `scripts/backup.sh` و`scripts/restore.sh` (يعملان على أي جهاز فيه bash وDocker، بما في ذلك خادم Hostinger نفسه). تم اختبار دورة النسخ والاستعادة بالكامل فعلياً (نسخ → رفع → تدمير محلي → تنزيل → استعادة → تحقق من البيانات). وجهة الإنتاج الحالية هي Amazon S3.

### إعداد وجهة التخزين السحابي (مرة واحدة لكل خادم)

المخزن السحابي الحالي للمشروع هو Amazon S3 في منطقة `eu-north-1`، bucket باسم **`azm-833565098460-eu-north-1-an`**، عبر remote في `rclone` باسم **`azm-s3`**. أنشئ التكوين على الخادم:

```bash
apt-get install -y rclone   # أو حسب توزيعة الخادم
rclone config
```

اختر `n` (New remote) → الاسم `azm-s3` → النوع `s3` → المزود `AWS` → المنطقة `eu-north-1`. استخدم مفتاح IAM **مخصصًا للنسخ الاحتياطي فقط** ومقيدًا بالحاوية والمسار `azm/*`، ولا تستخدم مفتاح root.

تحقق من الاتصال:

```bash
rclone lsd azm-s3:azm-833565098460-eu-north-1-an
```

**لا تستخدم بيانات root أو مستخدم IAM واسع الصلاحيات في سكربت آلي على الخادم**. احمِ ملف `rclone.conf` بصلاحية `600`، واقصر السياسة على الحاوية والمسار المذكورين.

### نسخ احتياطي يدوي أو مجدول

```bash
cd /opt/azm
./scripts/backup.sh \
  --compose-file deploy/hostinger/compose.yml \
  --env-file deploy/hostinger/.env \
  --backup-dir /opt/azm-backups \
  --retention-days 14 \
  --rclone-remote azm-s3:azm-833565098460-eu-north-1-an/azm
```

ينشئ السكربت في كل تشغيل:
- تفريغاً مضغوطاً لقاعدة البيانات (`azm-db-<timestamp>.sql.gz`).
- أرشيف مضغوط لمجلد الوثائق المشفّرة (`azm-media-<timestamp>.tar.gz`).
- ملف `sha256` للتحقق من سلامة الملفين قبل أي استعادة.
- رفعاً إلى المسار `azm/` داخل bucket `azm-833565098460-eu-north-1-an` على Amazon S3 عبر [`rclone`](https://rclone.org) طالما مُرِّر `--rclone-remote`. **لا تعتمد فقط على القرص المحلي للخادم** — النسخة يجب أن تُرفع لموقع مختلف فعلياً لتحمي من فقدان الخادم بالكامل.
- حذف النسخ المحلية الأقدم من `--retention-days` (افتراضياً 14 يوماً).

يُنشأ تفريغ PostgreSQL دون أوامر ملكية أو صلاحيات (`--no-owner --no-acl`) حتى
يمكن استعادته في بيئة تعافٍ تستخدم اسم مستخدم قاعدة مختلفًا عن الإنتاج.

### الجدولة اليومية عبر cron

يفضل في Ubuntu استخدام وحدة `systemd` الموجودة في `deploy/hostinger/systemd` لأنها تسجل نتيجة كل تشغيل، تعوض التشغيل الفائت بعد إعادة تشغيل الخادم، وترفض النسخ المحلية فقط.

```bash
cd /opt/azm/deploy/hostinger
cp backup.env.example backup.env
chmod 600 backup.env
nano backup.env
cp systemd/azm-backup.service systemd/azm-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now azm-backup.timer
systemctl start azm-backup.service
systemctl status azm-backup.service
systemctl list-timers azm-backup.timer
```

يجب أن يحتوي `backup.env` على `AZM_BACKUP_REQUIRE_REMOTE=true` ووجهة `AZM_BACKUP_REMOTE`. ويمكن ضبط `AZM_BACKUP_HEALTHCHECK_URL` لإرسال نبضة نجاح أو `/fail` عند فشل النسخ. يتحقق السكربت من الملفات المرفوعة بواسطة `rclone check` قبل إعلان النجاح.

بديلًا عن ذلك يمكن استخدام cron:

```bash
crontab -e
```

أضف سطراً لتشغيل النسخ يومياً في الساعة 2 صباحاً بتوقيت الخادم، مع تسجيل المخرجات:

```
0 2 * * * cd /opt/azm && ./scripts/backup.sh --compose-file deploy/hostinger/compose.yml --env-file deploy/hostinger/.env --backup-dir /opt/azm-backups --retention-days 14 --rclone-remote azm-s3:azm-833565098460-eu-north-1-an/azm >> /opt/azm-backups/backup.log 2>&1
```

راقب `/opt/azm-backups/backup.log` دورياً، أو أضف تنبيهاً (مثل [healthchecks.io](https://healthchecks.io)) يستدعيه السكربت عند النجاح للتأكد من عدم توقف الجدولة بصمت.

### الاستعادة (اختبرها دورياً على بيئة منفصلة قبل الاعتماد عليها)

عند فقدان الخادم بالكامل، نزّل أحدث نسخة من Amazon S3 أولاً:

```bash
mkdir -p /opt/azm-restore && cd /opt/azm-restore
rclone copy azm-s3:azm-833565098460-eu-north-1-an/azm . --include "azm-*-20260810-*"   # عدّل التاريخ/الاسم حسب النسخة المطلوبة
sha256sum -c azm-20260810-*.sha256   # تأكد من سلامة الملفات قبل المتابعة
```

ثم شغّل الاستعادة:

```bash
cd /opt/azm
./scripts/restore.sh \
  --compose-file deploy/hostinger/compose.yml \
  --env-file deploy/hostinger/.env \
  --db-dump /opt/azm-restore/azm-db-20260810-020000.sql.gz \
  --media-archive /opt/azm-restore/azm-media-20260810-020000.tar.gz \
  --checksum-file /opt/azm-restore/azm-20260810-020000.sha256
```

عند اختبار الاستعادة باستخدام ملف Compose نفسه وبيئة معزولة، مرّر اسم المشروع
صراحةً مثل `--project-name azm-staging`. يمنع ذلك استنتاج اسم مشروع الإنتاج من
مسار ملف Compose واستهداف حجومه بالخطأ. يرفض التحقق المدمج بدء الاستعادة إذا لم
تطابق الملفات ملف `sha256` الممرر.

**تحذير**: هذا الأمر يحذف قاعدة البيانات الحالية بالكامل ويستبدل محتوى مجلد الوثائق. يطلب تأكيداً تفاعلياً (`Type 'yes' to continue`) ما لم يُمرَّر `--yes`. لا تُشغّله على الإنتاج دون التأكد أولاً من صحة النسخة عبر ملف `sha256` المرافق وتجربتها على بيئة اختبار منفصلة أولاً.

حافظ على نسخة ثابتة من `DOCUMENT_ENCRYPTION_KEY`؛ تغييرها يمنع فك تشفير الوثائق القديمة حتى بعد استعادة صحيحة للملفات.

### التحديث

```bash
git pull
docker compose up -d --build
```

تطبق خدمة `api` الترحيلات تلقائيًا قبل بدء الخادم. لا تشغل أكثر من نسخة API لأول مرة أثناء ترحيل كبير إلا بعد تنفيذ الترحيل كخطوة إصدار منفصلة.

## فحص Staging المتكرر

بعد تشغيل `db` و`redis` و`api`، نفّذ من PowerShell داخل مجلد `deploy/hostinger`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\..\scripts\staging-smoke.ps1 -EnvironmentFile .env -TimeoutSeconds 180
```

يتحقق الفحص من صحة ملف Compose، وينتظر وصول PostgreSQL وRedis وAPI وCelery worker وCelery beat جميعًا إلى الحالة `healthy`، ثم يستدعي `/healthz/` داخليًا للتأكد من اتصال التبعيات، ويتأكد أن عملية التطبيق الرئيسية لا تعمل بصلاحية root. عند الفشل يعرض حالة الخدمات وآخر سجلات API والعامل والمجدول.

فحص العامل ينفذ `Celery ping` موجّهًا إلى عقدته الفعلية، وفحص beat يتحقق من بقاء عملية المجدول المسجلة في ملف PID. لذلك لا يكفي ظهور الحاوية بحالة `running` وحدها لاعتماد النشر.

تبدأ صورة Backend بمدخل قصير لضبط ملكية مجلدي `logs` و`media` المركبين، ثم تُسقط الصلاحيات فورًا وتشغّل التطبيق بالمستخدم `azm`. لا تستبدل هذا المدخل بأمر يعمل كـroot.
