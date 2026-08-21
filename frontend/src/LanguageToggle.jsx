function LanguageToggle({ language, onChange, compact = false }) {
  const nextLanguage = language === 'ar' ? 'en' : 'ar'
  return <button className={`language-toggle${compact ? ' compact' : ''}`} type="button" onClick={() => onChange(nextLanguage)} aria-label={language === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}>{language === 'ar' ? 'English' : 'العربية'}</button>
}

export default LanguageToggle
