// The desktop band's drawings, as SVG markup. Pure functions, no `$`.
// Mods can't read the app's theme, so the icons use one neutral mid gray that reads on a white and on a black
// card alike, and tell their state by shape (check, pulsing dot, ring), never by hue. The card, the words and
// the lines around them take the app's theme keys.
import type { Part, Phase } from '../types'

export type IconState = 'done' | 'current' | 'blocked' | 'todo'

const GRAY = '#7C828C'

/** One status icon, drawn on a 24-unit grid so it scales from a phase's 20px to a part's 12px:
 *  a check in a filled disc when done, a pulsing dot when current, a dashed ring when blocked, an empty ring after. */
export function iconSvg(state: IconState): string {
  const c = "cx='12' cy='12'"
  let body: string
  if (state === 'done') {
    body = `<circle ${c} r='10' fill='${GRAY}'/>` +
      `<path d='M7.2 12.4 l3.3 3.3 l6.3 -7' fill='none' stroke='#fff' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'/>`
  } else if (state === 'current') {
    body = `<circle ${c} r='8' fill='none' stroke='${GRAY}' stroke-width='1.6'>` +
      `<animate attributeName='r' values='8;11.5' dur='1.8s' repeatCount='indefinite'/>` +
      `<animate attributeName='stroke-opacity' values='0.6;0' dur='1.8s' repeatCount='indefinite'/></circle>` +
      `<circle ${c} r='8' fill='${GRAY}'/><circle ${c} r='3' fill='#fff'/>`
  } else if (state === 'blocked') {
    body = `<circle ${c} r='8.5' fill='none' stroke='${GRAY}' stroke-width='2.2' stroke-dasharray='3 3'/>`
  } else {
    body = `<circle ${c} r='8.5' fill='none' stroke='${GRAY}' stroke-opacity='0.7' stroke-width='2.2'/>`
  }
  return `<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'>${body}</svg>`
}

export const PHASE_ICON = 20
export const PART_ICON = 12

export function phaseState(i: number, at: number): IconState {
  return i < at ? 'done' : i === at ? 'current' : 'todo'
}

export function partState(p: Part, current: Part | null): IconState {
  if (p.status.startsWith('done')) return 'done'
  if (current && p.id === current.id) return 'current'
  if (p.status.startsWith('blocked')) return 'blocked'
  return 'todo'
}

export function phaseAlt(phase: Phase, state: IconState): string {
  return `${phase}: ${state === 'done' ? 'done' : state === 'current' ? 'in progress' : 'not started'}`
}

export function partAlt(p: Part, state: IconState): string {
  return `${p.id}: ${state === 'done' ? 'done' : state === 'current' ? 'in progress' : state === 'blocked' ? 'blocked' : 'not started'}`
}
