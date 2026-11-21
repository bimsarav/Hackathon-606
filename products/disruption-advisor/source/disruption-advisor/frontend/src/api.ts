// API client. Types mirror the backend (app/schemas.py, app/engine/scenarios.py); contract at /api/openapi.json.

/** RFC 9457 problem details, as returned by the backend for every error. */
export interface Problem {
  title: string;
  status: number;
  detail?: string;
  errors?: { loc: (string | number)[]; msg: string }[];
}

export class ApiError extends Error {
  readonly problem: Problem;

  constructor(problem: Problem) {
    super(problem.detail ?? problem.title);
    this.problem = problem;
  }
}

export type Role = "OCC" | "PCU";
export interface Session {
  token: string;
  username: string;
  role: Role;
  expires_at: string;
}

export type WeightKey = "loyalty" | "frequency" | "fare_value" | "ancillaries" | "journey" | "booking";
export type Weights = Record<WeightKey, number>;
export const WEIGHT_KEYS: WeightKey[] = ["loyalty", "frequency", "fare_value", "ancillaries", "journey", "booking"];

export interface Meta {
  user: { username: string; role: Role };
  now_utc: string;
  horizon_days: number;
  /** Minimum ground time between two flights of one aircraft (optional for older APIs). */
  min_turn_minutes?: { default: number; by_station: Record<string, number> };
  ai_enabled: boolean;
  ai_model: string;
  default_weights: Weights;
  weight_labels: Record<WeightKey, string>;
  ingest: { counts?: Record<string, number>; quality?: Record<string, unknown>; window?: Record<string, string> };
}

export interface FlightRow {
  flight_id: string;
  flight_number: string;
  airline: string;
  tail: string;
  origin: string;
  destination: string;
  std: string;
  sta: string;
  capacity: number;
  booked_seats: number;
  booked_pax: number;
  aircraft_model: string;
  capacity_source: string;
}

export interface DelayPreset {
  flight_id: string;
  flight_number: string;
  origin: string;
  destination: string;
  std: string;
  tail: string;
  is_demo: boolean;
  turn_minutes: number;
  connecting_pax: number;
}

export interface CancelPreset {
  flight_id: string;
  flight_number: string;
  origin: string;
  destination: string;
  std: string;
  tail: string;
  booked_seats: number;
  free_seats: number;
  care_pax: number;
}

export interface OptionLeg {
  flight_id: string;
  flight_number: string;
  origin: string;
  destination: string;
  std: string;
  new_std: string;
  new_sta: string;
  delay_minutes: number;
  operated_by: string;
  scheduled_tail: string;
  booked_pax: number;
}

export interface RecoveryOption {
  key: string;
  label: string;
  total_delay_minutes: number;
  legs_delayed: number;
  delayed_passengers: number;
  misconnects: number;
  connections_checked: number;
  eu261_compensation_eur: number;
  cost_aed: number;
  cost_breakdown: Record<string, number>;
  legs: OptionLeg[];
  // Phase 3 (ADR 0011); optional so scenarios saved before phase 3 still render.
  kind?: OptionKind;
  cancelled_flights?: CancelledFlight[];
  cancelled_passengers?: number;
  passengers_rebooked?: number;
  passengers_without_seat?: number;
  passenger_delay_minutes?: number;
  picked_by?: StrategyKey[];
}

export type OptionKind = "absorb" | "swap" | "cancel" | "consolidate";
export type StrategyKey = "lowest_cost" | "protect_passengers" | "least_delay";
export const STRATEGY_KEYS: StrategyKey[] = ["lowest_cost", "protect_passengers", "least_delay"];
export const STRATEGY_LABEL: Record<StrategyKey, string> = {
  lowest_cost: "Lowest cost",
  protect_passengers: "Protect passengers",
  least_delay: "Least delay",
};

export interface CancelledFlight {
  flight_id: string;
  flight_number: string;
  origin: string;
  destination: string;
  std: string;
  booked_pax: number;
}

export interface StrategyPick {
  key: StrategyKey;
  label: string;
  pick: string;
}

/** The agent's recommendation as attached to the scenario it produced (ADR 0010). */
export interface AgentNote {
  run_id: string;
  source: string;
  option_key: string;
  strategy: StrategyKey;
  reasons: string[];
  risks: string[];
  checks: string[];
}

