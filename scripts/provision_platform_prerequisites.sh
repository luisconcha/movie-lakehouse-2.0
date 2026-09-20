#!/usr/bin/env bash

set -euo pipefail

TARGET="dev"

echo "======================================"
echo " Movie Lakehouse 2.0"
echo " Provisionamento dos pré-requisitos"
echo " Contexto: PLATAFORMA / BOOTSTRAP"
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
SILVER_SCHEMA="$(read_bundle_variable silver_schema)"
GOLD_SCHEMA="$(read_bundle_variable gold_schema)"

echo
echo "Configuração resolvida:"
echo "  Catalog: ${CATALOG}"
echo "  Bronze:  ${CATALOG}.${BRONZE_SCHEMA}"
echo "  Silver:  ${CATALOG}.${SILVER_SCHEMA}"
echo "  Gold:    ${CATALOG}.${GOLD_SCHEMA}"

provision_schema() {
  local schema="$1"
  local namespace="${CATALOG}.${schema}"

  echo
  echo "--> Verificando schema '${namespace}'"

  if databricks schemas get \
    "${namespace}" \
    --target "${TARGET}" \
    --output json >/dev/null 2>&1
  then
    echo "OK: schema '${namespace}' já existe."
    return
  fi

  echo "Schema '${namespace}' não encontrado."
  echo "--> Criando schema '${namespace}'"

  databricks schemas create \
    "${schema}" \
    "${CATALOG}" \
    --target "${TARGET}" \
    --output json >/dev/null

  echo "OK: schema '${namespace}' criado."
}

provision_schema "${BRONZE_SCHEMA}"
provision_schema "${SILVER_SCHEMA}"
provision_schema "${GOLD_SCHEMA}"

echo
echo "======================================"
echo " Provisionamento concluído"
echo "======================================"
echo "Nenhum GRANT ou alteração de ownership foi executado."