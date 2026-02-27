import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import { LanguageAbbreviation } from '@/constants/common';
import translation_en from './en';
import { createTranslationTable, flattenObject } from './until';
import translation_vi from './vi';
import translation_zh from './zh';

const resources = {
  [LanguageAbbreviation.En]: translation_en,
  [LanguageAbbreviation.Vi]: translation_vi,
  [LanguageAbbreviation.Zh]: translation_zh,
};
const enFlattened = flattenObject(translation_en);
const viFlattened = flattenObject(translation_vi);
const zhFlattened = flattenObject(translation_zh);

export const translationTable = createTranslationTable(
  [enFlattened, viFlattened, zhFlattened],
  ['English', 'Vietnamese', 'Chinese'],
);
i18n
  .use(initReactI18next)
  .use(LanguageDetector)
  .init({
    detection: {
      lookupLocalStorage: 'lng',
    },
    supportedLngs: Object.values(LanguageAbbreviation),
    resources,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
