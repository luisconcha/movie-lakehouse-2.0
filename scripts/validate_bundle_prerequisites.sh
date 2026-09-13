#!/usr/bin/env bash

set -euo pipefail

PROFILE="movie-lakehouse-2.0"

echo "======================================"
echo " Movie Lakehouse 2.0"
echo " Validação dos pré-requisitos do Bundle"
echo " Contexto de execução: LOCAL"
echo "======================================"

echo
echo "--> Validando raiz do repositório"

if [[ ! -d ".git" ]]; then
  echo "ERRO: diretório .git não encontrado."
  echo "Execute o script a partir da raiz do repositório."
  exit 1
fi

if [[ ! -f "databricks.yml" ]]; then
  echo "ERRO: databricks.yml não encontrado."
  echo "Execute o script a partir da raiz do repositório."
  exit 1
fi

echo
echo "--> Validando Databricks CLI"

if ! command -v databricks >/dev/null 2>&1; then
  echo "ERRO: Databricks CLI não encontrado no PATH."
  exit 1
fi

databricks --version

echo
echo "--> Validando autenticação e comunicação com o workspace"
echo "Profile esperado: ${PROFILE}"

if ! databricks current-user me --profile "${PROFILE}"; then
  echo
  echo "ERRO: não foi possível autenticar ou comunicar com o workspace"
  echo "usando o profile '${PROFILE}'."
  echo
  echo "Configure ou renove a autenticação com:"
  echo
  echo "  databricks auth login \\"
  echo "    --host https://<HOST-DO-WORKSPACE-MOVIE-LAKEHOUSE-2.0> \\"
  echo "    --profile ${PROFILE}"
  echo
  echo "Depois execute novamente este script."
  exit 1
fi

echo
echo "--> Pré-requisitos locais do Bundle validados com sucesso."