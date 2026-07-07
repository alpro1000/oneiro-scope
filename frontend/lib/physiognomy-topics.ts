/**
 * Human-readable titles for KB topic keys returned by the archive
 * analyzer (`backend/services/physiognomy/knowledge_base/*.json`).
 * Presentation only — no interpretation lives here; unknown topics
 * fall back to a formatted version of the raw key rather than
 * crashing or hiding the reading.
 */
const TOPIC_LABEL: Record<string, {ru: string; en: string}> = {
  'five_elements.earth': {ru: 'Тип «Земля»', en: 'Type "Earth"'},
  'five_elements.water': {ru: 'Тип «Вода»', en: 'Type "Water"'},
  'five_elements.wood': {ru: 'Тип «Дерево»', en: 'Type "Wood"'},
  'five_elements.fire': {ru: 'Тип «Огонь»', en: 'Type "Fire"'},
  'five_elements.metal': {ru: 'Тип «Металл»', en: 'Type "Metal"'},
  'three_courts.upper': {ru: 'Верхний двор', en: 'Upper court'},
  'three_courts.middle': {ru: 'Средний двор', en: 'Middle court'},
  'three_courts.lower': {ru: 'Нижний двор', en: 'Lower court'},
  'lavater_zones.upper': {ru: 'Верхний этаж (Лафатер)', en: 'Upper storey (Lavater)'},
  'lavater_zones.middle': {ru: 'Средний этаж (Лафатер)', en: 'Middle storey (Lavater)'},
  'lavater_zones.lower': {ru: 'Нижний этаж (Лафатер)', en: 'Lower storey (Lavater)'},
  'corman.dilated': {ru: 'Дилатированный тип', en: 'Dilated type'},
  'corman.retracted': {ru: 'Ретрактированный тип', en: 'Retracted type'},
  'corman.mixed_guarded': {ru: 'Смешанный охранный тип', en: 'Mixed guarded type'},
  'kretschmer.pyknic': {ru: 'Пикнический тип', en: 'Pyknic type'},
  'kretschmer.athletic': {ru: 'Атлетический тип', en: 'Athletic type'},
  'kretschmer.asthenic': {ru: 'Астенический тип', en: 'Asthenic type'},
  'fwhr.high': {ru: 'Высокий fWHR', en: 'High fWHR'},
  'fwhr.low': {ru: 'Низкий fWHR', en: 'Low fWHR'},
  'features.eyes_wide_set': {ru: 'Широко расставленные глаза', en: 'Wide-set eyes'},
  'features.eyes_close_set': {ru: 'Близко посаженные глаза', en: 'Close-set eyes'},
  'features.eyes_large': {ru: 'Крупные глаза', en: 'Large eyes'},
  'features.eyes_small': {ru: 'Некрупные глаза', en: 'Smaller eyes'},
  'features.eyelid_heavy': {ru: 'Тяжёлое верхнее веко', en: 'Heavy upper eyelid'},
  'features.gaze_steady': {ru: 'Устойчивый взгляд', en: 'Steady gaze'},
  'features.brows_thick': {ru: 'Густые брови', en: 'Thick brows'},
  'features.brows_thin': {ru: 'Тонкие брови', en: 'Thin brows'},
  'features.nose_fleshy': {ru: 'Мясистый нос', en: 'Fleshy nose'},
  'features.nose_narrow': {ru: 'Узкий нос', en: 'Narrow nose'},
  'features.mouth_full': {ru: 'Полные губы', en: 'Full lips'},
  'features.mouth_thin': {ru: 'Тонкие губы', en: 'Thin lips'},
  'features.jaw_wide': {ru: 'Широкая челюсть', en: 'Wide jaw'},
  'features.jaw_soft': {ru: 'Мягкая линия челюсти', en: 'Soft jawline'},
  'features.cheeks_full': {ru: 'Полные щёки', en: 'Full cheeks'},
  'features.cheekbones_high': {ru: 'Выраженные скулы', en: 'Pronounced cheekbones'},
  'features.forehead_high': {ru: 'Высокий лоб', en: 'High forehead'},
  'features.forehead_compact': {ru: 'Компактный лоб', en: 'Compact forehead'},
  'features.ears_large': {ru: 'Крупные уши', en: 'Large ears'},
  'features.chin_strong': {ru: 'Крепкий подбородок', en: 'Strong chin'},
};

export function topicTitle(topic: string, locale: string): string {
  const entry = TOPIC_LABEL[topic];
  if (entry) return locale === 'en' ? entry.en : entry.ru;
  // Unknown key: format rather than hide (e.g. "features.new_trait" -> "New trait")
  const tail = topic.split('.').pop() || topic;
  const words = tail.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}
