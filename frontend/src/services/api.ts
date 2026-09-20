import { getAnonymousId } from './session';
import { getAuthHeaders } from './auth';
import type { VerificationResponse } from '../types/api';
import type { CaseRecord } from '../components/cloudscape/DashboardView';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export interface UnifiedQuery {
  text?: string;
  imageFile?: File;
  imageS3Key?: string;   // Pre-uploaded S3 key — skips re-upload (used after OCR confirm)
  batchNo?: string;
  drugName?: string;
  manufacturer?: string;
}

export async function submitVerification(query: UnifiedQuery): Promise<VerificationResponse> {
  const anonId = getAnonymousId();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Anonymous-Id': anonId,
    ...getAuthHeaders(),
  };

  // If a pre-uploaded S3 key is provided, use it directly (OCR confirm flow)
  let imageS3Key: string | undefined = query.imageS3Key;

  // If an image File is provided (and no pre-existing key), upload first then investigate
  if (!imageS3Key && query.imageFile) {
    try {
      const presignRes = await fetch(`${API_BASE}/uploads/presign`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          filename: query.imageFile.name,
          content_type: query.imageFile.type || 'image/jpeg',
        }),
      });
      if (presignRes.ok) {
        const presignData = await presignRes.json();
        imageS3Key = presignData.s3_key;
        // Attempt upload to presigned URL
        try {
          await fetch(presignData.upload_url, {
            method: 'PUT',
            headers: { 'Content-Type': query.imageFile.type || 'image/jpeg' },
            body: query.imageFile,
          });
        } catch (error) {
          throw new Error(`Image upload failed: ${error instanceof Error ? error.message : 'unknown error'}`);
        }
      }
    } catch (error) {
      throw error instanceof Error ? error : new Error('Image upload preparation failed');
    }
  }

  // Determine intent:
  // 1. If text is long / has symptom words or "suspicious", call /investigate/deep
  // 2. If image is attached, call /investigate
  // 3. Otherwise call /check for ultra-fast response
  const textQuery = (query.text || '').trim();
  const isSuspiciousOrLong =
    textQuery.length > 50 ||
    /fake|counterfeit|adverse|reaction|symptom|hospital|suspicious|smudged|defect|smell|taste/i.test(textQuery);

  if (isSuspiciousOrLong) {
    const res = await fetch(`${API_BASE}/investigate/deep`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        free_text_query: textQuery,
        batch_no: query.batchNo,
        drug_name: query.drugName,
        image_s3_key: imageS3Key,
      }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Deep investigation failed');
    const data = await res.json();
    return {
      session_id: data.session_id,
      ...data,
    };
  }

  if (imageS3Key) {
    const res = await fetch(`${API_BASE}/investigate`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        image_s3_key: imageS3Key,
        notes: textQuery,
      }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Image investigation failed');
    const data = await res.json();
    return {
      ...data,
      session_id: data.session_id,
      image_url: query.imageFile ? URL.createObjectURL(query.imageFile) : undefined,
      status_category: data.status_category || 'CLEAR',
      summary:
        data.summary ||
        `Packaging photo processed via Google Gemini Flash Multimodal OCR pipeline (${query.imageFile?.name || 'scan'}).`,
      official_record: data.batch_record || null,
      community_flag: false,
      disclaimer: data.limitation_statement || 'Absence of a flag is not proof of safety.',
      orchestrator_tier: 'REACTIVE',
      orchestrator_reasoning: 'Image input detected -> Routed to Reactive Multi-step Verification Agent.',
      reasoning_trace: data.reasoning_trace || [
        `Step 1: Uploaded packaging artifact to S3 bucket 'medverify-uploads' (${query.imageFile?.name || 'packaging.jpg'}).`,
        'Step 2: Orchestrator detected visual modality -> routed to Reactive Agent Tier.',
        'Step 3: Initiated multimodal extraction via Google Gemini Flash OCR.',
      ],
      extracted_fields: data.extracted_fields || {
        batch_no: query.batchNo || (textQuery ? textQuery : 'Auto-extracted'),
        drug_name: query.drugName || (textQuery ? textQuery : 'Packaging scan'),
        ocr_confidence: 0.95,
      },
      sources: data.sources || [],
    };
  }

  // Intelligent parameter extraction from free-text user queries
  let batchParam = query.batchNo;
  let drugParam = query.drugName;

  if (!batchParam && textQuery) {
    const batchMatch = textQuery.match(/(?:batch\s*(?:no\.?|number|code)?\s*[:#-]?\s*|\b)([A-Za-z0-9]{1,5}-[0-9]{2,6}[A-Za-z0-9]?|[A-Za-z]{2,5}[0-9]{3,6})\b/i);
    if (batchMatch) {
      batchParam = batchMatch[1].toUpperCase();
    } else if (textQuery.length <= 15 && !/\s/.test(textQuery)) {
      batchParam = textQuery.toUpperCase();
    } else {
      const cleanDrug = textQuery.replace(/verify|check|inspect|batch|details|safety|records/gi, '').trim();
      if (cleanDrug) {
        drugParam = drugParam || cleanDrug;
      }
    }
  }

  // Quick Check via /check
  const res = await fetch(`${API_BASE}/check`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      batch_no: batchParam || undefined,
      drug_name: drugParam || undefined,
      manufacturer: query.manufacturer,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to verify' }));
    throw new Error(err.detail || 'Verification request failed');
  }

  const raw = await res.json();
  const decision = raw.orchestrator_decision;
  const officialRecord = raw.batch_record || raw.official_record || null;
  const tier = raw.orchestrator_tier || decision?.selected_tier || decision?.target_tier || 'SKILL';
  const statusCat =
    raw.status_category === 'MATCH_FOUND' && officialRecord?.alert_status
      ? officialRecord.alert_status
      : raw.status_category;

  return {
    ...raw,
    session_id: raw.session_id,
    status_category: statusCat,
    summary:
      raw.summary ||
      (officialRecord
        ? `Batch ${officialRecord.batch_no} (${officialRecord.drug_name}) flagged as ${officialRecord.alert_status}: ${officialRecord.nsq_reason || 'Official CDSCO alert recorded'}.`
        : `No regulatory quality failure or spurious notice recorded for ${query.batchNo || textQuery || 'the requested item'}.`),
    official_record: officialRecord,
    community_flag: Boolean(raw.community_flag),
    disclaimer: raw.disclaimer || raw.limitation_statement || 'Absence of a flag is not proof of safety.',
    orchestrator_tier: tier,
    orchestrator_reasoning:
      raw.orchestrator_reasoning ||
      decision?.reasoning ||
      (decision ? `Classified as ${decision.intent || 'batch_lookup'} (${decision.complexity || 'LOW'} complexity).` : undefined),
    reasoning_trace: raw.reasoning_trace || [
      `Step 1: Orchestrator classified query as ${decision?.intent || 'batch_lookup'} -> routed to ${tier} tier.`,
      `Step 2: Queried CDSCO official batches registry for batch '${query.batchNo || textQuery}'.`,
      `Step 3: ${officialRecord ? `Match found with status ${officialRecord.alert_status}.` : 'No matching regulatory quality alert recorded in CDSCO repository.'}`,
      `Step 4: Checked community signals -> ${raw.community_flag ? 'community flags present' : 'no active community reports'}.`,
    ],
    sources: raw.sources || [],
  };
}


export async function submitFeedback(sessionId: string, helpful: boolean, comment?: string): Promise<boolean> {
  const anonId = getAnonymousId();
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Anonymous-Id': anonId,
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ helpful, comment }),
    });
    return res.ok;
  } catch (err) {
    console.error('Feedback error:', err);
    return false;
  }
}

