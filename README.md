# movie-lakehouse-2.0

Projeto de engenharia de dados construído no Azure Databricks com arquitetura medalhão Bronze -> Silver -> Gold.

## Objetivo

Construir um produto de dados de filmes coerente, reproduzível e defensável, voltado principalmente a consumo analítico e BI.

## Arquitetura

O fluxo lógico da aplicação é:

RAW externo -> Bronze -> Silver -> Gold -> Analistas / BI

- **Bronze:** preservação da fonte e rastreabilidade.
- **Silver:** tipagem, limpeza, parsing, normalização e integridade.
- **Gold:** produtos orientados às necessidades analíticas aprovadas.
- **EDA:** investigação separada do fluxo produtivo.

## Plataforma

A fundação Azure/Databricks é um pré-requisito externo.

Este repositório não provisiona nem administra infraestrutura, identidade, storage, grants, ownership ou bootstrap da plataforma.

## Estrutura

- `notebooks/_shared/`: contratos estruturais e interface central de configuração.
- `notebooks/_eda/`: investigação e evidências exploratórias versionadas.
- `notebooks/01_bronze/`: processamento Bronze.
- `notebooks/02_silver/`: processamento Silver.
- `notebooks/03_gold/`: processamento Gold.
- `resources/`: recursos declarativos de deployment quando aplicáveis.

A estrutura é criada conforme necessidades reais do projeto; diretórios e abstrações não são adicionados apenas para antecipar etapas futuras.

## Configuração

Os workloads produtivos devem consumir valores dependentes de ambiente por meio de `notebooks/_shared/configuration.py`.

A origem física desses valores pertence ao mecanismo de deployment/execução e não deve ser reproduzida como valores hardcoded nos notebooks produtivos.