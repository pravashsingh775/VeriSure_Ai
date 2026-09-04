export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
  brand_id?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type DecisionState =
  | 'LIKELY_GENUINE'
  | 'LOW_RISK'
  | 'MEDIUM_RISK'
  | 'HIGH_RISK'
  | 'CRITICAL_RISK'
  | 'INSUFFICIENT_EVIDENCE'
  | 'UNSUPPORTED_PRODUCT'
  | 'TAMPERED_OR_DAMAGED';

export interface RegionBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  label?: string;
  difference_score?: number;
  explanation?: string;
}

export interface EvidenceObject {
  id?: string;
  type: string;
  score: number | null;
  confidence: number;
  availability: boolean;
  quality: number;
  source: string;
  model_version: string;
  features: Record<string, any>;
  regions: RegionBox[];
  explanation: string;
  warnings: string[];
  created_at?: string;
}

export interface DecisionResult {
  state: DecisionState;
  risk_score: number;
  confidence: number;
  uncertainty: number;
  evidence_coverage: number;
  recommendation: string;
  reason_codes: string[];
  explanation_summary: string;
  contradictions: string[];
  suspicious_regions: RegionBox[];
}

export interface ScanImageDetail {
  id: string;
  view_type: string;
  image_path: string;
  crop_path?: string | null;
  heatmap_path?: string | null;
  quality_score?: number | null;
  quality_details?: Record<string, any> | null;
}

export interface ScanDetail {
  id: string;
  status: string;
  identified_product_name?: string | null;
  identified_variant_name?: string | null;
  identified_pack_size?: string | null;
  packaging_version_code?: string | null;
  images: ScanImageDetail[];
  evidences: EvidenceObject[];
  decision?: DecisionResult | null;
  fingerprint?: Record<string, any> | null;
  report_url?: string | null;
  suspicious_case_id?: string | null;
  created_at: string;
}

export interface ScanSummary {
  id: string;
  status: string;
  product_name?: string;
  variant_name?: string;
  risk_score?: number | null;
  decision_state?: DecisionState | null;
  confidence?: number | null;
  created_at: string;
}

export interface SuspiciousCase {
  id: string;
  scan_id: string;
  brand_id: string;
  case_number: string;
  status: string;
  priority: string;
  assigned_to?: string | null;
  notes?: string | null;
  reviews: Array<{
    id: string;
    reviewer_id: string;
    previous_status: string;
    new_status: string;
    comments?: string;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface ModelVersion {
  id: string;
  model_id: string;
  version_tag: string;
  status: string;
  artifact_path?: string;
  hyperparameters: Record<string, any>;
  evaluations: Array<{
    id: string;
    accuracy?: number;
    precision?: number;
    recall?: number;
    f1?: number;
    roc_auc?: number;
    confusion_matrix?: Record<string, any>;
    robustness_metrics?: Record<string, any>;
    evaluated_at?: string;
  }>;
  created_at: string;
}

export interface ModelEntity {
  id: string;
  name: string;
  task: string;
  architecture: string;
  description?: string;
  versions: ModelVersion[];
}

export interface AdminAnalytics {
  total_scans: number;
  total_cases: number;
  open_cases: number;
  verified_counterfeits: number;
  quality_pass_rate_percent: number;
  decision_distribution: Record<string, number>;
  common_anomaly_types: Record<string, number>;
}

export interface ReferenceImage {
  id: string;
  packaging_version_id: string;
  view_type: string;
  image_path: string;
  original_filename?: string | null;
  source_type: string;
  source_document?: string | null;
  trust_level: number;
  approval_status: string;
  verification_status: string;
  created_at: string;
  product_name?: string | null;
  variant_name?: string | null;
  pack_size?: string | null;
  version_code?: string | null;
}

export interface BrandAnalytics {
  brand_code: string;
  brand_name: string;
  total_scans: number;
  active_packaging_versions: number;
  counterfeit_risk_rate_percent: number;
  risk_distribution: Record<string, number>;
}