export interface PassengerRow {
  rank: number;
  pnr: string;
  customer_key: string;
  name: string;
  pax_type: string;
  route: string;
  flight_id: string;
  tier: number;
  tier_reason: string;
  score: number;
  contributions: Record<WeightKey, number>;
  non_revenue: boolean;
  reason: string;
  loyalty_tier: string | null;
  /** Phase 3 loyalty (airline loyalty sample): optional for scenarios saved before it. */
  loyalty_priority?: string | null;
  loyalty_effective_tier?: string | null;
  loyalty_effective_priority?: string | null;
  loyalty_via_family?: boolean;
  loyalty_points?: number | null;
  family_account?: boolean;
  family_head?: boolean;
  frequency: string | null;
  fare: number;
  fare_family: string | null;
  ancillaries: number;
  ssr: string | null;
  ssr_source: string | null;
  pnr_size: number;
  infants: number;
  children: number;
  assigned_flight: string | null;
  assigned_flight_id: string | null;
  new_departure: string | null;
  arrival_delay_minutes: number | null;
  onward_ok: boolean | null;
  split: boolean;
  assignment_reason: string;
  missed_inbound_flight?: string | null;
  care?: {
    summary: string;
    wait_minutes: number | null;
    meals: number;
    hotel: boolean;
    transport: boolean;
    refund_option: boolean;
    flags: string[];
    cost_aed: number;
  };
  message: string;
  /** Delay scenarios (phase 3): why the passenger needs a new flight. */
  group?: "missed_connection" | "cancelled";
}

export interface Alternative {
  flight_id: string;
  flight_number: string;
  std: string;
  sta: string;
  available_seats: number;
  capacity_source: string;
  assigned: number;
}

export interface Rebooking {
  alternatives: Alternative[];
  protected: number;
  unprotected: number;
  groups_split: number;
  care_cost_aed?: number;
  hotel_rooms?: number;
}

interface ResultBase {
  flight: FlightRow;
  explanation: { text: string; source: string };
  passengers: PassengerRow[];
  rebooking: Rebooking | null;
  tier_counts?: Record<string, number>;
  assumptions: string[];
}

export interface DelayResult extends ResultBase {
  type: "DELAY";
  delay_minutes: number;
  options: RecoveryOption[];
  recommended_key: string;
  selected_key?: string;
  strategy?: StrategyKey;
  strategies?: StrategyPick[];
  agent?: AgentNote;
  misconnections: { pnr: string; customer_key: string; outbound_flight_number: string; final_destination: string;
    planned_minutes: number; new_minutes: number | null; mct_minutes: number }[];
}

export interface CancelResult extends ResultBase {
  type: "CANCEL";
  cost_aed: Record<string, number>;
  cost_total_aed: number;
  eu261_per_passenger_eur: number;
  onward_connections: number;
  solver_status: string;
  aircraft_follow_on: FlightRow | null;
}

export interface Scenario {
  id: string;
  kind: "DELAY" | "CANCEL";
  flight_id: string;
  delay_minutes: number | null;
  weights: Weights;
  result: DelayResult | CancelResult;
  created_by: string;
  created_at: string;
}

export interface ScenarioSummary {
  id: string;
  kind: "DELAY" | "CANCEL";
  flight_id: string;
  delay_minutes: number | null;
  created_by: string;
  created_at: string;
}

export interface Decision {
  id: number;
  target: string;
  action: "APPROVE" | "REJECT";
  comment: string;
  decided_by: string;
  decided_at: string;
}

// --- Phase 2: delay risk (app/risk.py, app/ml/delay_risk.py) ---
export interface RiskReason {
  feature: string;
  text: string;
  contribution: number;
}

export interface RiskFlight {
  flight_id: string;
  flight_number: string;
  origin: string;
  destination: string;
  std: string;
  sta: string;
  tail: string | null;
  aircraft_model: string | null;
  p_15: number;
  p_30: number;
  p_60: number;
  p_120: number;
  planning_delay_minutes: number | null;
  risk_band: "low" | "medium" | "high";
  reasons: RiskReason[];
  connecting_pax: number;
  expected_misconnects: number;
}

