export type AgentTier = 'SKILL' | 'REACTIVE' | 'DEEP';

export type StatusCategory = 'CLEAR' | 'NSQ' | 'SPURIOUS' | 'COMMUNITY_FLAGGED' | 'NO_MATCH' | 'INFO_NEEDED';

export interface TodoItem {
  content: string;
  status: 'pending' | 'in_progress' | 'completed' | string;
}

export interface OfficialRecord {
  batch_no: string;
  drug_name?: string;
  manufacturer_name?: string;
  alert_status?: 'NONE' | 'NSQ' | 'SPURIOUS';
  nsq_reason?: string | null;
  source_month?: string;
  source_document_s3_key?: string;
  source_document_pdf_url?: string;
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

/** A single attributed data source — either a DynamoDB batch record (DB) or a Bedrock KB advisory chunk (KB). */
export interface SourceChunk {
  type: 'DB' | 'KB';
  label: string;               // e.g. "CDSCO DynamoDB · Apr 2025 — NSQ Record"
  reference?: string;          // batch_no (DB) or S3 URI (KB)
  content_preview?: string;    // summary line or first 150 chars of KB text
  doc_url?: string;            // clickable CDSCO PDF URL
  score?: number;              // relevance score (KB only)
}

export interface VerificationResponse {
  session_id: string;
  status_category: StatusCategory;
  summary?: string;
  explanation?: string;
  todos?: TodoItem[];
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
  sources?: SourceChunk[];     // Attributed data sources (DB records + KB advisory chunks)
  extracted_fields?: {
    drug_name?: string;
    batch_no?: string;
    manufacturer?: string;
    expiry_date?: string;
    mfg_date?: string;
    ocr_confidence?: number;
    symptoms_reported?: string;
  };
  image_url?: string;
  input_type?: 'TEXT' | 'IMAGE';
}

export interface PresignUploadResponse {
  upload_url: string;
  s3_key: string;
}
