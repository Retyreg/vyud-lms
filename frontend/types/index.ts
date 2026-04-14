export type BackendStatus = 'loading' | 'warming' | 'ok' | 'error';

export interface HealthInfo {
  status: 'ok' | 'degraded' | 'error';
  uptime_seconds: number;
  database: 'connected' | 'not_configured' | 'error';
  database_error: string | null;
  ai_openrouter: 'configured' | 'not_configured';
}

export interface ApiNode {
  id: number;
  label: string;
  level: number;
  is_completed: boolean;
  is_available: boolean;
  mastery_pct: number;
  next_review: string | null;
}

export interface ApiEdge {
  source: number;
  target: number;
}

export interface FlowNode {
  id: string;
  data: { label: string; isAvailable: boolean };
}

export interface MemberProgress {
  user_key: string;
  completed_count: number;
  total_count: number;
  percent: number;
  avg_mastery_pct: number;
  current_streak: number;
}

export interface DashboardData {
  org_name: string;
  invite_code: string;
  members: MemberProgress[];
}

export interface WeekActivity {
  week_label: string;
  reviews: number;
}

export interface ROIData {
  org_name: string;
  total_members: number;
  active_members: number;
  total_nodes: number;
  avg_completion_rate: number;
  avg_days_to_first_completion: number | null;
  fastest_member: string | null;
  total_reviews: number;
  avg_streak: number;
  onboarding_efficiency_score: number;
  summary: string;
  weekly_activity: WeekActivity[];
}

export interface StreakAchievement {
  id: string;
  label: string;
  type: 'streak' | 'days';
  threshold: number;
}

export interface StreakMilestone {
  label: string;
  streak_needed?: number;
  days_needed?: number;
  days_left: number;
}

export interface StreakInfo {
  current_streak: number;
  longest_streak: number;
  total_days_active: number;
  last_activity_date: string | null;
  badge: string | null;
  activity_dates: string[];
  achievements: StreakAchievement[];
  next_milestone: StreakMilestone | null;
}

export interface SOPListItem {
  id: number;
  title: string;
  description: string | null;
  status: string;
  steps_count: number;
  is_completed: boolean;
}

export interface SOPStep {
  step_number: number;
  title: string;
  content: string;
}

export interface SOPQuizQuestion {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

export interface SOPDetail {
  id: number;
  title: string;
  description: string | null;
  status: string;
  steps: SOPStep[];
  quiz_json: SOPQuizQuestion[] | null;
  created_at: string | null;
}
