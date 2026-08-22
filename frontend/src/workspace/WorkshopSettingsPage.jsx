export default function WorkshopSettingsPage({ profile, setProfile, logo, setLogo, onSubmit }) {
  const change = (key) => (event) => setProfile({ ...profile, [key]: event.target.value })
  return <section className="form-card workshop-settings">
    <div className="section-heading"><div><h2>هوية وبيانات الورشة</h2><p>تظهر هذه البيانات في الفواتير الضريبية. التعديل متاح لمالك الورشة فقط.</p></div>{profile.logo_url && <img className="workshop-logo-preview" src={profile.logo_url} alt="شعار الورشة" />}</div>
    <form className="entry-form" onSubmit={onSubmit}>
      <label>اسم الورشة<input required value={profile.name} onChange={change('name')} /></label>
      <label>الاسم القانوني<input required value={profile.legal_name} onChange={change('legal_name')} /></label>
      <label>الرقم الضريبي<input required inputMode="numeric" pattern="[0-9]{15}" minLength="15" maxLength="15" value={profile.tax_number} onChange={change('tax_number')} title="يجب أن يتكون الرقم الضريبي من 15 رقماً" /></label>
      <label>السجل التجاري<input value={profile.commercial_registration} onChange={change('commercial_registration')} /></label>
      <label>رقم الاتصال<input required type="tel" value={profile.phone} onChange={change('phone')} /></label>
      <label>البريد الإلكتروني<input type="email" value={profile.email} onChange={change('email')} /></label>
      <label>الموقع الإلكتروني<input type="url" placeholder="https://" value={profile.website} onChange={change('website')} /></label>
      <label>المدينة<input required value={profile.city} onChange={change('city')} /></label>
      <label>الحي<input required value={profile.district} onChange={change('district')} /></label>
      <label>الشارع<input required value={profile.street} onChange={change('street')} /></label>
      <label>رقم المبنى<input required value={profile.building_number} onChange={change('building_number')} /></label>
      <label>الرمز البريدي<input required inputMode="numeric" value={profile.postal_code} onChange={change('postal_code')} /></label>
      <label>الرقم الإضافي<input value={profile.additional_number} onChange={change('additional_number')} /></label>
      <label className="wide"><input type="checkbox" checked={Boolean(profile.auto_deliver_paid_ready_jobs)} onChange={(event) => setProfile({ ...profile, auto_deliver_paid_ready_jobs: event.target.checked })} /> تسليم البطاقة الجاهزة آليًا عند سداد الفاتورة بالكامل</label>
      <label>خط العرض<input type="number" min="-90" max="90" step="0.000001" value={profile.latitude} onChange={change('latitude')} /></label>
      <label>خط الطول<input type="number" min="-180" max="180" step="0.000001" value={profile.longitude} onChange={change('longitude')} /></label>
      <label className="wide">العنوان الوطني<textarea value={profile.national_address} onChange={change('national_address')} placeholder="يمكن إضافة وصف العنوان الوطني كاملاً" /></label>
      <label className="wide">شعار الورشة (PNG أو JPG، بحد أقصى 2MB)<input accept="image/png,image/jpeg,image/webp" type="file" onChange={(event) => setLogo(event.target.files?.[0] || null)} />{logo && <small>{logo.name}</small>}</label>
      <button className="primary">حفظ إعدادات الورشة</button>
    </form>
  </section>
}
