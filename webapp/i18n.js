/* Qayta Mini App: translations and helpers. Plain browser script (globals on window). */
"use strict";

var STRINGS = {
  uz: {
    "tab.scan": "Skan",
    "tab.map": "Xarita",
    "tab.prices": "Narxlar",
    "tab.me": "Men",

    "lang.title": "Til",
    "lang.name.uz": "O'zbekcha",
    "lang.name.ru": "Русский",
    "lang.name.en": "English",

    "common.loading": "Yuklanmoqda...",
    "common.error": "Xatolik yuz berdi. Keyinroq qayta urinib ko'ring.",
    "common.optional": "ixtiyoriy",
    "common.none": "—",
    "common.attribution": "© OpenStreetMap contributors",

    "scan.title": "Chiqindini skanerlash",
    "scan.text": "Mini ilova ichida kameradan foydalanib bo'lmaydi. Rasmni bot chatiga yuboring.",
    "scan.step1": "Buyumning aniq, yorug' rasmini oling",
    "scan.step2": "Rasmni shu chatga yuboring",
    "scan.step3": "Material, tayyorlash maslahatlari va narxni oling",
    "scan.button": "Chatga qaytish",

    "map.title": "Qayta ishlash xaritasi",
    "map.choose_material": "Materialni tanlang",
    "map.all_materials": "Barcha materiallar",
    "map.no_points": "Yaqin atrofda qabul punktlari topilmadi. Uni OpenStreetMap'ga qo'shishingiz mumkin.",
    "map.route": "Marshrut",
    "map.verified_on": "{date} sanasida tekshirilgan",
    "map.no_location": "Joylashuv aniqlanmadi. Ma'lum punktlar masofasiz ko'rsatilmoqda.",
    "map.open_osm": "OpenStreetMap'da ochish",
    "map.materials_unknown": "Qabul qilinadigan materiallar noma'lum, avval qo'ng'iroq qiling",
    "map.pick_city": "Shaharni tanlang yoki xaritaga bosing",
    "map.city.tashkent": "Toshkent",
    "map.city.ohangaron": "Ohangaron",
    "map.city.samarkand": "Samarqand",
    "map.accepts": "Qabul qiladi",
    "map.phone": "Telefon",
    "map.hours": "Ish vaqti",
    "map.distance": "Masofa",
    "map.loading_points": "Punktlar qidirilmoqda...",
    "map.overpass_failed": "Jonli xarita ma'lumotlari yuklanmadi. Faqat tekshirilgan punktlar ko'rsatilmoqda.",

    "prices.title": "Chiqindi narxlari",
    "prices.col.material": "Material",
    "prices.col.point": "Punkt",
    "prices.col.price": "Narx (so'm/kg)",
    "prices.col.source": "Manba",
    "prices.col.date": "Sana",
    "prices.empty": "Hozircha tasdiqlangan narxlar yo'q. Siz birinchi bo'lib xabar bering!",
    "prices.report_link": "Narx haqida xabar berish",
    "prices.note": "Narxlar faqat tekshirilgan yozuvlardan olinadi, manba va sana ko'rsatiladi.",
    "price.outdated": "eskirgan bo'lishi mumkin",
    "price.line": "💰 Eng yaxshi narx: {price} so'm/kg ({source}, {date})",
    "nearest.line": "📍 Eng yaqin punkt: {name}, {distance}",

    "me.title": "Mening hissam",
    "me.no_data": "Statistikangizni ko'rish uchun botga /stats buyrug'ini yuboring.",
    "me.thresholds": "Darajalar",
    "me.points_short": "{n} ball",
    "me.next_level": "Keyingi darajagacha {n} ball qoldi",
    "me.max_level": "Siz eng yuqori darajadasiz!",
    "me.rank": "O'rningiz: {rank}",
    "me.leaderboard_hint": "Eng yaxshi qayta ishlovchilar ro'yxati uchun botga /stats yuboring.",
    "me.points_note": "Ballarning pul qiymati yo'q.",

    "report.received": "✅ Rahmat! Xabaringiz qabul qilindi va ko'rib chiqiladi.",
    "report.invalid": "⚠️ Xabar to'liq emas. Barcha majburiy maydonlarni to'ldirib, qayta urinib ko'ring.",
    "report.point_form": "Qabul punkti haqida xabar berish",
    "report.price_form": "Narx haqida xabar berish",
    "report.use_command": "Xabar yuborish uchun botda /report buyrug'ini yuboring va u yerdagi tugmani bosing.",
    "report.name": "Nomi",
    "report.lat": "Kenglik",
    "report.lon": "Uzunlik",
    "report.materials": "Qabul qilinadigan materiallar",
    "report.phone": "Telefon",
    "report.hours": "Ish vaqti",
    "report.point": "Punkt",
    "report.material": "Material",
    "report.price": "Narx (so'm/kg)",
    "report.submit": "Yuborish",
    "report.required": "Majburiy maydonlarni to'ldiring",

    "stats.result": "📊 Sizning hissangiz\n\n♻️ Saralangan buyumlar: {items}\n📝 Tasdiqlangan xabarlar: {reports}\n⭐ Ballar: {points}\n🏅 Daraja: {level}",
    "stats.level": "Daraja",
    "stats.items": "Saralangan buyumlar",
    "stats.reports": "Tasdiqlangan xabarlar",
    "stats.points": "Ballar",
    "stats.leaderboard": "🏆 Eng yaxshi qayta ishlovchilar",

    "review.none_pending": "Ko'rib chiqishni kutayotgan xabarlar yo'q.",
    "review.approved": "✅ Tasdiqlandi",
    "review.rejected": "❌ Rad etildi",

    "impact.open_map_button": "🗺 Xaritani ochish",
    "cmd.review": "🛠 Ko'rib chiqishni kutayotgan xabarlar:",
    "cmd.stats": "📊 Sizning hissangiz",

    "level.beginner": "Boshlovchi",
    "level.recycler": "Qayta ishlovchi",
    "level.champion": "Chempion",
    "level.legend": "Afsona",

    "mat.PET_1": "PET Plastik #1",
    "mat.HDPE_2": "HDPE Plastik #2",
    "mat.PP_5": "PP Plastik #5",
    "mat.GLASS": "Shisha",
    "mat.PAPER": "Qog'oz",
    "mat.CARDBOARD": "Karton",
    "mat.ALUMINIUM": "Alyuminiy",
    "mat.STEEL": "Po'lat",
    "mat.BATTERIES": "Batareyalar",
    "mat.EWASTE": "Elektron chiqindi",
    "mat.TEXTILES": "To'qimachilik",
    "mat.ORGANIC": "Organik chiqindi",
    "mat.MIXED": "Aralash / Qayta ishlanmaydigan"
  },

  ru: {
    "tab.scan": "Скан",
    "tab.map": "Карта",
    "tab.prices": "Цены",
    "tab.me": "Я",

    "lang.title": "Язык",
    "lang.name.uz": "O'zbekcha",
    "lang.name.ru": "Русский",
    "lang.name.en": "English",

    "common.loading": "Загрузка...",
    "common.error": "Произошла ошибка. Попробуйте позже.",
    "common.optional": "необязательно",
    "common.none": "—",
    "common.attribution": "© OpenStreetMap contributors",

    "scan.title": "Сканирование отходов",
    "scan.text": "Камера внутри мини-приложения недоступна. Отправьте фото в чат с ботом.",
    "scan.step1": "Сделайте чёткое, хорошо освещённое фото предмета",
    "scan.step2": "Отправьте фото в этот чат",
    "scan.step3": "Получите материал, советы по подготовке и цену",
    "scan.button": "Вернуться в чат",

    "map.title": "Карта переработки",
    "map.choose_material": "Выберите материал",
    "map.all_materials": "Все материалы",
    "map.no_points": "Рядом нет пунктов приёма. Вы можете добавить пункт в OpenStreetMap.",
    "map.route": "Маршрут",
    "map.verified_on": "Проверено {date}",
    "map.no_location": "Местоположение недоступно. Показаны известные пункты без расстояний.",
    "map.open_osm": "Открыть в OpenStreetMap",
    "map.materials_unknown": "Принимаемые материалы неизвестны, сначала позвоните",
    "map.pick_city": "Выберите город или нажмите на карту",
    "map.city.tashkent": "Ташкент",
    "map.city.ohangaron": "Ахангаран",
    "map.city.samarkand": "Самарканд",
    "map.accepts": "Принимает",
    "map.phone": "Телефон",
    "map.hours": "Часы работы",
    "map.distance": "Расстояние",
    "map.loading_points": "Поиск пунктов...",
    "map.overpass_failed": "Живые данные карты не загрузились. Показаны только проверенные пункты.",

    "prices.title": "Цены на вторсырьё",
    "prices.col.material": "Материал",
    "prices.col.point": "Пункт",
    "prices.col.price": "Цена (сум/кг)",
    "prices.col.source": "Источник",
    "prices.col.date": "Дата",
    "prices.empty": "Проверенных цен пока нет. Станьте первым, кто сообщит цену!",
    "prices.report_link": "Сообщить цену",
    "prices.note": "Цены берутся только из проверенных записей, с указанием источника и даты.",
    "price.outdated": "возможно, устарело",
    "price.line": "💰 Лучшая цена: {price} сум/кг ({source}, {date})",
    "nearest.line": "📍 Ближайший пункт: {name}, {distance}",

    "me.title": "Мой вклад",
    "me.no_data": "Чтобы увидеть свою статистику, отправьте боту команду /stats.",
    "me.thresholds": "Уровни",
    "me.points_short": "{n} баллов",
    "me.next_level": "До следующего уровня: {n} баллов",
    "me.max_level": "У вас максимальный уровень!",
    "me.rank": "Ваше место: {rank}",
    "me.leaderboard_hint": "Чтобы увидеть лучших сортировщиков, отправьте боту /stats.",
    "me.points_note": "Баллы не имеют денежной стоимости.",

    "report.received": "✅ Спасибо! Ваше сообщение получено и будет проверено.",
    "report.invalid": "⚠️ Сообщение неполное. Заполните все обязательные поля и попробуйте снова.",
    "report.point_form": "Сообщить о пункте приёма",
    "report.price_form": "Сообщить о цене",
    "report.use_command": "Чтобы отправить сообщение, отправьте боту команду /report и нажмите кнопку там.",
    "report.name": "Название",
    "report.lat": "Широта",
    "report.lon": "Долгота",
    "report.materials": "Принимаемые материалы",
    "report.phone": "Телефон",
    "report.hours": "Часы работы",
    "report.point": "Пункт",
    "report.material": "Материал",
    "report.price": "Цена (сум/кг)",
    "report.submit": "Отправить",
    "report.required": "Заполните обязательные поля",

    "stats.result": "📊 Ваш вклад\n\n♻️ Отсортировано предметов: {items}\n📝 Одобренных отчётов: {reports}\n⭐ Баллы: {points}\n🏅 Уровень: {level}",
    "stats.level": "Уровень",
    "stats.items": "Отсортировано предметов",
    "stats.reports": "Одобренные отчёты",
    "stats.points": "Баллы",
    "stats.leaderboard": "🏆 Лучшие сортировщики",

    "review.none_pending": "Нет отчётов, ожидающих проверки.",
    "review.approved": "✅ Одобрено",
    "review.rejected": "❌ Отклонено",

    "impact.open_map_button": "🗺 Открыть карту",
    "cmd.review": "🛠 Отчёты, ожидающие проверки:",
    "cmd.stats": "📊 Ваш вклад",

    "level.beginner": "Новичок",
    "level.recycler": "Переработчик",
    "level.champion": "Чемпион",
    "level.legend": "Легенда",

    "mat.PET_1": "ПЭТ Пластик #1",
    "mat.HDPE_2": "ПЭВП Пластик #2",
    "mat.PP_5": "ПП Пластик #5",
    "mat.GLASS": "Стекло",
    "mat.PAPER": "Бумага",
    "mat.CARDBOARD": "Картон",
    "mat.ALUMINIUM": "Алюминий",
    "mat.STEEL": "Сталь",
    "mat.BATTERIES": "Батарейки",
    "mat.EWASTE": "Электронные отходы",
    "mat.TEXTILES": "Текстиль",
    "mat.ORGANIC": "Органические отходы",
    "mat.MIXED": "Смешанные / Не перерабатываемые"
  },

  en: {
    "tab.scan": "Scan",
    "tab.map": "Map",
    "tab.prices": "Prices",
    "tab.me": "Me",

    "lang.title": "Language",
    "lang.name.uz": "O'zbekcha",
    "lang.name.ru": "Русский",
    "lang.name.en": "English",

    "common.loading": "Loading...",
    "common.error": "Something went wrong. Please try again later.",
    "common.optional": "optional",
    "common.none": "—",
    "common.attribution": "© OpenStreetMap contributors",

    "scan.title": "Scan your waste",
    "scan.text": "The camera is not available inside a Mini App. Send the photo to the bot chat.",
    "scan.step1": "Take a clear, well-lit photo of one item",
    "scan.step2": "Send the photo in this chat",
    "scan.step3": "Get the material, preparation tips and the price",
    "scan.button": "Back to chat",

    "map.title": "Recycling map",
    "map.choose_material": "Choose a material",
    "map.all_materials": "All materials",
    "map.no_points": "No collection points found nearby. You can add one to OpenStreetMap.",
    "map.route": "Route",
    "map.verified_on": "Verified on {date}",
    "map.no_location": "Location is unavailable. Showing known points without distances.",
    "map.open_osm": "Open in OpenStreetMap",
    "map.materials_unknown": "Accepted materials unknown, call first",
    "map.pick_city": "Pick a city or tap the map",
    "map.city.tashkent": "Tashkent",
    "map.city.ohangaron": "Ohangaron",
    "map.city.samarkand": "Samarkand",
    "map.accepts": "Accepts",
    "map.phone": "Phone",
    "map.hours": "Opening hours",
    "map.distance": "Distance",
    "map.loading_points": "Looking for points...",
    "map.overpass_failed": "Live map data could not be loaded. Showing verified points only.",

    "prices.title": "Recycling prices",
    "prices.col.material": "Material",
    "prices.col.point": "Point",
    "prices.col.price": "Price (so'm/kg)",
    "prices.col.source": "Source",
    "prices.col.date": "Date",
    "prices.empty": "No verified prices yet. Be the first to report one!",
    "prices.report_link": "Report a price",
    "prices.note": "Prices come only from verified records, shown with their source and date.",
    "price.outdated": "may be outdated",
    "price.line": "💰 Best price: {price} so'm/kg ({source}, {date})",
    "nearest.line": "📍 Nearest point: {name}, {distance}",

    "me.title": "My impact",
    "me.no_data": "Send /stats to the bot to see your statistics.",
    "me.thresholds": "Levels",
    "me.points_short": "{n} points",
    "me.next_level": "{n} points to the next level",
    "me.max_level": "You are at the highest level!",
    "me.rank": "Your rank: {rank}",
    "me.leaderboard_hint": "Send /stats to the bot to see the top recyclers.",
    "me.points_note": "Points have no cash value.",

    "report.received": "✅ Thank you! Your report was received and will be reviewed.",
    "report.invalid": "⚠️ The report is incomplete. Please fill in all required fields and try again.",
    "report.point_form": "Report a collection point",
    "report.price_form": "Report a price",
    "report.use_command": "To send a report, send /report to the bot and tap the button there.",
    "report.name": "Name",
    "report.lat": "Latitude",
    "report.lon": "Longitude",
    "report.materials": "Accepted materials",
    "report.phone": "Phone",
    "report.hours": "Opening hours",
    "report.point": "Point",
    "report.material": "Material",
    "report.price": "Price (so'm/kg)",
    "report.submit": "Submit",
    "report.required": "Fill in the required fields",

    "stats.result": "📊 Your impact\n\n♻️ Items sorted: {items}\n📝 Approved reports: {reports}\n⭐ Points: {points}\n🏅 Level: {level}",
    "stats.level": "Level",
    "stats.items": "Items sorted",
    "stats.reports": "Approved reports",
    "stats.points": "Points",
    "stats.leaderboard": "🏆 Top recyclers",

    "review.none_pending": "No reports are waiting for review.",
    "review.approved": "✅ Approved",
    "review.rejected": "❌ Rejected",

    "impact.open_map_button": "🗺 Open Map",
    "cmd.review": "🛠 Pending reports for review:",
    "cmd.stats": "📊 Your impact",

    "level.beginner": "Beginner",
    "level.recycler": "Recycler",
    "level.champion": "Champion",
    "level.legend": "Legend",

    "mat.PET_1": "PET Plastic #1",
    "mat.HDPE_2": "HDPE Plastic #2",
    "mat.PP_5": "PP Plastic #5",
    "mat.GLASS": "Glass",
    "mat.PAPER": "Paper",
    "mat.CARDBOARD": "Cardboard",
    "mat.ALUMINIUM": "Aluminium",
    "mat.STEEL": "Steel",
    "mat.BATTERIES": "Batteries",
    "mat.EWASTE": "E-Waste",
    "mat.TEXTILES": "Textiles",
    "mat.ORGANIC": "Organic Waste",
    "mat.MIXED": "Mixed / Non-recyclable"
  }
};

