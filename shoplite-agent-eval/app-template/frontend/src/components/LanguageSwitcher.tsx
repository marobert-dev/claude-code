import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { SUPPORTED_LANGUAGES } from '../i18n';

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const id = useId();

  return (
    <div className="language-switcher">
      <label htmlFor={id}>{t('language.label')}</label>
      <select id={id} value={i18n.language} onChange={(event) => void i18n.changeLanguage(event.target.value)}>
        {SUPPORTED_LANGUAGES.map((language) => (
          <option key={language} value={language} lang={language}>
            {t(`language.${language}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
