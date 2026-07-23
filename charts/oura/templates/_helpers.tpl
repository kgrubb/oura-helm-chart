{{/* Expand the name of the chart. */}}
{{- define "oura.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oura.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "oura.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "oura.labels" -}}
app.kubernetes.io/name: {{ include "oura.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "oura.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oura.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "oura.configMapName" -}}
{{- printf "%s-collector" (include "oura.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oura.tokenPvcName" -}}
{{- printf "%s-token" (include "oura.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oura.useOauth" -}}
{{- eq .Values.auth.mode "oauth" -}}
{{- end -}}

{{- define "oura.collectorEnv" -}}
- name: TZ
  value: {{ .Values.timeZone | quote }}
- name: PGHOST
  value: {{ .Values.postgres.host | quote }}
- name: PGPORT
  value: {{ .Values.postgres.port | quote }}
- name: PGDATABASE
  value: {{ .Values.postgres.database | quote }}
- name: PGUSER
  value: {{ .Values.postgres.user | quote }}
- name: PGPASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ required "postgres.existingSecret is required" .Values.postgres.existingSecret }}
      key: {{ .Values.postgres.passwordKey }}
- name: OURA_RECENT_DAYS
  value: {{ .Values.recentDays | quote }}
- name: OURA_HR_CHUNK_DAYS
  value: {{ .Values.hrChunkDays | quote }}
- name: OURA_PAGE_SLEEP
  value: {{ .Values.pageSleepSeconds | quote }}
{{- if eq .Values.auth.mode "pat" }}
- name: OURA_PAT
  valueFrom:
    secretKeyRef:
      name: {{ required "auth.existingSecret is required" .Values.auth.existingSecret }}
      key: {{ .Values.auth.patKey }}
{{- else if eq .Values.auth.mode "oauth" }}
- name: OURA_CLIENT_ID
  valueFrom:
    secretKeyRef:
      name: {{ required "auth.existingSecret is required" .Values.auth.existingSecret }}
      key: {{ .Values.auth.clientIdKey }}
- name: OURA_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ .Values.auth.existingSecret }}
      key: {{ .Values.auth.clientSecretKey }}
- name: OURA_TOKEN_PATH
  value: {{ printf "%s/%s" .Values.persistence.mountPath .Values.persistence.tokenFile | quote }}
{{- else }}
{{- fail "auth.mode must be pat or oauth" }}
{{- end }}
{{- range $k, $v := .Values.extraEnv }}
- name: {{ $k }}
  value: {{ $v | quote }}
{{- end }}
{{- end -}}
