// Core types for the Ankification app

export type CardType = 'basic' | 'cloze';
export type CardStatus = 'draft' | 'accepted' | 'rejected';

export interface BasicCardContent {
  type: 'basic';
  front: string;
  back: string;
}

export interface ClozeCardContent {
  type: 'cloze';
  text: string;
}

export type CardContent = BasicCardContent | ClozeCardContent;

export interface Card {
  id: string;
  type: CardType;
  content: CardContent;
  source: string;
  status: CardStatus;
  tags: string[];
  created_at: string;
  modified_at: string;
}

export interface Session {
  id: string;
  sources: string[];
  provider: string;
  card_types: string[];
  count_guidance: string;
  created_at: string;
  completed_at: string | null;
  card_count: number;
  accepted_count: number;
  rejected_count: number;
  pending_count: number;
}

export interface GenerateRequest {
  sources: string[];
  provider: string;
  card_types: CardType[];
  count_guidance: string;
  tags: string[];
  user_directives?: string;
}

export interface GenerateResponse {
  job_id: string;
  message: string;
  ws_url: string;
}

export interface GenerationProgress {
  type: 'progress' | 'complete' | 'error';
  job_id: string;
  status: 'queued' | 'fetching' | 'generating' | 'complete' | 'error';
  message?: string;
  progress?: number;
  total?: number;
  cards?: Card[];
  error?: string;
  session_id?: string;
}

export interface RefineRequest {
  card_id: string;
  feedback: string;
}

export interface Config {
  llm: {
    default_provider: string;
    openai: {
      api_key: string;
      model: string;
    };
    anthropic: {
      api_key: string;
      model: string;
    };
  };
  generation: {
    default_card_types: CardType[];
    default_count_guidance: string;
  };
  tags: {
    pools: string[];
  };
}
