/** Campos que descrevem a personalidade — o que varia entre personas. */
export type PersonaTraits = {
  personality: string; humor: string; tone: string; energy: string;
  objective: string; avoid: string; extra_instructions: string;
}
export type Persona = PersonaTraits & {
  id: number; name: string; description: string; greeting: string; avatar_emoji: string;
  /** Prompt final montado no servidor: regra global + campos + extras. */
  composed_prompt: string;
}
export type ProviderKind = 'ollama' | 'nvidia_nim'
export type Provider = {
  id: number; name: string; kind: ProviderKind; base_url: string; has_api_key: boolean; is_enabled: boolean;
}
export type ModelConfig = {
  id: number; provider_id: number; provider_name: string; provider_kind: string; display_name: string; model_id: string;
  temperature: number; max_tokens: number | null; top_p: number;
  /** 0 = janela desconhecida; sem orçamento o histórico não é truncado. */
  context_window: number;
}

/** "complete" | "failed" | "cancelled" — resposta interrompida deixa de sumir. */
export type MessageStatus = 'complete' | 'failed' | 'cancelled'

export type Message = {
  id: number; role: 'user' | 'assistant'; content: string; status: MessageStatus;
  error_code?: string | null; error_message?: string | null;
  model_id?: string | null; provider_kind?: string | null;
  latency_ms?: number | null; prompt_tokens?: number | null; completion_tokens?: number | null; created_at?: string;
}
export type Conversation = {
  id: number; title: string; persona_id: number; persona_name: string; persona_emoji: string; model_config_id: number;
  model_display_name: string; provider_kind: string; is_archived: boolean; messages: Message[]; updated_at: string;
}
export type Settings = {
  app_name: string; user_display_name: string; assistant_display_name: string; theme: string;
  active_persona_id: number; active_model_config_id: number;
  /** Regra que toda persona obedece, antes de qualquer traço de personalidade. */
  global_persona_rules: string;
}

export type MemoryScope = 'global' | 'persona' | 'conversation'
export type Memory = {
  id: number; category: string; content: string; is_active: boolean;
  scope: MemoryScope; persona_id: number | null; conversation_id: number | null;
  created_at: string; updated_at: string;
}

/**
 * Erro normalizado do backend. O `code` é estável e é o que a UI usa para
 * decidir a ação sugerida — antes tudo chegava como uma string crua.
 */
export type ApiError = {
  code: string
  message: string
  providerDetail?: string | null
}
