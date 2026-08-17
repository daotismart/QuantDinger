export const CANDLE_COLOR_SCHEMES = {
  GREEN_UP: 'green_up',
  RED_UP: 'red_up'
}

export const CANDLE_COLOR_STORAGE_KEY = 'qd_candle_color_scheme'

const ALIASES = {
  red_up: 'red_up',
  redup: 'red_up',
  cn: 'red_up',
  china: 'red_up',
  asian: 'red_up',
  green_down: 'red_up',
  green_up: 'green_up',
  greenup: 'green_up',
  us: 'green_up',
  western: 'green_up',
  red_down: 'green_up'
}

export function normalizeCandleColorScheme (value) {
  const raw = String(value || '').trim().toLowerCase().replace(/[-\s]/g, '_')
  return ALIASES[raw] || ''
}

export function defaultCandleColorScheme () {
  try {
    const lang = String(navigator.language || '').toLowerCase()
    if (lang.startsWith('zh')) return CANDLE_COLOR_SCHEMES.RED_UP
  } catch (e) {}
  return CANDLE_COLOR_SCHEMES.GREEN_UP
}

export function readStoredCandleColorScheme () {
  try {
    return normalizeCandleColorScheme(window.localStorage.getItem(CANDLE_COLOR_STORAGE_KEY))
  } catch (e) {
    return ''
  }
}

export function writeStoredCandleColorScheme (scheme) {
  const normalized = normalizeCandleColorScheme(scheme) || defaultCandleColorScheme()
  try {
    window.localStorage.setItem(CANDLE_COLOR_STORAGE_KEY, normalized)
  } catch (e) {}
  return normalized
}

export function resolveCandleColorScheme (preferred) {
  return normalizeCandleColorScheme(preferred) || readStoredCandleColorScheme() || defaultCandleColorScheme()
}

export function candleBarColors (scheme, isDark) {
  const redUp = resolveCandleColorScheme(scheme) === CANDLE_COLOR_SCHEMES.RED_UP
  if (isDark) {
    return redUp
      ? { upColor: '#f6465d', downColor: '#0ecb81', noChangeColor: '#848e9c' }
      : { upColor: '#0ecb81', downColor: '#f6465d', noChangeColor: '#848e9c' }
  }
  return redUp
    ? { upColor: '#f5222d', downColor: '#13c2c2', noChangeColor: '#8c8c8c' }
    : { upColor: '#13c2c2', downColor: '#fa541c', noChangeColor: '#8c8c8c' }
}

export function klinechartsCandleBarStyles (scheme, isDark) {
  const colors = candleBarColors(scheme, isDark)
  return {
    ...colors,
    upBorderColor: colors.upColor,
    downBorderColor: colors.downColor,
    upWickColor: colors.upColor,
    downWickColor: colors.downColor
  }
}
