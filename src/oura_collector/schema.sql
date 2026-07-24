CREATE TABLE IF NOT EXISTS personal_info (
  id int PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  email text, age int, weight double precision, height double precision,
  biological_sex text, raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_activity (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, score double precision,
  steps double precision, active_calories double precision, total_calories double precision,
  sedentary_time double precision, low_activity_time double precision,
  medium_activity_time double precision, high_activity_time double precision,
  target_calories double precision, target_meters double precision, meters_to_target double precision,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_readiness (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, score double precision,
  temperature_deviation double precision, temperature_trend_deviation double precision,
  contributors jsonb NOT NULL DEFAULT '{}', raw jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_sleep (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, score double precision,
  contributors jsonb NOT NULL DEFAULT '{}', raw jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_spo2 (
  id text PRIMARY KEY, day date NOT NULL UNIQUE,
  spo2_percentage_average double precision, breathing_disturbance_index double precision,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_stress (
  id text PRIMARY KEY, day date NOT NULL UNIQUE,
  stress_high double precision, recovery_high double precision, day_summary text,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_resilience (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, level text,
  contributors jsonb NOT NULL DEFAULT '{}', raw jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_cardiovascular_age (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, vascular_age double precision,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS vo2_max (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, vo2_max double precision,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sleep_time (
  id text PRIMARY KEY, day date NOT NULL UNIQUE, recommendation text, status text,
  optimal_bedtime text, raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS workout (
  id text PRIMARY KEY, day date, activity text, calories double precision,
  distance double precision, intensity text, label text,
  start_datetime timestamptz, end_datetime timestamptz,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS workout_day_idx ON workout (day);
CREATE TABLE IF NOT EXISTS sleep_period (
  id text PRIMARY KEY, day date, bedtime_start timestamptz, bedtime_end timestamptz,
  average_breath double precision, average_heart_rate double precision, average_hrv double precision,
  awake_time double precision, deep_sleep_duration double precision,
  light_sleep_duration double precision, rem_sleep_duration double precision,
  total_sleep_duration double precision, efficiency double precision, latency double precision,
  lowest_heart_rate double precision, restless_periods double precision, type text,
  raw jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS sleep_period_day_idx ON sleep_period (day);
CREATE INDEX IF NOT EXISTS sleep_period_bedtime_idx ON sleep_period (bedtime_start);
CREATE TABLE IF NOT EXISTS sleep_stage (
  sleep_id text NOT NULL REFERENCES sleep_period (id) ON DELETE CASCADE,
  start_ts timestamptz NOT NULL, end_ts timestamptz NOT NULL, stage text NOT NULL,
  PRIMARY KEY (sleep_id, start_ts));
CREATE INDEX IF NOT EXISTS sleep_stage_range_idx ON sleep_stage (start_ts, end_ts);
CREATE TABLE IF NOT EXISTS heartrate (ts timestamptz PRIMARY KEY, bpm int NOT NULL, source text);
CREATE TABLE IF NOT EXISTS symptom_radar_daily (
  day date PRIMARY KEY, level text NOT NULL, score int NOT NULL DEFAULT 0,
  n_baseline_nights int NOT NULL DEFAULT 0, n_signals int NOT NULL DEFAULT 0,
  contributors jsonb NOT NULL DEFAULT '[]', summary_text text NOT NULL DEFAULT '',
  algorithm_version text NOT NULL DEFAULT 'v1', computed_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sync_state (
  resource text PRIMARY KEY, high_watermark timestamptz, updated_at timestamptz NOT NULL DEFAULT now());
ALTER TABLE daily_activity ADD COLUMN IF NOT EXISTS sedentary_time double precision;
ALTER TABLE daily_activity ADD COLUMN IF NOT EXISTS low_activity_time double precision;
ALTER TABLE daily_activity ADD COLUMN IF NOT EXISTS medium_activity_time double precision;
ALTER TABLE daily_activity ADD COLUMN IF NOT EXISTS high_activity_time double precision;
ALTER TABLE daily_activity ADD COLUMN IF NOT EXISTS target_calories double precision;
ALTER TABLE daily_activity ADD COLUMN IF NOT EXISTS target_meters double precision;
ALTER TABLE daily_activity ADD COLUMN IF NOT EXISTS meters_to_target double precision;
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'oura_ro') THEN
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO oura_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO oura_ro;
  END IF;
END $$;
