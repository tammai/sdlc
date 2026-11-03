// The desktop band's drawings, as SVG markup. Pure functions, no `$`.
// Mods can't read the app's theme, so every color here reads on a light and a dark background alike: saturated
// accents and a mid gray, never black or white text. The card around them takes the app's theme keys.
import type { Part, Phase } from '../types'
import { PHASES } from './sdlc'

const GREEN = '#2FA36B'
const ACCENT = '#D97757'
const GRAY = '#8B919A'
const FONT = "font-family='-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif'"

export const STEPPER_WIDTH = 640
const HEIGHT = 58
const CY = 20
const R = 11

function x(i: number): number {
  return 40 + (i * (STEPPER_WIDTH - 80)) / (PHASES.length - 1)
}

/** Define → Build → Review → Ship: checks for done phases, a pulsing dot for the current one, outlines after. */
export function phasesSvg(phase: Phase): string {
  const at = PHASES.indexOf(phase)
  const lines = PHASES.slice(0, -1).map((_, i) => {
    const from = x(i) + R + 4
    const to = x(i + 1) - R - 4
    const done = i < at
    const color = done ? GREEN : i === at ? ACCENT : GRAY
    const style = done ? '' : i === at ? " stroke-opacity='0.55'" : " stroke-opacity='0.4' stroke-dasharray='2 5'"
    return `<line x1='${from}' y1='${CY}' x2='${to}' y2='${CY}' stroke='${color}' stroke-width='2.5' stroke-linecap='round'${style}/>`
  })
  const nodes = PHASES.map((p, i) => {
    const cx = x(i)
    const label = `<text x='${cx}' y='${HEIGHT - 6}' text-anchor='middle' font-size='12.5' ${FONT}`
    if (i < at) {
      return `<circle cx='${cx}' cy='${CY}' r='${R}' fill='${GREEN}'/>` +
        `<path d='M${cx - 4.5} ${CY + 0.5} l3 3 l6 -6.5' fill='none' stroke='#fff' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/>` +
        `${label} fill='${GREEN}' font-weight='500'>${p}</text>`
    }
    if (i === at) {
      return `<circle cx='${cx}' cy='${CY}' r='${R}' fill='none' stroke='${ACCENT}' stroke-width='2'>` +
        `<animate attributeName='r' values='${R};${R + 7}' dur='1.8s' repeatCount='indefinite'/>` +
        `<animate attributeName='stroke-opacity' values='0.6;0' dur='1.8s' repeatCount='indefinite'/></circle>` +
        `<circle cx='${cx}' cy='${CY}' r='${R}' fill='${ACCENT}'/>` +
        `<circle cx='${cx}' cy='${CY}' r='3.8' fill='#fff'/>` +
        `${label} fill='${ACCENT}' font-weight='700'>${p}</text>`
    }
    return `<circle cx='${cx}' cy='${CY}' r='${R - 1}' fill='none' stroke='${GRAY}' stroke-opacity='0.6' stroke-width='1.8'/>` +
      `${label} fill='${GRAY}' font-weight='500'>${p}</text>`
  })
  return `<svg xmlns='http://www.w3.org/2000/svg' width='${STEPPER_WIDTH}' height='${HEIGHT}' viewBox='0 0 ${STEPPER_WIDTH} ${HEIGHT}'>` +
    lines.join('') + nodes.join('') + '</svg>'
}

export function phasesAlt(phase: Phase): string {
  const at = PHASES.indexOf(phase)
  const done = PHASES.slice(0, at)
  return `Phase ${at + 1} of ${PHASES.length}: ${phase}` + (done.length ? `; done: ${done.join(', ')}` : '')
}

export const PARTS_WIDTH = 180
const SEG_H = 8
const GAP = 4

/** One rounded segment per part: done green, the current one accent (gently breathing), the rest faint gray. */
export function partsSvg(parts: Part[], current: Part | null): string {
  const n = Math.max(parts.length, 1)
  const w = (PARTS_WIDTH - GAP * (n - 1)) / n
  const segs = parts.map((p, i) => {
    const at = `x='${(i * (w + GAP)).toFixed(2)}' y='0' width='${w.toFixed(2)}' height='${SEG_H}' rx='${SEG_H / 2}'`
    if (p.status.startsWith('done')) return `<rect ${at} fill='${GREEN}'/>`
    if (current && p.id === current.id) {
      return `<rect ${at} fill='${ACCENT}'><animate attributeName='fill-opacity' values='1;0.55;1' dur='2.4s' repeatCount='indefinite'/></rect>`
    }
    if (p.status.startsWith('blocked')) return `<rect ${at} fill='none' stroke='${ACCENT}' stroke-opacity='0.7' stroke-dasharray='2 2'/>`
    return `<rect ${at} fill='${GRAY}' fill-opacity='0.3'/>`
  })
  return `<svg xmlns='http://www.w3.org/2000/svg' width='${PARTS_WIDTH}' height='${SEG_H}' viewBox='0 0 ${PARTS_WIDTH} ${SEG_H}'>` +
    segs.join('') + '</svg>'
}

export function partsAlt(parts: Part[]): string {
  const done = parts.filter(p => p.status.startsWith('done')).length
  return `${done} of ${parts.length} parts done`
}