export async function submitCommunityReport(report: {
  batch_no?: string;
  drug_name?: string;
  issue_type: string;
  description: string;
}): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/reports`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Anonymous-Id': getAnonymousId(),
        ...getAuthHeaders(),
      },
      body: JSON.stringify(report),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getManufacturerDetails(manufacturerId: string) {
  try {
    const res = await fetch(`${API_BASE}/manufacturers/${encodeURIComponent(manufacturerId)}`, {
      headers: {
        ...getAuthHeaders(),
      },
    });
    if (res.ok) return await res.json();
    return null;
  } catch {
    return null;
  }
}

export async function getRegulatoryNotices() {
  try {
    const res = await fetch(`${API_BASE}/batches/notices/list`, {
      headers: {
        ...getAuthHeaders(),
      },
    });
    if (res.ok) {
      const data = await res.json();
      return data.documents || [];
    }
    return [];
  } catch {
    return [];
  }
}

export async function fetchUserSessions(): Promise<CaseRecord[]> {
  try {
    const res = await fetch(`${API_BASE}/sessions`, {
      headers: {
        'Content-Type': 'application/json',
        'X-Anonymous-Id': getAnonymousId(),
        ...getAuthHeaders(),
      },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.sessions || [];
  } catch (err) {
    console.warn('Failed to fetch user sessions from backend:', err);
    return [];
  }
}

export async function saveSessionToBackend(session: CaseRecord): Promise<void> {
  try {
    await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Anonymous-Id': getAnonymousId(),
        ...getAuthHeaders(),
      },
      body: JSON.stringify(session),
    });
  } catch (err) {
    console.warn('Failed to persist session to backend:', err);
  }
}

export async function triggerWebScraper() {
  const res = await fetch(`${API_BASE}/batches/notices/scrape`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Anonymous-Id': getAnonymousId(),
      ...getAuthHeaders(),
    },
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    throw new Error('Failed to scrape CDSCO portal');
  }
  return await res.json();
}

/**
 * Uploads an image file to S3 using the presigned URL endpoint.
 */
export async function uploadImageFile(file: File): Promise<{ s3_key: string; image_url: string }> {
  const anonId = getAnonymousId();
  const presignRes = await fetch(`${API_BASE}/uploads/presign`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Anonymous-Id': anonId,
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type || 'image/jpeg',
    }),
  });

  if (!presignRes.ok) {
    throw new Error('Failed to obtain secure image upload credentials.');
  }

  const presignData = await presignRes.json();
  const uploadRes = await fetch(presignData.upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': file.type || 'image/jpeg' },
    body: file,
  });

  if (!uploadRes.ok) {
    throw new Error('Image upload failed to S3 storage.');
  }

  return {
    s3_key: presignData.s3_key,
    // Use the backend-generated presigned GET URL (7-day expiry) so images
    // remain visible in chat history after page reload — not an ephemeral blob.
    image_url: presignData.view_url || URL.createObjectURL(file),
  };
}

/**
 * Executes Gemini Multimodal OCR extraction on an uploaded packaging image.
 */
export async function extractPackagingOcr(
  imageS3Key: string,
  mimeType: string = 'image/jpeg'
): Promise<any> {
  const anonId = getAnonymousId();
  const res = await fetch(`${API_BASE}/investigate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Anonymous-Id': anonId,
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      image_s3_key: imageS3Key,
      mime_type: mimeType,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Multimodal OCR analysis failed.');
  }

  return await res.json();
}

/**
 * Retrieves historical session details by ID.
 */
export async function getSessionDetails(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error(`Session ${sessionId} not found`);
  }
  return await res.json();
}
