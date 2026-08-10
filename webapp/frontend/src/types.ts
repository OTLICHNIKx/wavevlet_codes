export type ExperimentStatus =
  | "queued" | "validating" | "running" | "completed"
  | "failed" | "cancelling" | "cancelled" | "interrupted";

export interface CodeConfig {
  name: string;
  family: "wavelet" | "bch" | "bch_derived";
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
  expected_min_distance?: number | null;
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

export interface Experiment {
  id: string;
  name: string;
  description: string;
  status: ExperimentStatus;
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
}