export interface Watchlist {
  from_utc: string;
  days: number;
  band: string;
  totals: { flights: number; high: number; medium: number; expected_misconnects: number | null };
  flights: RiskFlight[];
}

export interface ConnectionRisk {
  pnr: string;
  passenger_id: string | null;
  outbound_flight_id: string;
  outbound_flight_number: string;
  hub: string;
  final_destination: string;
  connection_minutes: number;
  mct_minutes: number;
  default_mct: boolean;
  slack_minutes: number;
  misconnect_risk: number;
}

export interface CascadeRow {
  date: string;
  tail: string;
  prev_flight: string;
  prev_arrival_delay: number;
  flight: string;
  route: string;
  std: string;
  formula_etd: string;
  actual_atd: string;
  formula_ko: number;
  actual_ko: number;
  delta: number;
}

export interface CascadeCheck {
  formula: string;
  definition: string;
  from: string | null;
  to: string | null;
  kpis: {
    pairs: number;
    mean_delta: number | null;
    within_15: number;
    within_15_share: number | null;
    within_30: number;
    within_30_share: number | null;
    underestimates: number;
    overestimates: number;
  };
  histogram: { label: string; count: number }[];
  excluded: CascadeRow[];
  excluded_rule: string;
  rows_total: number;
  rows: CascadeRow[];
}

export interface RewardRow {
  pnr: string;
  customer_key: string;
  passenger_id: string | null;
  route: string;
  tier: number;
  severity: number;
  severity_reasons: string[];
  value: number;
  target_aed: number;
  reward: { type: string; label: string; detail: string; cost_aed: number; acceptance?: number } | null;
  preferred: { type: string; label: string; score: number }[];
  why: string[];
  downgraded_for_budget: boolean;
  note: string;
}

export interface RewardPlan {
  budget_aed: number;
  planned_spend_aed: number;
  left_aed: number;
  ideal_spend_aed: number;
  budget_covers_share: number;
  passengers: number;
  rewarded: number;
  by_type: Record<string, { passengers: number; spend_aed: number }>;
  disruption: { score: number; label: string };
  preference_model?: { kind: string; synthetic_training_data: boolean; auc?: number; baseline_proxy_rules_auc?: number };
  assumptions: string[];
  rows: RewardRow[];
}

// --- Phase 3: agent runs (app/agent_api.py) ---
export interface AgentStep {
  n: number;
  tool: string;
  input: Record<string, unknown>;
  summary: string;
  note: string;
  error: boolean;
  ms: number;
  at: string;
}

export interface AgentRecommendation {
  flight_id: string;
  delay_minutes: number;
  option_key: string;
  strategy: StrategyKey;
  reasons: string[];
  risks: string[];
  checks: string[];
}

export type AgentStatus = "RUNNING" | "DONE" | "FAILED";

export interface AgentRun {
  id: string;
  flight_id: string;
  delay_minutes: number | null;
  strategy: StrategyKey | null;
  note: string;
  status: AgentStatus;
  source: string | null;
  fallback_reason: string | null;
  trace: AgentStep[];
  recommendation: AgentRecommendation | null;
  error: string | null;
  scenario_id: string | null;
  created_by: string;
  created_at: string;
  finished_at: string | null;
}

export type AgentRunSummary = Omit<AgentRun, "trace" | "note" | "fallback_reason">;

export interface AgentRunRequest {
  flight_id: string;
  delay_minutes?: number | null;
  strategy?: StrategyKey | null;
  note?: string;
}

export interface ModelMetrics {
  observed_rate: number;
  auc: number | null;
  brier: number;
  baseline_auc?: number | null;
  baseline_brier?: number;
  climatology_brier: number;
}

export interface ConfusionPoint {
  label?: string;
  cutoff: number;
  true_positive: number;
  false_positive: number;
  false_negative: number;
  true_negative: number;
  precision: number | null;
  recall: number | null;
  f1: number;
  accuracy: number | null;
  specificity: number | null;
  flagged_share: number | null;
}

export interface Classification {
  operating_points: ConfusionPoint[];
  sweep: Pick<ConfusionPoint, "cutoff" | "precision" | "recall" | "f1" | "flagged_share">[];
  top_10_percent: { share: number; flights: number; late_rate: number; overall_rate: number; lift: number | null };
}

