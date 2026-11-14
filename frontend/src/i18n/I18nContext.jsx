import React, { createContext, useContext, useState, useEffect } from 'react';
import en from './en.json';
import hi from './hi.json';

const translations = { en, hi };

const I18nContext = createContext({
  language: 'en',
  setLanguage: () => {},
  t: (key, params) => key,
});

export function I18nProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    try {
      const saved = localStorage.getItem('crowdwise_lang');
      return saved === 'hi' ? 'hi' : 'en';
    } catch {
      return 'en';
    }
  });

  const setLanguage = (lang) => {
    const valid = lang === 'hi' ? 'hi' : 'en';
    setLanguageState(valid);
    try {
      localStorage.setItem('crowdwise_lang', valid);
    } catch {}
  };

  useEffect(() => {
    document.documentElement.lang = language;
    if (language === 'hi') {
      document.body.classList.add('lang-hi');
    } else {
      document.body.classList.remove('lang-hi');
    }
  }, [language]);

  const t = (path, params = {}) => {
    const dict = translations[language] || translations.en;
    const fallbackDict = translations.en;

    const resolve = (obj, p) => {
      return p.split('.').reduce((prev, curr) => (prev && prev[curr] !== undefined ? prev[curr] : null), obj);
    };

    let text = resolve(dict, path);
    if (!text && dict !== fallbackDict) {
      text = resolve(fallbackDict, path);
    }
    if (!text) return path;

    // Replace {{param}} variables
    if (params && typeof params === 'object') {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(new RegExp(`{{\\s*${k}\\s*}}`, 'g'), String(v));
      });
    }

    return text;
  };

  return (
    <I18nContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
