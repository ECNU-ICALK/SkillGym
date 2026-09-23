{{- define "podpulse.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "podpulse.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "podpulse.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "podpulse.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "podpulse.selectorLabels" -}}
app.kubernetes.io/name: {{ include "podpulse.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "podpulse.labels" -}}
helm.sh/chart: {{ include "podpulse.chart" . }}
{{ include "podpulse.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: api
app.kubernetes.io/part-of: observability-suite
platform.example.com/team: sre
platform.example.com/tier: observability
platform.example.com/environment: {{ .Values.environment | quote }}
{{- end -}}

{{- define "podpulse.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "podpulse.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
default
{{- end -}}
{{- end -}}
