export type ExperimentStatus =
  | "queued" | "validating" | "running" | "completed"
  | "failed" | "cancelling" | "cancelled" | "interrupted";

export interface CodeConfig {
  name: string;
  family: "wavelet" | "bch" | "bch_derived" | "goppa_derived" | "reed_solomon_binary";
  n: number;
  k: number;
  h?: number[] | null;
  g?: number[] | null;
  a?: number;
  b?: number;
  shift?: number;
  bch_m?: number | null;
  bch_designed_distance?: number | null;
  bch_primitive_polynomial?: number | null;
  bch_first_root?: number;
  bch_shortening_count?: number | null;
  bch_puncture_count?: number | null;
  bch_puncture_coordinates?: number[] | null;
  goppa_m?: number | null;
  goppa_degree?: number | null;
  goppa_support_size?: number | null;
  goppa_seed?: number;
  goppa_primitive_polynomial?: number | null;
  reed_solomon_m?: number | null;
  reed_solomon_symbol_n?: number | null;
  reed_solomon_symbol_k?: number | null;
  reed_solomon_primitive_polynomial?: number | null;
  reed_solomon_evaluation_points?: number[] | null;
  reed_solomon_column_multipliers?: number[] | null;
  expected_min_distance?: number | null;
  minimum_distance_exact?: number | null;
  minimum_distance_lower_bound?: number | null;
  minimum_distance_upper_bound?: number | null;
  distance_evidence?: string;
  verified_error_correction_radius?: number | null;
  syndrome_max_error_weight?: number | null;
  chase_inner_decoder_max_error_weight?: number | null;
  chase_unreliable_positions_count?: number | null;
}

export interface ResearchConfig {
  message_count: number;
  message_seed: number;
  noise_seed: number;
  ebn0_db_values: number[];
  codes: CodeConfig[];
  decoders: {
    run_syndrome: boolean;
    run_hard_mld: boolean;
    run_soft_mld: boolean;
    run_chase: boolean;
    syndrome_max_error_weight: number;
    chase_inner_decoder_max_error_weight: number;
    chase_unreliable_positions_count: number;
    max_k_for_mld: number;
  };
  results_dir: string;
}

export type ExperimentSource = "local" | "imported_csv" | "imported_package";

export interface Experiment {
  id: string;
  name: string;
  description: string;
  status: ExperimentStatus;
  source: ExperimentSource;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  results_dir: string;
  exit_code: number | null;
  progress_completed: number;
  progress_total: number;
  progress: Record<string, unknown>;
  error_message: string;
  config: ResearchConfig;
  runtime_config_available: boolean;
  log_available: boolean;
}

export interface CustomPreset {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  schema_version: number;
  config: ResearchConfig;
}

export interface ExperimentPreview {
  valid: boolean;
  errors: string[];
  warnings: string[];
  summary?: {
    message_count: number;
    ebn0_db_values: number[];
    code_count: number;
    family_count: number;
    families: string[];
    message_seed: number;
    noise_seed: number;
  };
  common_random_numbers: {
    enabled: boolean;
    same_information_messages: boolean;
    same_base_noise: boolean;
    scope: string;
  };
  groups: Array<{
    key: string;
    n: number;
    rate_matched: boolean;
    decoder_matched: boolean;
    codes: Array<{
      name: string;
      family: string;
      n: number;
      k: number;
      rate: number;
      syndrome_t: number;
      chase_inner_t: number;
      chase_p: number;
      guaranteed_radius: number | null;
      hard_mld: { status: string; reason: string | null };
      soft_mld: { status: string; reason: string | null };
    }>;
  }>;
  workload: Record<string, number | string>;
}