export interface RollingFold {
  month: string;
  train_flights: number;
  test_flights: number;
  [threshold: string]: ModelMetrics | string | number;
}

export interface ModelCard {
  model: string;
  trained_at: string;
  thresholds_minutes: number[];
  features: string[];
  target?: string;
  versions?: Record<string, string>;
  evaluation: {
    train: string;
    test: string;
    baseline?: string;
    metrics_by_threshold: Record<string, ModelMetrics>;
    connection_backtest: { slack: string; pairs: number; predicted: number; observed: number }[];
    classification?: Record<string, Classification>;
    rolling_monthly?: RollingFold[];
  };
  production?: {
    train: string;
    scored_flights: number;
    bands_on_p60: { high: number; medium: number };
  };
  connections?: { pairs: number; default_mct_minutes: number };
  assumptions: string[];
}

let token: string | null = null;
export const setToken = (value: string | null): void => {
  token = value;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as Problem | null;
    throw new ApiError(problem ?? { title: response.statusText, status: response.status });
  }
  return (await response.json()) as T;
}

const post = <T>(path: string, body: unknown): Promise<T> =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  login: (username: string, password: string) => post<Session>("/api/v1/auth/login", { username, password }),
  meta: () => request<Meta>("/api/v1/meta"),
  presets: () => request<{ delay: DelayPreset[]; cancel: CancelPreset[] }>("/api/v1/presets"),
  flights: (q: string, day?: string) =>
    request<FlightRow[]>(`/api/v1/flights?q=${encodeURIComponent(q)}${day ? `&day=${day}` : ""}&limit=30`),
  createScenario: (body: { kind: "DELAY" | "CANCEL"; flight_id: string; delay_minutes?: number; weights: Weights;
    strategy?: StrategyKey }) =>
    post<Scenario>("/api/v1/scenarios", body),
  scenarios: () => request<ScenarioSummary[]>("/api/v1/scenarios"),
  scenario: (id: string) => request<Scenario>(`/api/v1/scenarios/${id}`),
  reprioritise: (id: string, weights: Weights) => post<Scenario>(`/api/v1/scenarios/${id}/reprioritise`, { weights }),
  selectOption: (id: string, optionKey: string) =>
    post<Scenario>(`/api/v1/scenarios/${id}/select`, { option_key: optionKey }),
  chooseStrategy: (id: string, strategy: StrategyKey) =>
    post<Scenario>(`/api/v1/scenarios/${id}/strategy`, { strategy }),
  startAgent: (body: AgentRunRequest) => post<AgentRun>("/api/v1/agent/runs", body),
  agentRun: (id: string) => request<AgentRun>(`/api/v1/agent/runs/${encodeURIComponent(id)}`),
  agentRuns: () => request<AgentRunSummary[]>("/api/v1/agent/runs"),
  decisions: (id: string) => request<Decision[]>(`/api/v1/scenarios/${id}/decisions`),
  decide: (id: string, target: string, action: "APPROVE" | "REJECT", comment = "") =>
    post<Decision>(`/api/v1/scenarios/${id}/decisions`, { target, action, comment }),
  watchlist: (band: "all" | "medium" | "high", sort: "misconnects" | "delay") =>
    request<Watchlist>(`/api/v1/risk/watchlist?days=7&band=${band}&sort=${sort}&limit=60`),
  flightRisk: (flightId: string) =>
    request<{ flight: RiskFlight; connections: ConnectionRisk[] }>(`/api/v1/risk/flights/${encodeURIComponent(flightId)}?limit=30`),
  rewards: (id: string, budgetAed: number) =>
    post<RewardPlan>(`/api/v1/scenarios/${id}/rewards`, { budget_aed: budgetAed }),
  cascade: () => request<CascadeCheck>("/api/v1/risk/cascade"),
  modelCard: () => request<ModelCard>("/api/v1/risk/model"),
  message: (id: string, customerKey: string) =>
    post<{ text: string; source: string }>(`/api/v1/scenarios/${id}/messages`, { customer_key: customerKey }),
};

export const errorText = (error: unknown, fallback: string): string =>
  error instanceof ApiError ? (error.problem.errors?.[0]?.msg ?? error.message) : fallback;
