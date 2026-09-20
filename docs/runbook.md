# Runbook operacional do movie-lakehouse-2.0

Este documento descreve como preparar o contexto de execução, validar pré-requisitos, implantar, executar, diagnosticar e remover com segurança os recursos do `movie-lakehouse-2.0`.

O runbook pressupõe que a fundação Azure Databricks já exista. A aplicação consome essa fundação; ela não a administra durante o processamento.

## 1. Pré-requisitos

Antes da execução, devem estar disponíveis:

-   um workspace Azure Databricks acessível pela identidade utilizada;
-   Unity Catalog habilitado e um catálogo destinado ao workload;
-   schemas `bronze`, `silver` e `gold`;
-   Volume `bronze.raw`;
-   os arquivos `tmdb_5000_movies.csv` e `tmdb_5000_credits.csv` no Volume raw;
-   Databricks CLI compatível com Declarative Automation Bundles;
-   privilégios necessários para a identidade que executará o workload.

O projeto complementar [`databricks-infra-bootstrap`](https://github.com/luisconcha/databricks-infra-bootstrap) pode ser utilizado para preparar a fundação Azure/Databricks. A configuração funcional necessária especificamente ao workload deve ser validada antes da execução.

## 2. Privilégios do workload

No cenário validado pelo projeto, a identidade técnica utilizada pelo CI/CD recebeu os seguintes privilégios:

``` text
<catalogo>
└── USE CATALOG

<catalogo>.bronze
├── USE SCHEMA
├── SELECT
├── MODIFY
└── CREATE TABLE

<catalogo>.bronze.raw
└── READ VOLUME

<catalogo>.silver
├── USE SCHEMA
├── SELECT
├── MODIFY
└── CREATE TABLE

<catalogo>.gold
├── USE SCHEMA
├── SELECT
├── MODIFY
└── CREATE TABLE
```

Esses grants são preparados antes da execução do workload. Notebooks, Lakeflow Job e Bundle não executam `GRANT` nem ampliam seus próprios privilégios.

A lista representa o conjunto comprovado para este projeto e não deve ser tratada como conjunto universal de permissões para qualquer workload
Databricks.

## 3. Contexto local

Execute os comandos a partir da raiz do repositório, onde está `databricks.yml`.

Confirme primeiro a CLI:

``` bash
databricks --version
```

Na operação local, o workspace e o catálogo físico do ambiente são fornecidos explicitamente no contexto de cada comando:
``` bash
DATABRICKS_CONFIG_PROFILE=<profile-do-workspace> \
BUNDLE_VAR_catalog=<catalogo-do-ambiente> \
databricks bundle validate -t dev
```

O target lógico implementado pelo projeto é:

``` text
dev
```

Os nomes lógicos versionados são:

``` text
bronze_schema = bronze
silver_schema = silver
gold_schema   = gold
raw_volume    = raw
```

O profile local e o catálogo físico não devem ser codificados nos notebooks ou workflows.

## 4. Validar configuração do Bundle

Execute:

``` bash
./scripts/validate_bundle_prerequisites.sh
```

O script verifica o contexto mínimo necessário para trabalhar com o Bundle e executa a validação do target `dev`.

A validação também pode ser executada diretamente:

``` bash
databricks bundle validate -t dev
```

Para inspecionar a configuração resolvida em JSON:

``` bash
databricks bundle validate -t dev --output json
```

Uma falha nesta etapa deve ser diagnosticada antes do deployment.

## 5. Validar pré-requisitos externos

Execute:

``` bash
./scripts/validate_platform_contract.sh
```

O validador resolve a configuração do Bundle e verifica, sem corrigir automaticamente o ambiente:

-   existência do catálogo;
-   existência dos schemas `bronze`, `silver` e `gold`;
-   existência do Volume raw;
-   presença dos dois CSVs;
-   capacidade de leitura dos arquivos.

O sucesso desse script indica que os pré-requisitos que ele verifica estão disponíveis para o contexto utilizado.

Se a validação falhar, identifique primeiro qual condição está ausente. Não altere notebooks, contratos ou regras de qualidade para contornar uma falha de preparação do ambiente.

## 6. Preparação auxiliar de schemas

O repositório contém:

``` text
scripts/provision_platform_prerequisites.sh
```

Esse script é uma ferramenta administrativa auxiliar e **não faz parte do DAG produtivo**.

Ele pode ser executado explicitamente pelo responsável pela preparação do ambiente quando a validação comprovar que os schemas esperados estão ausentes:

``` bash
./scripts/provision_platform_prerequisites.sh
```

O script trata somente os schemas previstos por sua implementação e não concede grants nem altera ownership.

Após qualquer preparação do ambiente, execute novamente:

``` bash
./scripts/validate_platform_contract.sh
```

A aplicação não chama esse provisionador como mecanismo de autocorreção.

## 7. Deployment

Com as validações concluídas:

``` bash
databricks bundle deploy -t dev
```

O deployment utiliza:

``` text
databricks.yml
resources/movie_lakehouse_job.yml
```

e implanta os recursos pertencentes ao Bundle no workspace selecionado pelo contexto de autenticação.

Catálogo, schemas, Volume, arquivos raw e grants não são criados pelo deployment normal do workload.

## 8. Execução

Para executar o pipeline completo:

``` bash
databricks bundle run -t dev movie_lakehouse_job
```

O DAG produtivo é:

``` text
bronze_ingestion
        ↓
silver_transformation
        ↓
    gold_build
```

A execução deve respeitar a propagação de falhas entre as tasks. Se uma task upstream falhar, investigue a causa antes de forçar uma continuação downstream.

Os notebooks em `notebooks/_eda/` não fazem parte da execução produtiva.

## 9. Inspeção e reexecução

O histórico e os detalhes das execuções podem ser inspecionados pela interface de Lakeflow Jobs no workspace.

Para o cenário validado neste projeto, uma reexecução integral com os arquivos raw inalterados manteve as cardinalidades das 17 tabelas materializadas:

``` text
2 Bronze + 8 Silver + 7 Gold
```

Essa evidência sustenta a reexecução do cenário testado; não é uma garantia universal de determinismo.

Em caso de falha parcial, siga:

``` text
inspeção → hipótese → evidência → correção → revalidação
```

Depois de corrigir a causa, a estratégia comprovada é executar novamente o workload. As materializações entre tabelas são independentes e não existe rollback transacional global entre todas elas.

## 10. CI/CD

Os workflows estão em:

``` text
.github/workflows/ci.yml
.github/workflows/cd.yml
```

### CI

O CI é executado em Pull Requests para `main` e valida o Bundle.

Fluxo:

``` text
checkout → Databricks CLI → bundle validate
```

### CD

O CD é executado em `push` para `main` ou manualmente.

Fluxo:

``` text
checkout → Databricks CLI → bundle validate → bundle deploy → bundle run
```

A autenticação utiliza GitHub OIDC e uma identidade técnica no Databricks, sem PAT ou OAuth client secret versionados no repositório.

As variáveis utilizadas pelo workflow são:

``` text
DATABRICKS_HOST
DATABRICKS_CLIENT_ID
DATABRICKS_CATALOG
```

`DATABRICKS_CATALOG` é fornecido ao Bundle como `BUNDLE_VAR_catalog`.

A federação OIDC, associação da identidade ao workspace e grants necessários precisam estar preparados no ambiente antes da execução dos workflows.

Os arquivos YAML versionados são a fonte de verdade para triggers, permissões do workflow e sequência exata das ações.

## 11. Troubleshooting

### Bundle não encontra autenticação ou workspace

Inspecione:

``` bash
echo "$DATABRICKS_CONFIG_PROFILE"
databricks --version
```

Confirme que o profile selecionado corresponde ao workspace pretendido e que a autenticação está válida.

Depois execute novamente:

``` bash
databricks bundle validate -t dev
```

### Catálogo, schema ou Volume ausente

Execute:

``` bash
./scripts/validate_platform_contract.sh
```

Use a mensagem do validador para identificar o objeto ausente.

Se forem schemas previstos pelo script auxiliar, o responsável pela preparação do ambiente pode executar:

``` bash
./scripts/provision_platform_prerequisites.sh
./scripts/validate_platform_contract.sh
```

Para catálogo, Volume, storage, identidade ou permissões, corrija a preparação do ambiente pelo mecanismo administrativo apropriado; não introduza autocorreção no workload.

### Arquivos raw ausentes ou ilegíveis

O Volume deve conter:

``` text
tmdb_5000_movies.csv
tmdb_5000_credits.csv
```

Execute o validador para comprovar presença e leitura:

``` bash
./scripts/validate_platform_contract.sh
```

Não substitua silenciosamente a fonte nem altere o pipeline para aceitar um arquivo diferente.

### Erro de permissão

Compare a identidade em uso com os privilégios descritos na seção **Privilégios do workload**.

Se algum privilégio necessário estiver ausente, configure o grant correspondente no Unity Catalog antes de reexecutar o workload e valide novamente o acesso.

A concessão desses privilégios faz parte da preparação do ambiente para receber a aplicação e pode ser realizada pelo engenheiro responsável pelo deployment. Ela permanece, porém, separada da execução do workload: notebooks, Lakeflow Job e Bundle não executam `GRANT` nem ampliam suas próprias permissões durante o processamento.

### Falha em uma task do Job

Identifique:

1.  qual task falhou;
2.  a mensagem e o contexto do erro;
3.  se a falha é de dados, código, configuração ou ambiente;
4.  a menor correção compatível com a arquitetura.

Depois da correção:

``` bash
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run -t dev movie_lakehouse_job
```

Use somente os comandos necessários ao tipo de mudança. Uma falha de dados ou pré-requisito externo não implica automaticamente novo deployment.

### CI/CD falha na autenticação OIDC

Verifique:

-   `DATABRICKS_HOST`;
-   `DATABRICKS_CLIENT_ID`;
-   configuração de federação da identidade;
-   associação da identidade ao workspace;
-   correspondência entre o subject emitido pelo GitHub e a política de
    federação configurada.

Não substitua OIDC por segredo permanente apenas para fazer o pipeline passar.

## 12. Remoção segura

A remoção completa do `movie-lakehouse-2.0` não foi executada como parte das validações realizadas até o momento. Portanto, este projeto não apresenta um procedimento de teardown como comportamento operacional comprovado.

A separação de responsabilidades da arquitetura estabelece, entretanto, uma fronteira importante para qualquer remoção futura:

- recursos implantados pelo Bundle pertencem ao workload e podem ser considerados no teardown da aplicação;
- catálogo, schemas, Volume raw, arquivos de origem, identidade, grants, storage e demais recursos da fundação não devem ser removidos implicitamente como consequência da remoção do workload;
- a desmontagem da fundação Azure/Databricks deve seguir o processo do mecanismo responsável por seu provisionamento.

O Databricks CLI disponibiliza `databricks bundle destroy` para destruir recursos previamente implantados por um Bundle. Esse comando não foi executado e validado neste projeto e, por isso, não é apresentado aqui como procedimento operacional comprovado.

Antes de realizar qualquer teardown, devem ser identificados explicitamente os recursos pertencentes ao Bundle e os recursos externos compartilhados que precisam ser preservados.

## 13. Checklist operacional

Antes de uma execução ou implantação relevante:

``` text
[ ] workspace/contexto correto
[ ] catálogo físico informado
[ ] Bundle validado
[ ] catálogo, schemas e Volume disponíveis
[ ] dois CSVs presentes e legíveis
[ ] identidade com privilégios necessários
[ ] deployment realizado quando necessário
[ ] Job executado
[ ] resultado inspecionado
```

Para detalhes arquiteturais, consulte [`architecture.md`](architecture.md). Para a evolução técnica e as decisões permanentes do desenvolvimento, consulte [`project-history.md`](project-history.md).
