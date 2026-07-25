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

{{- define "oura.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oura.labels" -}}
app.kubernetes.io/name: {{ include "oura.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ include "oura.chart" . }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "oura.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oura.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "oura.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "oura.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "oura.tokenPvcName" -}}
{{- printf "%s-token" (include "oura.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "oura.image" -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- printf "%s:%s" .Values.image.repository $tag -}}
{{- end -}}

{{- define "oura.bootstrapEnabled" -}}
{{- ternary "true" "false" (or .Values.quickstart.enabled .Values.postgres.bootstrap.enabled) -}}
{{- end -}}

{{- define "oura.dashboardEnabled" -}}
{{- ternary "true" "false" (or .Values.quickstart.enabled .Values.dashboard.enabled) -}}
{{- end -}}

{{- define "oura.createDatasource" -}}
{{- ternary "true" "false" (or .Values.quickstart.enabled .Values.dashboard.createDatasource) -}}
{{- end -}}

{{- define "oura.postgresSecretName" -}}
{{- if .Values.postgres.existingSecret -}}
{{- .Values.postgres.existingSecret -}}
{{- else -}}
{{- printf "%s-db" (include "oura.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "oura.authSecretName" -}}
{{- if .Values.auth.existingSecret -}}
{{- .Values.auth.existingSecret -}}
{{- else -}}
{{- printf "%s-auth" (include "oura.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "oura.adminSecretName" -}}
{{- if .Values.postgres.bootstrap.admin.existingSecret -}}
{{- .Values.postgres.bootstrap.admin.existingSecret -}}
{{- else -}}
{{- printf "%s-pgadmin" (include "oura.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "oura.createPostgresSecret" -}}
{{- ternary "true" "false" (and (empty .Values.postgres.existingSecret) (ne (.Values.postgres.password | default "") "")) -}}
{{- end -}}

{{- define "oura.createAuthSecret" -}}
{{- ternary "true" "false" (and (empty .Values.auth.existingSecret) (eq .Values.auth.mode "pat") (ne (.Values.auth.pat | default "") "")) -}}
{{- end -}}

{{- define "oura.createAdminSecret" -}}
{{- ternary "true" "false" (and (eq (include "oura.bootstrapEnabled" .) "true") (empty .Values.postgres.bootstrap.admin.existingSecret) (ne (.Values.postgres.bootstrap.admin.password | default "") "")) -}}
{{- end -}}

{{/*
Read-only role for bootstrap / Grafana. Explicit values win.
Quickstart defaults to oura_ro only when the chart creates the DB Secret,
so existingSecret installs are not forced to provide password-ro.
*/}}
{{- define "oura.readOnlyUser" -}}
{{- $u := .Values.postgres.bootstrap.readOnlyUser | default "" -}}
{{- if $u -}}
{{- $u -}}
{{- else if and .Values.quickstart.enabled (eq (include "oura.createPostgresSecret" .) "true") -}}
oura_ro
{{- end -}}
{{- end -}}

{{- define "oura.readOnlyPasswordKey" -}}
{{- if include "oura.readOnlyUser" . -}}
{{- .Values.postgres.bootstrap.readOnlyPasswordKey | default "password-ro" -}}
{{- end -}}
{{- end -}}

{{- define "oura.dashboardDatasourceUser" -}}
{{- $configured := .Values.dashboard.datasource.user | default "" -}}
{{- $roUser := include "oura.readOnlyUser" . -}}
{{- $roKey := include "oura.readOnlyPasswordKey" . -}}
{{- if $configured -}}
{{- $configured -}}
{{- else if and (eq (include "oura.bootstrapEnabled" .) "true") $roUser $roKey -}}
{{- $roUser -}}
{{- else -}}
{{- .Values.postgres.user -}}
{{- end -}}
{{- end -}}

{{- define "oura.dashboardDatasourceSecretName" -}}
{{- $configured := .Values.dashboard.datasource.existingSecret | default "" -}}
{{- if $configured -}}
{{- $configured -}}
{{- else -}}
{{- include "oura.postgresSecretName" . -}}
{{- end -}}
{{- end -}}

{{- define "oura.dashboardDatasourcePasswordKey" -}}
{{- $configured := .Values.dashboard.datasource.passwordKey | default "" -}}
{{- $roUser := include "oura.readOnlyUser" . -}}
{{- $roKey := include "oura.readOnlyPasswordKey" . -}}
{{- if $configured -}}
{{- $configured -}}
{{- else if and (eq (include "oura.bootstrapEnabled" .) "true") $roUser $roKey -}}
{{- $roKey -}}
{{- else -}}
{{- .Values.postgres.passwordKey -}}
{{- end -}}
{{- end -}}

{{- define "oura.dashboardDatasourcePassword" -}}
{{- $explicit := .Values.dashboard.datasource.password | default "" -}}
{{- if $explicit -}}
{{- $explicit -}}
{{- else if eq (include "oura.createPostgresSecret" .) "true" -}}
{{- $key := include "oura.dashboardDatasourcePasswordKey" . -}}
{{- if eq $key (include "oura.readOnlyPasswordKey" .) -}}
{{- .Values.postgres.passwordRo | default "" -}}
{{- else -}}
{{- .Values.postgres.password | default "" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "oura.collectorEnv" -}}
- name: HOME
  value: /tmp
- name: TMPDIR
  value: /tmp
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
      name: {{ include "oura.postgresSecretName" . }}
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
      name: {{ include "oura.authSecretName" . }}
      key: {{ .Values.auth.patKey }}
{{- else if eq .Values.auth.mode "oauth" }}
- name: OURA_CLIENT_ID
  valueFrom:
    secretKeyRef:
      name: {{ include "oura.authSecretName" . }}
      key: {{ .Values.auth.clientIdKey }}
- name: OURA_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "oura.authSecretName" . }}
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

{{- define "oura.volumeMounts" -}}
- name: tmp
  mountPath: /tmp
{{- if eq .Values.auth.mode "oauth" }}
- name: token
  mountPath: {{ .Values.persistence.mountPath }}
{{- end }}
{{- end -}}

{{- define "oura.volumes" -}}
- name: tmp
  emptyDir: {}
{{- if eq .Values.auth.mode "oauth" }}
- name: token
  persistentVolumeClaim:
    claimName: {{ include "oura.tokenPvcName" . }}
{{- end }}
{{- end -}}

{{- define "oura.jobScheduling" -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.podSecurityContext }}
securityContext:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}

{{/* Usage: include "oura.container" (dict "root" $ "name" "collector" "backfill" false) */}}
{{- define "oura.container" -}}
- name: {{ .name }}
  image: {{ include "oura.image" .root | quote }}
  imagePullPolicy: {{ .root.Values.image.pullPolicy }}
  {{- with .root.Values.securityContext }}
  securityContext:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  env:
    {{- if .backfill }}
    - name: BACKFILL
      value: "1"
    - name: START_DATE
      value: {{ .root.Values.backfill.startDate | quote }}
    {{- end }}
    {{- include "oura.collectorEnv" .root | nindent 4 }}
  resources:
    {{- if .backfill }}
    {{- toYaml .root.Values.backfill.resources | nindent 4 }}
    {{- else }}
    {{- toYaml .root.Values.resources | nindent 4 }}
    {{- end }}
  volumeMounts:
    {{- include "oura.volumeMounts" .root | nindent 4 }}
{{- end -}}

{{- define "oura.podSpec" -}}
{{- /* Usage: include "oura.podSpec" (dict "root" $ "name" "collector" "backfill" false) */ -}}
restartPolicy: Never
serviceAccountName: {{ include "oura.serviceAccountName" .root }}
automountServiceAccountToken: {{ .root.Values.serviceAccount.automount }}
{{- include "oura.jobScheduling" .root | nindent 0 }}
containers:
  {{- include "oura.container" . | nindent 2 }}
volumes:
  {{- include "oura.volumes" .root | nindent 2 }}
{{- end -}}
