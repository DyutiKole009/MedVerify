export type AgentTier = 'SKILL' | 'REACTIVE' | 'DEEP';

export type StatusCategory = 'CLEAR' | 'NSQ' | 'SPURIOUS' | 'COMMUNITY_FLAGGED' | 'NO_MATCH';

export interface OfficialRecord {
  batch_no: string;
  drug_name?: string;
  manufacturer_name?: string;
  alert_status?: 'NONE' | 'NSQ' | 'SPURIOUS';
  nsq_reason?: string | null;
  source_month?: string;
  source_document_s3_key?: string;
  mfg_date?: string;
  expiry_date?: string;
}

export interface CommunityReport {
  report_id: string;
  batch_no?: string;
  drug_name?: string;
  issue_type?: string;
  description?: string;
  created_at?: string;
  status?: string;
  verified?: boolean;
}

export interface ManufacturerProfile {
  PK?: string;
  manufacturer_name: string;
  total_flags?: number;
  spurious_count?: number;
  last_flagged_date?: string;
}

export interface VerificationResponse {
  session_id: string;
  status_category: StatusCategory;
  summary?: string;
  official_record?: OfficialRecord | null;
  community_flag: boolean;
  community_report_count?: number;
  community_reports?: CommunityReport[];
  manufacturer_record?: ManufacturerProfile | null;
  recent_manufacturer_batches?: OfficialRecord[];
  disclaimer: string;
  orchestrator_tier: AgentTier;
  orchestrator_reasoning?: string;
  reasoning_trace?: string[];
  citations?: Array<{ title?: string; source_url: string; text?: string }>;
  extracted_fields?: {
    drug_name?: string;
    batch_no?: string;
    manufacturer?: string;
    expiry_date?: string;
    mfg_date?: string;
    ocr_confidence?: number;
  };
  image_url?: string;
  input_type?: 'TEXT' | 'IMAGE';
}

export interface PresignUploadResponse {
  upload_url: string;
  s3_key: string;
}
