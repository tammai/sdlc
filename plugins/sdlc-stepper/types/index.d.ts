export type Phase = 'Define' | 'Build' | 'Review' | 'Ship'

export type Part = { id: string; title: string; status: string }

export type View = {
  /** The repo's folder under the session's, '' when the session started in it. */
  repo: string
  feature: string
  phase: Phase
  parts: Part[]
  /** The part in progress, else the next one not done. */
  current: Part | null
}

/** The step the session was last seen on, and the phase it belongs to. */
export type Step = { phase: Phase; name: string }

declare module 'claude-code' {
  interface PluginState {
    'sdlc-stepper': {
      view: Shaped<View | null>
      step: Shaped<Step | null>
    }
  }
}
