export type Persona = {
  id: number; name: string; description: string; system_prompt: string; greeting: string; avatar_emoji: string;
}
export type Provider = {
  id: number; name: string; kind: 'ollama' | 'nvidia_nim'; base_url: string; has_api_key: boolean; is_enabled: boolean;
}
export type ModelConfig = {
  id: number; provider_id: number; provider_name: string; provider_kind: string; display_name: string; model_id: string;
  temperature: number; max_tokens: number | null; top_p: number;
}
export type Message = {
  id: number; role: 'user' | 'assistant'; content: string; model_id?: string | null; provider_kind?: string | null;
  latency_ms?: number | null; created_at?: string;
}
export type Conversation = {
  id: number; title: string; persona_id: number; persona_name: string; persona_emoji: string; model_config_id: number;
  model_display_name: string; provider_kind: string; is_archived: boolean; messages: Message[]; updated_at: string;
}
export type Settings = {
  app_name: string; user_display_name: string; assistant_display_name: string; theme: string;
  active_persona_id: number; active_model_config_id: number;
}

export type Memory = {
  id: number; category: string; content: string; is_active: boolean; created_at: string; updated_at: string;
}