var DEFAULT_LANG = "uz";
var LANG_STORAGE_KEY = "qayta_lang";
var SUPPORTED_LANGS = ["uz", "ru", "en"];

function _storage() {
  try {
    if (typeof localStorage !== "undefined") return localStorage;
  } catch (e) { /* storage blocked */ }
  return null;
}

function getLang() {
  var store = _storage();
  var lang = null;
  try { lang = store ? store.getItem(LANG_STORAGE_KEY) : null; } catch (e) { lang = null; }
  return SUPPORTED_LANGS.indexOf(lang) >= 0 ? lang : DEFAULT_LANG;
}

function setLang(lang) {
  var value = SUPPORTED_LANGS.indexOf(lang) >= 0 ? lang : DEFAULT_LANG;
  var store = _storage();
  try { if (store) store.setItem(LANG_STORAGE_KEY, value); } catch (e) { /* ignore */ }
  return value;
}

function t(key, params) {
  var lang = getLang();
  var str = STRINGS[lang][key];
  if (str === undefined) str = STRINGS[DEFAULT_LANG][key];
  if (str === undefined) str = key;
  if (params) {
    Object.keys(params).forEach(function (name) {
      str = str.split("{" + name + "}").join(String(params[name]));
    });
  }
  return str;
}

function applyI18n(root) {
  var scope = root || (typeof document !== "undefined" ? document : null);
  if (!scope) return;
  scope.querySelectorAll("[data-i18n]").forEach(function (el) {
    el.textContent = t(el.getAttribute("data-i18n"));
  });
  scope.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
    el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
  });
  scope.querySelectorAll("[data-i18n-title]").forEach(function (el) {
    el.setAttribute("title", t(el.getAttribute("data-i18n-title")));
  });
}

if (typeof window !== "undefined") {
  window.STRINGS = STRINGS;
  window.t = t;
  window.getLang = getLang;
  window.setLang = setLang;
  window.applyI18n = applyI18n;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    STRINGS: STRINGS, t: t, getLang: getLang, setLang: setLang, applyI18n: applyI18n,
    SUPPORTED_LANGS: SUPPORTED_LANGS, DEFAULT_LANG: DEFAULT_LANG, LANG_STORAGE_KEY: LANG_STORAGE_KEY
  };
}
