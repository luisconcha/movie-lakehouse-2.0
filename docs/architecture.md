# Arquitetura do movie-lakehouse-2.0

![Arquitetura do
movie-lakehouse-2.0](assets/movie-lakehouse-architecture.png)

## 1. Visão geral

O `movie-lakehouse-2.0` é um produto de engenharia de dados construído no Azure Databricks para transformar o **TMDB 5000 Movie Dataset** em dados governados e produtos analíticos orientados principalmente a analistas e consumidores de BI.

```text
TMDB 5000 → Volume raw no Unity Catalog → Bronze → Silver → Gold → Analistas / BI
```

A solução combina Azure Databricks, Apache Spark, Delta Lake, Unity Catalog, Lakeflow Jobs, Databricks Declarative Automation Bundles, GitHub Actions e autenticação GitHub OIDC. A arquitetura é deliberadamente simples: componentes adicionais não são introduzidos sem necessidade comprovada pelo produto ou pela operação.

## 2. Fronteira entre infraestrutura e aplicação

O projeto separa a preparação da fundação Azure/Databricks da execução do workload de engenharia de dados.

O projeto complementar [`databricks-infra-bootstrap`](https://github.com/luisconcha/databricks-infra-bootstrap) é a implementação utilizada e validada neste ecossistema para preparar uma fundação capaz de receber workloads como o `movie-lakehouse-2.0`.

O `databricks-infra-bootstrap` pode preparar infraestrutura Azure e Azure Databricks, identidade e acesso, storage, Unity Catalog, schemas, Volumes, governança e permissões.

O `movie-lakehouse-2.0` valida os pré-requisitos externos que consome, ingere os arquivos raw, transforma e normaliza os dados, aplica qualidade, publica os produtos analíticos, orquestra o DAG e implanta somente recursos pertencentes ao workload.

A preparação de um ambiente para receber a aplicação inclui conceder à identidade de execução os privilégios mínimos necessários sobre os objetos do Unity Catalog consumidos pelo workload. Essa configuração é realizada externamente à execução da aplicação e deve ser feita pelo responsável pela preparação do ambiente.

No cenário validado pelo projeto, a identidade técnica utilizada pelo CI/CD recebeu:

- `USE CATALOG` no catálogo utilizado pela aplicação;
- `USE SCHEMA`, `SELECT`, `MODIFY` e `CREATE TABLE` nos schemas `bronze`, `silver` e `gold`;
- `READ VOLUME` no Volume `bronze.raw`.

Esses privilégios permitem que a aplicação consuma os arquivos raw e materialize suas tabelas, sem exigir privilégios administrativos amplos.

Nenhum `GRANT`, alteração de ownership ou correção administrativa de permissões é executado pelos notebooks, pelo Lakeflow Job ou pelo Bundle durante o processamento. Se os privilégios necessários não estiverem disponíveis, a aplicação deve falhar de forma diagnosticável em vez de tentar ampliar suas próprias permissões.

Essa separação permite implantar a aplicação em outra fundação compatível, desde que o ambiente e a identidade de execução tenham sido previamente preparados com os recursos e privilégios necessários.

## 3. Fluxo de dados

### 3.1 Fonte e Volume raw

A origem é o **TMDB 5000 Movie Dataset**, disponibilizado no Kaggle. A aplicação consome:

```text
tmdb_5000_movies.csv
tmdb_5000_credits.csv
```

Os arquivos não são distribuídos pelo repositório. Eles são disponibilizados externamente em um Volume do Unity Catalog denominado logicamente `raw`.

```text
Kaggle → arquivos CSV → Unity Catalog Volume: raw → Bronze
```

### 3.2 Bronze

A Bronze representa a ingestão do snapshot raw para tabelas Delta governadas pelo Unity Catalog.

```text
bronze.credits
bronze.movies
```

Suas responsabilidades são ler os dois CSVs com schema explícito, preservar os campos raw necessários, registrar metadados de rastreabilidade, detectar incompatibilidades relevantes na estrutura esperada e materializar o snapshot em Delta.

A camada utiliza semântica de **snapshot completo com overwrite**. As duas tabelas são materializações independentes; não existe atomicidade conjunta entre suas escritas. Em uma falha parcial, a recuperação validada consiste em diagnosticar a causa, corrigi-la e executar novamente o workload integral.

### 3.3 Silver

A Silver transforma a representação raw em entidades tipadas e normalizadas:

```text
silver.cast_credit
silver.crew_credit
silver.movie
silver.movie_genre
silver.movie_keyword
silver.movie_production_company
silver.movie_production_country
silver.movie_spoken_language
```

A camada realiza tipagem, parsing das estruturas semiestruturadas, normalização das relações multivaloradas, preservação das chaves necessárias e aplicação das regras estruturais e de qualidade definidas.

Entidades como gêneros, palavras-chave, empresas, países, idiomas, elenco e equipe são materializadas em relações próprias, em vez de manter arrays semiestruturados como interface principal de consumo.

As materializações Silver também são independentes e utilizam overwrite. Não há rollback transacional entre todas as tabelas da camada; após diagnóstico e correção de uma falha parcial, a estratégia validada é a reexecução integral.

### 3.4 Gold

A Gold publica sete produtos de dados orientados ao consumo analítico:

```text
gold.movie_company_performance
gold.movie_country_performance
gold.movie_credit_participation
gold.movie_genre_performance
gold.movie_keyword_performance
gold.movie_language_profile
gold.movie_performance
```

Os produtos possuem grão e semântica próprios. Entre as regras materializadas estão:

- `release_year` derivado de `release_date`;
- elegibilidade das métricas comerciais condicionada a `budget > 0`;
- `profit = revenue - budget` quando elegível;
- `roi = (revenue - budget) / budget` quando elegível;
- `profit` e `roi` nulos quando `budget <= 0`;
- distinção entre participação de `cast` e `crew`;
- distinção entre idioma original e idioma falado.

Filmes com `budget > 0` e `revenue = 0` continuam elegíveis para métricas comerciais; resultado negativo é válido.

Produtos derivados de relações N:N carregam métricas necessárias no grão da associação. O projeto não introduz agregações implícitas que poderiam esconder risco de dupla contagem.

Os contratos executáveis permanecem a referência para schemas, tipos, chaves e demais detalhes de implementação.

## 4. Contratos e qualidade

Qualidade é uma responsabilidade contínua do fluxo, não uma etapa isolada no final.

Os contratos tornam verificáveis schema e tipos, campos obrigatórios, chaves, unicidade no grão esperado, integridade referencial, regras de negócio e relações esperadas quando aplicáveis.

Os módulos em `notebooks/_shared/` concentram configuração e contratos reutilizados pelos workloads. Os notebooks em `notebooks/_eda/` complementam a validação com investigação e reconciliação orientadas por evidência, mas não integram o DAG produtivo.

Quando evidência legítima contradiz uma hipótese anterior, o contrato afetado deve ser revisto conscientemente; dados não são transformados ou descartados silenciosamente apenas para fazer uma validação passar.

## 5. Materialização, reexecução e recuperação

Bronze, Silver e Gold são materializadas como tabelas Delta e seguem uma estratégia compatível com reconstrução integral do estado derivado a partir da entrada disponível.

```text
raw inalterado → execução integral → reexecução integral → mesmas cardinalidades nas 17 tabelas
```

A validação em uma segunda fundação Databricks confirmou que as 2 tabelas Bronze, 8 Silver e 7 Gold mantiveram suas cardinalidades após reexecuções completas com a mesma entrada raw.

Essa evidência sustenta a reexecução do cenário testado; não constitui garantia universal de determinismo para qualquer alteração de dados, runtime ou condição operacional.

Como as materializações são independentes, falhas parciais podem deixar uma camada temporariamente inconsistente. A recuperação não depende de rollback distribuído: a falha é diagnosticada e, depois de corrigida, o workload é executado novamente.

## 6. Unity Catalog e governança

A organização lógica consumida pela aplicação é:

```text
<catalogo-do-ambiente>
├── bronze
│   ├── Volume: raw
│   ├── credits
│   └── movies
├── silver
│   └── 8 tabelas normalizadas
└── gold
    └── 7 produtos analíticos
```

O catálogo físico varia entre ambientes e não é codificado no processamento. Os nomes lógicos versionados são:

```text
bronze_schema = bronze
silver_schema = silver
gold_schema   = gold
raw_volume    = raw
```

A identidade utilizada para executar o workload deve possuir os privilégios necessários sobre os objetos do Unity Catalog consumidos pela aplicação. Esses privilégios são configurados durante a preparação do ambiente, antes da execução do workload, conforme descrito na seção de fronteira entre infraestrutura e aplicação.

A aplicação consome essas permissões, mas não as concede nem as amplia durante sua execução. Se um privilégio necessário estiver ausente, a condição deve ser diagnosticada e corrigida na preparação do ambiente; notebooks, Lakeflow Job e Bundle não executam `GRANT`, não alteram ownership e não criam mecanismos de acesso ao storage como forma de autocorreção.

## 7. Orquestração com Lakeflow Jobs

A execução produtiva é representada pelo Lakeflow Job `movie_lakehouse_job`:

```text
bronze_ingestion → silver_transformation → gold_build
```

Cada task recebe somente os parâmetros necessários à sua camada. Silver depende do sucesso de Bronze e Gold depende do sucesso de Silver; falhas upstream impedem a execução normal das tasks downstream.

A estratégia de repair do Job é compatível com a capacidade de reexecução das materializações, mas o orquestrador não torna o processamento idempotente por si próprio. Essa propriedade depende da implementação das tasks.

Notebooks de EDA e ferramentas administrativas de preparação da infraestrutura não fazem parte do DAG.

## 8. Configuração e ambientes

O Bundle implementa atualmente um único target lógico: `dev`. Ele representa configuração lógica da aplicação, não um workspace físico específico.

A configuração lógica versionada mantém:

```text
bronze_schema = bronze
silver_schema = silver
gold_schema   = gold
raw_volume    = raw
```

O contexto físico é fornecido externamente:

```text
DATABRICKS_CONFIG_PROFILE
BUNDLE_VAR_catalog
```

Na execução local, `DATABRICKS_CONFIG_PROFILE` seleciona autenticação/workspace da Databricks CLI e `BUNDLE_VAR_catalog` fornece o catálogo físico.

No GitHub Actions não há profile local: o contexto é fornecido por variáveis do repositório e autenticação OIDC.

Essa separação foi validada ao implantar a mesma aplicação em uma segunda fundação Databricks sem criar outro target apenas para representar outro workspace. Targets como `test` ou `prod` não são declarados como implementados.

## 9. Deployment declarativo

A estratégia de deployment utiliza Databricks Declarative Automation Bundles.

```text
databricks.yml
resources/movie_lakehouse_job.yml
```

`databricks.yml` define Bundle, variáveis e target lógico;
`resources/movie_lakehouse_job.yml` declara o Lakeflow Job e suas tasks.

O Bundle declara recursos pertencentes ao workload. Catálogo, schemas, Volume, storage, identidades e permissões são pré-requisitos externos e não são incorporados ao Bundle apenas para tornar o deployment aparentemente autocontido.

Operação local e CI/CD consomem a mesma estratégia declarativa.

## 10. CI/CD e identidade

O CI/CD é implementado com GitHub Actions.

Em Pull Requests para `main`, o CI faz checkout, configura a Databricks CLI e valida o Bundle.

Em `push` para `main` ou execução manual, o CD executa:

```text
checkout → configura CLI → bundle validate → bundle deploy → bundle run
```

A identidade técnica utiliza GitHub OIDC para autenticação no Azure Databricks, sem depender de PAT ou OAuth client secret armazenados no repositório.

O contexto físico da automação é fornecido externamente:

```text
DATABRICKS_HOST
DATABRICKS_CLIENT_ID
DATABRICKS_CATALOG
```

`DATABRICKS_CATALOG` alimenta `BUNDLE_VAR_catalog`.

A associação da identidade ao workspace e os privilégios no Unity Catalog são preparados externamente. Os workflows apenas consomem essa identidade.

## 11. Observabilidade, troubleshooting e performance

A observabilidade utiliza sinais da execução do Lakeflow Job e os artefatos de validação do projeto.

A investigação de falhas segue:

```text
inspeção → hipótese → evidência → correção → revalidação
```

O projeto não altera arquitetura, contratos ou regras de qualidade apenas para fazer uma execução passar.

Durante a validação de performance, o pipeline completo apresentou tempo de execução da ordem de poucos minutos no volume atual e em compute serverless. Não foi identificado gargalo relevante que justificasse otimização artificial.

Esse baseline é contextual ao dataset, plataforma e condições observadas; não representa SLA nem garantia de performance futura.

Procedimentos e comandos operacionais ficam em [`runbook.md`](runbook.md).

## 12. Decisões e limitações arquiteturais

As principais decisões e limitações atuais são:

- os arquivos TMDB são tratados como snapshots completos;
- o pipeline produtivo é batch;
- Bronze, Silver e Gold utilizam materializações independentes;
- não existe transação distribuída entre todas as tabelas de uma camada;
- a recuperação validada para falha parcial é diagnóstico seguido de reexecução;
- somente o target lógico `dev` está implementado;
- a aplicação depende de uma fundação Azure Databricks previamente preparada;
- identidade, storage, governança e permissões são externos ao workload;
- `_eda` contém investigação e validação, não etapas produtivas;
- não foram introduzidas otimizações sem gargalo medido;
- machine learning, recomendação, análise de sentimento e processamento em tempo real não fazem parte do escopo atual.

A evolução dessas decisões deve ser sustentada por necessidade do produto ou evidência operacional.

## 13. Fontes executáveis de verdade

Este documento explica a arquitetura, mas não substitui os artefatos versionados que implementam o sistema:

```text
databricks.yml
resources/movie_lakehouse_job.yml
notebooks/_shared/configuration.py
notebooks/_shared/contracts.py
notebooks/01_bronze/ingest_raw.ipynb
notebooks/02_silver/transform_silver.ipynb
notebooks/03_gold/build_gold.ipynb
.github/workflows/ci.yml
.github/workflows/cd.yml
scripts/validate_bundle_prerequisites.sh
scripts/validate_platform_contract.sh
scripts/provision_platform_prerequisites.sh
```

A documentação descreve decisões e comportamento validado; os artefatos executáveis permanecem a referência para detalhes concretos de implementação.
