from .translations import TRANSLATIONS, LANGUAGES

_current_language = 'en'


def set_language(lang_code):
    global _current_language
    if lang_code in TRANSLATIONS:
        _current_language = lang_code
        return True
    return False


def get_language():
    return _current_language


def tr(key):
    lang_dict = TRANSLATIONS.get(_current_language, TRANSLATIONS['en'])
    return lang_dict.get(key, TRANSLATIONS['en'].get(key, key))
