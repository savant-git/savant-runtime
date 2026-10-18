import type {ChatAttachment} from "./attachments"
export type MessageStatus =
  | "sending"
  | "sent"
  | "failed"
  | "received";


export type Message = {
  id: string;

  role:
    | "user"
    | "assistant"
    | "system";

  content: string;
  trace?: string;
  contextProjection?: { included: number; omitted: number };
  timestamp: number;
  status?: MessageStatus;
  attachments?: ChatAttachment[];
};


export type ChatMode =
  | "standard"
  | "develop"
  | "inspect"
  | "study"
  | "minimum";


export type ResponsePayload = {
  ok?: boolean;
  answer?: string;
  response?: unknown;
  output_text?: string;
  output?: unknown;
  error?: string;
  error_code?: string;
  diagnostic?: string;
  retryable?: boolean;
  trace?: string;
};
