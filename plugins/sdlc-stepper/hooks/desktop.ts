// The desktop band's drawing, as SVG markup. Pure functions, no `$`.
// Mods can't read the app's theme, so the drawing uses colors that read on a white and on a black ground alike: a
// green for what is done or under way and a mid gray for what is ahead. State is also told by shape (check, dot,
// ring). The words beside it take the app's theme keys.
import type { Phase } from '../types'
import { PHASES } from './sdlc'

export type IconState = 'done' | 'current' | 'blocked' | 'todo'

export const GREEN = '#2DA44E'
const GRAY = '#7C828C'

/** A status icon's drawing on a 24-unit grid, so it scales to any size: a check in a green disc when done, a white
 *  dot in a green disc when current (with a ring that spreads out from it: the one thing that pulses), an empty ring
 *  after. */
function iconBody(state: IconState): string {
  const c = "cx='12' cy='12'"
  if (state === 'done') {
    return `<circle ${c} r='10' fill='${GREEN}'/>` +
      `<path d='M7.2 12.4 l3.3 3.3 l6.3 -7' fill='none' stroke='#fff' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'/>`
  }
  if (state === 'current') {
    return `<circle ${c} r='8' fill='none' stroke='${GREEN}' stroke-width='1.6'>` +
      `<animate attributeName='r' values='8;11.5' dur='1.8s' repeatCount='indefinite'/>` +
      `<animate attributeName='stroke-opacity' values='0.6;0' dur='1.8s' repeatCount='indefinite'/></circle>` +
      `<circle ${c} r='8' fill='${GREEN}'/><circle ${c} r='3' fill='#fff'/>`
  }
  return `<circle ${c} r='8.5' fill='none' stroke='${GRAY}' stroke-opacity='0.7' stroke-width='2.2'/>`
}

// The mini stepper: the four stages as small icons joined by short 1px lines, one drawing, where a title would be.
// It is the whole stepper: where the session is now (phase, part, step) is words beside it.
export const MINI_H = 20
const MINI_ICON = 16
const MINI_LINE = 10 // the room between two icons: a 6px line with 2px of air at each end

export function phaseState(i: number, at: number): IconState {
  return i < at ? 'done' : i === at ? 'current' : 'todo'
}

export function phaseAlt(phase: Phase, state: IconState): string {
  return `${phase}: ${state === 'done' ? 'done' : state === 'current' ? 'in progress' : 'not started'}`
}

/** The mini stepper for a feature at `phase`, with its width and alt text. */
export function miniSvg(phase: Phase): { source: string; alt: string; width: number } {
  const at = PHASES.indexOf(phase)
  const width = PHASES.length * MINI_ICON + (PHASES.length - 1) * MINI_LINE
  const body: string[] = []
  const alts: string[] = []
  PHASES.forEach((p: Phase, i) => {
    const state = phaseState(i, at)
    const x = i * (MINI_ICON + MINI_LINE)
    body.push(`<svg x='${x}' y='${(MINI_H - MINI_ICON) / 2}' width='${MINI_ICON}' height='${MINI_ICON}' viewBox='0 0 24 24'>${iconBody(state)}</svg>`)
    if (i < PHASES.length - 1) {
      const done = i < at // the line is green once the work is past the stage before it
      body.push(`<rect data-line='${done ? 'done' : 'ahead'}' x='${x + MINI_ICON + 2}' y='${MINI_H / 2}' width='${MINI_LINE - 4}' height='1' fill='${done ? GREEN : GRAY}' fill-opacity='${done ? 1 : 0.45}'/>`)
    }
    alts.push(phaseAlt(p, state))
  })
  return {
    source: `<svg xmlns='http://www.w3.org/2000/svg' width='${width}' height='${MINI_H}' viewBox='0 0 ${width} ${MINI_H}'>${body.join('')}</svg>`,
    alt: alts.join(', '),
    width,
  }
}
