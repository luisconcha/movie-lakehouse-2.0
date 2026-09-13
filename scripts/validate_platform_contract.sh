#!/usr/bin/env bash

set -euo pipefail

TARGET="dev"
PROFILE="movie-lakehouse-2.0"

echo "======================================"
echo " Movie Lakehouse 2.0"
echo " Validação mínima do contrato da plataforma"
echo " Contexto de execução: LOCAL"
echo "======================================"

echo
echo "--> Validando execução a partir da raiz do repositório"

if [[ ! -d ".git" || ! -f "databricks.yml" ]]; then
  echo "ERRO: execute este script localmente, a partir da raiz do repositório."
  exit 1
fi

echo
echo "--> Resolvendo configuração do target '${TARGET}'"

BUNDLE_JSON="$(
  databricks bundle validate \
    -t "${TARGET}" \
    --output json
)"

read_bundle_variable() {
  local variable="$1"

  BUNDLE_JSON="${BUNDLE_JSON}" \
  VARIABLE="${variable}" \
  python3 <<'PY'
import json
import os

data = json.loads(os.environ["BUNDLE_JSON"])
name = os.environ["VARIABLE"]

try:
    print(data["variables"][name]["value"])
except (KeyError, TypeError):
    raise SystemExit(
        f"ERRO: variável '{name}' não encontrada no Bundle resolvido."
    )
PY
}

CATALOG="$(read_bundle_variable catalog)"
BRONZE_SCHEMA="$(read_bundle_variable bronze_schema)"
RAW_VOLUME="$(read_bundle_variable raw_volume)"

BRONZE_NAMESPACE="${CATALOG}.${BRONZE_SCHEMA}"
RAW_VOLUME_FULL_NAME="${BRONZE_NAMESPACE}.${RAW_VOLUME}"
RAW_VOLUME_PATH="dbfs:/Volumes/${CATALOG}/${BRONZE_SCHEMA}/${RAW_VOLUME}"

echo
echo "Configuração resolvida:"
echo "  Catalog:    ${CATALOG}"
echo "  Bronze:     ${BRONZE_NAMESPACE}"
echo "  Raw volume: ${RAW_VOLUME_FULL_NAME}"

echo
echo "--> Validando catálogo"

databricks catalogs get \
  "${CATALOG}" \
  --profile "${PROFILE}" \
  --output json >/dev/null

echo "OK: catálogo '${CATALOG}' acessível."

echo
echo "--> Validando schema Bronze"

databricks schemas get \
  "${BRONZE_NAMESPACE}" \
  --profile "${PROFILE}" \
  --output json >/dev/null

echo "OK: schema '${BRONZE_NAMESPACE}' acessível."

echo
echo "--> Validando volume raw"

databricks volumes read \
  "${RAW_VOLUME_FULL_NAME}" \
  --profile "${PROFILE}" \
  --output json >/dev/null

echo "OK: volume '${RAW_VOLUME_FULL_NAME}' acessível."

echo
echo
echo "--> Validando arquivos raw"

RAW_FILES="$(
  databricks fs ls \
    "${RAW_VOLUME_PATH}" \
    --profile "${PROFILE}"
)"

for file in \
  "tmdb_5000_movies.csv" \
  "tmdb_5000_credits.csv"
do
  FILE_PATH="${RAW_VOLUME_PATH}/${file}"

  if ! grep -Fq "${file}" <<< "${RAW_FILES}"; then
    echo "ERRO: arquivo '${file}' não encontrado em '${RAW_VOLUME_PATH}'."
    exit 1
  fi

  databricks fs cat \
    "${FILE_PATH}" \
    --profile "${PROFILE}" >/dev/null

  echo "OK: '${file}' existe e é legível."
done


echo
echo "======================================"
echo " Contrato mínimo da plataforma validado"
echo "======================================"
echo "Nenhum recurso foi criado ou alterado."
echo "Nenhum GRANT foi executado."