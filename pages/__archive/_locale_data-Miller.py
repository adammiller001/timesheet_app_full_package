# Copyright 2012 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Data used by the tornado.locale module."""

LOCALE_NAMES = {
    "af_ZA": {"name_en": "Afrikaans", "name": "Afrikaans"},
    "am_ET": {"name_en": "Amharic", "name": "áŠ áˆ›áˆ­áŠ›"},
    "ar_AR": {"name_en": "Arabic", "name": "Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©"},
    "bg_BG": {"name_en": "Bulgarian", "name": "Ð‘ÑŠÐ»Ð³Ð°Ñ€ÑÐºÐ¸"},
    "bn_IN": {"name_en": "Bengali", "name": "à¦¬à¦¾à¦‚à¦²à¦¾"},
    "bs_BA": {"name_en": "Bosnian", "name": "Bosanski"},
    "ca_ES": {"name_en": "Catalan", "name": "CatalÃ "},
    "cs_CZ": {"name_en": "Czech", "name": "ÄŒeÅ¡tina"},
    "cy_GB": {"name_en": "Welsh", "name": "Cymraeg"},
    "da_DK": {"name_en": "Danish", "name": "Dansk"},
    "de_DE": {"name_en": "German", "name": "Deutsch"},
    "el_GR": {"name_en": "Greek", "name": "Î•Î»Î»Î·Î½Î¹ÎºÎ¬"},
    "en_GB": {"name_en": "English (UK)", "name": "English (UK)"},
    "en_US": {"name_en": "English (US)", "name": "English (US)"},
    "es_ES": {"name_en": "Spanish (Spain)", "name": "EspaÃ±ol (EspaÃ±a)"},
    "es_LA": {"name_en": "Spanish", "name": "EspaÃ±ol"},
    "et_EE": {"name_en": "Estonian", "name": "Eesti"},
    "eu_ES": {"name_en": "Basque", "name": "Euskara"},
    "fa_IR": {"name_en": "Persian", "name": "ÙØ§Ø±Ø³ÛŒ"},
    "fi_FI": {"name_en": "Finnish", "name": "Suomi"},
    "fr_CA": {"name_en": "French (Canada)", "name": "FranÃ§ais (Canada)"},
    "fr_FR": {"name_en": "French", "name": "FranÃ§ais"},
    "ga_IE": {"name_en": "Irish", "name": "Gaeilge"},
    "gl_ES": {"name_en": "Galician", "name": "Galego"},
    "he_IL": {"name_en": "Hebrew", "name": "×¢×‘×¨×™×ª"},
    "hi_IN": {"name_en": "Hindi", "name": "à¤¹à¤¿à¤¨à¥à¤¦à¥€"},
    "hr_HR": {"name_en": "Croatian", "name": "Hrvatski"},
    "hu_HU": {"name_en": "Hungarian", "name": "Magyar"},
    "id_ID": {"name_en": "Indonesian", "name": "Bahasa Indonesia"},
    "is_IS": {"name_en": "Icelandic", "name": "Ãslenska"},
    "it_IT": {"name_en": "Italian", "name": "Italiano"},
    "ja_JP": {"name_en": "Japanese", "name": "æ—¥æœ¬èªž"},
    "ko_KR": {"name_en": "Korean", "name": "í•œêµ­ì–´"},
    "lt_LT": {"name_en": "Lithuanian", "name": "LietuviÅ³"},
    "lv_LV": {"name_en": "Latvian", "name": "LatvieÅ¡u"},
    "mk_MK": {"name_en": "Macedonian", "name": "ÐœÐ°ÐºÐµÐ´Ð¾Ð½ÑÐºÐ¸"},
    "ml_IN": {"name_en": "Malayalam", "name": "à´®à´²à´¯à´¾à´³à´‚"},
    "ms_MY": {"name_en": "Malay", "name": "Bahasa Melayu"},
    "nb_NO": {"name_en": "Norwegian (bokmal)", "name": "Norsk (bokmÃ¥l)"},
    "nl_NL": {"name_en": "Dutch", "name": "Nederlands"},
    "nn_NO": {"name_en": "Norwegian (nynorsk)", "name": "Norsk (nynorsk)"},
    "pa_IN": {"name_en": "Punjabi", "name": "à¨ªà©°à¨œà¨¾à¨¬à©€"},
    "pl_PL": {"name_en": "Polish", "name": "Polski"},
    "pt_BR": {"name_en": "Portuguese (Brazil)", "name": "PortuguÃªs (Brasil)"},
    "pt_PT": {"name_en": "Portuguese (Portugal)", "name": "PortuguÃªs (Portugal)"},
    "ro_RO": {"name_en": "Romanian", "name": "RomÃ¢nÄƒ"},
    "ru_RU": {"name_en": "Russian", "name": "Ð ÑƒÑÑÐºÐ¸Ð¹"},
    "sk_SK": {"name_en": "Slovak", "name": "SlovenÄina"},
    "sl_SI": {"name_en": "Slovenian", "name": "SlovenÅ¡Äina"},
    "sq_AL": {"name_en": "Albanian", "name": "Shqip"},
    "sr_RS": {"name_en": "Serbian", "name": "Ð¡Ñ€Ð¿ÑÐºÐ¸"},
    "sv_SE": {"name_en": "Swedish", "name": "Svenska"},
    "sw_KE": {"name_en": "Swahili", "name": "Kiswahili"},
    "ta_IN": {"name_en": "Tamil", "name": "à®¤à®®à®¿à®´à¯"},
    "te_IN": {"name_en": "Telugu", "name": "à°¤à±†à°²à±à°—à±"},
    "th_TH": {"name_en": "Thai", "name": "à¸ à¸²à¸©à¸²à¹„à¸—à¸¢"},
    "tl_PH": {"name_en": "Filipino", "name": "Filipino"},
    "tr_TR": {"name_en": "Turkish", "name": "TÃ¼rkÃ§e"},
    "uk_UA": {"name_en": "Ukraini ", "name": "Ð£ÐºÑ€Ð°Ñ—Ð½ÑÑŒÐºÐ°"},
    "vi_VN": {"name_en": "Vietnamese", "name": "Tiáº¿ng Viá»‡t"},
    "zh_CN": {"name_en": "Chinese (Simplified)", "name": "ä¸­æ–‡(ç®€ä½“)"},
    "zh_TW": {"name_en": "Chinese (Traditional)", "name": "ä¸­æ–‡(ç¹é«”)"},
}
