#!/usr/bin/env bash

set -euo pipefail

TARGET="dev"

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
echo "--> Validando configuração, autenticação e comunicação do Bundle"
echo "Target esperado: ${TARGET}"

if ! databricks bundle validate -t "${TARGET}" >/dev/null; then
  echo
  echo "ERRO: não foi possível validar o Bundle no target '${TARGET}'."
  echo "Verifique a configuração do target e a autenticação para o workspace correspondente."
  exit 1
fi

echo
echo "--> Pré-requisitos locais do Bundle validados com sucesso."