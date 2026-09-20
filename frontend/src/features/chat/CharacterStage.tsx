import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { PersonaAvatar } from '../../components/PersonaAvatar'
import type { StreamBuffer } from '../../lib/streamBuffer'
import type { ApiError, Message } from '../../lib/types'
import { classifyReaction, listeningReaction, streamingReaction } from '../../lib/personaReactions'
import { REACTION_LABELS, type AvatarCharacter, type Reaction } from '../../lib/personaVisuals'

export type ReactionReplay = { conversationId: number; sequence: number; reaction: Reaction }

type Phase = 'idle' | 'listening' | 'thinking' | 'speaking' | 'finished' | 'replay' | 'error'
const PHASE_LABEL: Record<Phase, string> = {
  idle: 'Pronta para conversar',
  listening: 'Ouvindo você',
  thinking: 'Pensando na resposta',
  speaking: 'Respondendo agora',
  finished: 'Reação da última resposta',
  replay: 'Relembrando a reação',
  error: 'Houve um imprevisto',
}
const MIN_POSE_TIME_MS = 950

function completedReaction(message?: Message): Reaction {
  if (message?.status === 'failed') return 'ops_erro_leve'
  return message?.content ? classifyReaction(message.content) : 'escutando_atenta'
}

export function CharacterStage({ conversationId, name, character, emoji, buffer, streaming, pendingUserMessage, lastAssistantMessage, error, replay }: {
  conversationId: number
  name: string
  character: AvatarCharacter
  emoji: string
  buffer: StreamBuffer
  streaming: boolean
  pendingUserMessage: string | null
  lastAssistantMessage?: Message
  error: ApiError | null
  replay: ReactionReplay | null
}) {
  const text = useSyncExternalStore(buffer.subscribe, buffer.getSnapshot, buffer.getSnapshot)
  const [reaction, setReaction] = useState<Reaction>(() => completedReaction(lastAssistantMessage))
  const [phase, setPhase] = useState<Phase>(lastAssistantMessage ? 'finished' : 'idle')
  const reactionRef = useRef<Reaction>(reaction)
  const lastPoseAt = useRef(0)
  const queuedReaction = useRef<Reaction | null>(null)
  const poseTimer = useRef<number | null>(null)
  const waitingTimers = useRef<number[]>([])
  const idleTimer = useRef<number | null>(null)
  const wasStreaming = useRef(false)
  const firstTextSeen = useRef(false)
  const lastReplaySequence = useRef(0)

  const clearPoseTimer = useCallback(() => {
    if (poseTimer.current !== null) window.clearTimeout(poseTimer.current)
    poseTimer.current = null
    queuedReaction.current = null
  }, [])
  const clearWaitingTimers = useCallback(() => {
    waitingTimers.current.forEach(timer => window.clearTimeout(timer))
    waitingTimers.current = []
  }, [])
  const clearIdleTimer = useCallback(() => {
    if (idleTimer.current !== null) window.clearTimeout(idleTimer.current)
    idleTimer.current = null
  }, [])

  const showReaction = useCallback((next: Reaction, immediate = false) => {
    if (next === reactionRef.current) {
      clearPoseTimer()
      return
    }
    const wait = immediate ? 0 : Math.max(0, MIN_POSE_TIME_MS - (Date.now() - lastPoseAt.current))
    if (wait === 0) {
      clearPoseTimer()
      reactionRef.current = next
      lastPoseAt.current = Date.now()
      setReaction(next)
      return
    }
    queuedReaction.current = next
    if (poseTimer.current !== null) return
    poseTimer.current = window.setTimeout(() => {
      poseTimer.current = null
      const queued = queuedReaction.current
      queuedReaction.current = null
      if (queued && queued !== reactionRef.current) {
        reactionRef.current = queued
        lastPoseAt.current = Date.now()
        setReaction(queued)
      }
    }, wait)
  }, [clearPoseTimer])

  useEffect(() => {
    if (!streaming) return
    firstTextSeen.current = false
    clearIdleTimer()
    clearPoseTimer()
    clearWaitingTimers()
    setPhase('listening')
    showReaction(listeningReaction(pendingUserMessage), true)
    waitingTimers.current.push(window.setTimeout(() => {
      if (buffer.getSnapshot()) return
      setPhase('thinking')
      showReaction('analisando', true)
    }, 900))
    waitingTimers.current.push(window.setTimeout(() => {
      if (buffer.getSnapshot()) return
      showReaction('pensativa', true)
    }, 4400))
    return clearWaitingTimers
  }, [streaming, pendingUserMessage, buffer, clearIdleTimer, clearPoseTimer, clearWaitingTimers, showReaction])

  useEffect(() => {
    if (streaming) {
      wasStreaming.current = true
      return
    }
    if (!wasStreaming.current) return
    wasStreaming.current = false
    clearPoseTimer()
    clearWaitingTimers()
    setPhase('finished')
    showReaction(completedReaction(lastAssistantMessage), true)
  }, [streaming, clearPoseTimer, clearWaitingTimers, showReaction])

  useEffect(() => {
    if (!streaming || !text) return
    setPhase('speaking')
    const next = streamingReaction(text)
    if (!next) return
    if (!firstTextSeen.current) {
      firstTextSeen.current = true
      showReaction(next, true)
    } else {
      showReaction(next)
    }
  }, [text, streaming, showReaction])

  useEffect(() => {
    if (!replay || replay.conversationId !== conversationId || replay.sequence === lastReplaySequence.current || streaming) return
    lastReplaySequence.current = replay.sequence
    clearIdleTimer()
    setPhase('replay')
    showReaction(replay.reaction, true)
    idleTimer.current = window.setTimeout(() => {
      setPhase(lastAssistantMessage ? 'finished' : 'idle')
      showReaction(completedReaction(lastAssistantMessage), true)
      idleTimer.current = null
    }, 3200)
  }, [replay, conversationId, streaming, lastAssistantMessage, clearIdleTimer, showReaction])

  useEffect(() => {
    if (streaming) return
    if (error) {
      clearIdleTimer()
      setPhase('error')
      showReaction('ops_erro_leve', true)
    } else if (phase === 'error') {
      setPhase('idle')
      showReaction('escutando_atenta', true)
    }
  }, [error, streaming, clearIdleTimer, showReaction, phase])

  useEffect(() => () => {
    clearPoseTimer()
    clearWaitingTimers()
    clearIdleTimer()
  }, [clearPoseTimer, clearWaitingTimers, clearIdleTimer])

  return <aside className={`character-stage phase-${phase}`} aria-label={`Reações de ${name}`}>
    <div className="character-stage-kicker"><span aria-hidden="true" className="character-stage-signal"/> Reações ao vivo</div>
    <div className="character-stage-visual" aria-hidden="true">
      <div className="character-stage-halo"/>
      <div className="character-stage-ground"/>
      <div className="character-stage-float">
        <PersonaAvatar key={`${character}-${reaction}`} character={character} emoji={emoji} reaction={reaction} className="character-stage-portrait"/>
      </div>
    </div>
    <div className="character-stage-caption">
      <strong>{name}</strong>
      <span role="status">{PHASE_LABEL[phase]}</span>
      <small>{REACTION_LABELS[reaction]}</small>
    </div>
  </aside>
}
