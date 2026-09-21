# Histórico técnico do movie-lakehouse-2.0

## Propósito

Este documento preserva a evolução técnica relevante do `movie-lakehouse-2.0`: decisões que moldaram a arquitetura, evidências que confirmaram ou alteraram hipóteses, problemas encontrados durante a construção e o resultado obtido.

Ele não é um diário de execução nem uma transcrição de commits. Detalhes experimentais temporários foram mantidos durante o desenvolvimento apenas enquanto necessários à investigação. Aqui permanecem os aprendizados que ajudam a compreender e defender o estado atual do projeto.

## 1. Do legado para uma nova implementação

O projeto nasceu como uma reconstrução consciente de um lakehouse de filmes, e não como uma migração automática da implementação anterior.

A versão legada foi utilizada como evidência histórica. Arquitetura, contratos, produtos Gold e mecanismos operacionais foram reavaliados a partir das fontes reais e dos objetivos do novo produto.

Desde o início, três decisões orientaram a construção:

- arquitetura medalhão Bronze → Silver → Gold;
- Unity Catalog como fronteira de organização e governança dos dados;
- separação entre a fundação Azure Databricks e o workload de engenharia de dados.

A estrutura versionada nasceu em um novo repositório Git e foi disponibilizada no workspace por Git Folder. Código produtivo, investigação `_eda`, componentes `_shared`, recursos de deployment, scripts operacionais e CI/CD permaneceram separados.

## 2. Caracterização das fontes e contratos iniciais

As fontes aprovadas foram:

```text
tmdb_5000_movies.csv
tmdb_5000_credits.csv
```

Antes da implementação produtiva, os arquivos foram caracterizados quanto a estrutura, schema observado, cardinalidade, chaves, nulidade, duplicidade, estruturas semiestruturadas e relacionamento entre movies e credits.

Essa investigação mostrou que diversos atributos do dataset estavam representados como estruturas serializadas dentro dos CSVs. Em vez de ocultar essa característica com inferência automática, os contratos iniciais explicitaram como Bronze preservaria a origem e como Silver faria parsing, tipagem e normalização.

Os contratos foram tratados como hipóteses verificáveis, não como especificações imutáveis. Evidências posteriores de Bronze, Silver e Gold poderiam justificar revisão controlada.

## 3. Bronze: fidelidade, rastreabilidade e snapshot

A ingestão Bronze materializou duas tabelas Delta:

```text
bronze.movies
bronze.credits
```

A leitura passou a utilizar schema explícito e validação da estrutura esperada dos arquivos. Os campos raw relevantes foram preservados e a ingestão recebeu metadados de rastreabilidade, incluindo arquivo de origem, instante de ingestão e identificador da execução.

A validação observou 4.803 registros em cada fonte, sem IDs nulos, com 4.803 IDs distintos em cada arquivo e correspondência integral entre movies e credits no dataset utilizado.

### Decisão sobre reexecução

As fontes foram tratadas como snapshots completos. A estratégia escolhida foi `overwrite`, não append.

A reexecução com a mesma entrada manteve 4.803 registros em cada tabela, sem acumulação de linhas. Cada execução, entretanto, representa uma nova ingestão e possui seus próprios metadados.

Também foi testado o comportamento de falha parcial. Como `movies` e `credits` são escritos independentemente, não existe atomicidade conjunta entre as duas materializações. A recuperação definida foi:

```text
diagnosticar → corrigir → reexecutar integralmente
```

Essa constatação tornou explícito um limite arquitetural que permanece válido nas camadas posteriores: overwrite facilita convergência, mas não cria uma transação distribuída entre tabelas independentes.

## 4. Silver: normalização orientada pelo domínio

A Silver transformou as estruturas raw em oito relações:

```text
silver.movie
silver.movie_genre
silver.movie_keyword
silver.movie_production_company
silver.movie_production_country
silver.movie_spoken_language
silver.cast_credit
silver.crew_credit
```

Arrays e estruturas serializadas foram parseados e normalizados. As validações cobriram tipos, campos obrigatórios, unicidade das chaves contratuais, integridade referencial por `movie_id` e perdas durante conversões.

Não foram observadas violações nas regras críticas validadas.

### Falha parcial e recuperação

Um teste controlado, preservado em `notebooks/_eda/03_silver_modeling_validation.ipynb`, simulou uma falha durante a materialização da Silver.

A investigação, registrada no **Step 9 — Estratégia de materialização e recuperação da Silver**, confirmou que uma falha parcial pode deixar tabelas já concluídas persistidas, sem rollback automático das materializações anteriores.

Na sequência, o **Step 9.3 — Reexecução integral após falha parcial** comprovou que a reexecução completa com `overwrite` convergiu novamente para o baseline das oito entidades Silver.

Com base nessa evidência, o comportamento operacional adotado permaneceu fail-fast, seguido de diagnóstico, correção da causa e reexecução integral da Silver.

### Pré-requisito de ambiente descoberto durante a Silver

Durante a implementação da Silver, a ausência do schema `silver` em um ambiente expôs uma fronteira operacional importante: o workload não deveria criar silenciosamente a infraestrutura que esperava consumir.

A partir dessa evidência foram consolidados dois scripts com responsabilidades distintas:

- `scripts/validate_platform_contract.sh` - valida de forma não destrutiva os pré-requisitos externos consumidos pela aplicação, incluindo catálogo, schemas, Volume raw, presença dos arquivos de origem e capacidade de leitura;
- `scripts/provision_platform_prerequisites.sh` - ferramenta auxiliar utilizada explicitamente durante a preparação do ambiente para criar os schemas esperados pela aplicação quando estiverem ausentes.

O primeiro script apenas inspeciona e comprova o estado do ambiente; ele não cria nem corrige recursos.

O segundo pode criar os schemas `bronze`, `silver` e `gold` ausentes, mas sua execução é uma ação explícita de preparação do ambiente e não faz parte do processamento produtivo.

Nenhum dos dois mecanismos concede `GRANT`, altera ownership ou cria mecanismos de acesso ao storage. O script de provisionamento auxiliar também não integra o DAG do Lakeflow Job.

### Consistência da materialização

A escrita Delta já era o comportamento utilizado pelo projeto, mas a Silver foi posteriormente ajustada para declarar `.format("delta")` explicitamente, alinhando a intenção do código entre Bronze, Silver e Gold. A alteração foi revalidada downstream.

## 5. Gold: produtos analíticos e semântica de negócio

A modelagem Gold foi reconciliada com as evidências da Silver antes da implementação final.

Foram materializados sete produtos:

```text
gold.movie_performance
gold.movie_genre_performance
gold.movie_credit_participation
gold.movie_company_performance
gold.movie_country_performance
gold.movie_language_profile
gold.movie_keyword_performance
```

Entre as decisões de negócio consolidadas:

- `release_year` deriva de `release_date`;
- métricas comerciais são elegíveis quando `budget > 0`;
- `profit = revenue - budget` para registros elegíveis;
- `roi = (revenue - budget) / budget` para registros elegíveis;
- `profit` e `roi` permanecem nulos quando `budget <= 0`;
- `budget > 0` com `revenue = 0` continua sendo observação elegível e pode produzir resultado negativo;
- participação diferencia `cast` de `crew`;
- perfil de idiomas diferencia idioma original de idioma falado.

Os produtos derivados de associações N:N preservam seu grão. Agregações automáticas não foram introduzidas durante a construção porque poderiam criar dupla contagem de métricas de filmes.

A validação Gold cobriu cardinalidade, unicidade do grão, estrutura, regras de negócio, métricas críticas e capacidade de responder aos casos analíticos previstos.

## 6. Qualidade end-to-end e troubleshooting

A qualidade foi distribuída pelos pontos do fluxo onde cada regra pode ser verificada com maior clareza. As validações end-to-end foram usadas para fechar lacunas, não para duplicar gratuitamente checks já comprovados localmente.

O procedimento de troubleshooting consolidado foi:

```text
inspeção → hipótese → evidência → correção → revalidação
```

Um exemplo importante ocorreu durante a primeira execução integrada do Lakeflow Job. O workload falhou com `ModuleNotFoundError` ao tentar importar os módulos compartilhados do diretório `notebooks/_shared`.

A investigação foi realizada no próprio contexto de execução dos notebooks produtivos do Job. Instrumentação temporária foi adicionada para inspecionar o diretório de trabalho e o `sys.path` disponíveis durante a execução no Databricks.

A evidência mostrou que o caminho necessário para resolver o pacote `notebooks` não estava disponível no contexto em que os notebooks produtivos eram executados pelo Job.

A correção mínima aplicada aos notebooks produtivos foi incluir explicitamente a raiz necessária no `sys.path`:

```python
import os
import sys

sys.path.append(os.path.abspath("../.."))
```

Após a correção, o Lakeflow Job foi reexecutado com sucesso. A instrumentação utilizada exclusivamente para o diagnóstico foi então removida, permanecendo no código produtivo apenas o ajuste necessário para a resolução dos módulos compartilhados.

Esse episódio consolidou uma regra operacional do projeto: instrumentação temporária pode ser introduzida no próprio contexto onde a falha ocorre para produzir evidência diagnóstica, mas deve ser removida depois que a causa estiver compreendida e a correção tiver sido revalidada.

## 7. Performance: medir antes de otimizar

O pipeline integrado foi medido em compute serverless com o volume atual do TMDB 5000.

A execução completa ficou aproximadamente na faixa de 2 minutos e 12 / 13 segundos nas medições utilizadas como baseline, com Bronze, Silver e Gold consumindo dezenas de segundos cada.

Nenhum gargalo relevante foi identificado que justificasse uma otimização específica. Por isso, não foram introduzidos particionamento, clustering ou outras otimizações apenas para demonstrar recursos da plataforma.

A ausência de mudança foi uma decisão baseada em evidência: otimização sem problema medido aumentaria complexidade sem benefício comprovado.

O baseline é contextual ao dataset, runtime e condições observadas e não constitui SLA.

## 8. Orquestração produtiva

O pipeline foi formalizado como Lakeflow Job:

```text
bronze_ingestion
        ↓
silver_transformation
        ↓
    gold_build
```

As dependências foram declaradas explicitamente. Um teste de falha upstream confirmou que tasks downstream não prosseguem normalmente quando sua dependência falha.

Também foi validado o uso de repair run. O comportamento reforçou que o orquestrador controla dependências e reexecução operacional, mas não fornece idempotência automaticamente: a segurança da reexecução depende da implementação das tasks.

Notebooks `_eda` e mecanismos de preparação do ambiente permaneceram fora do DAG.

## 9. Deployment declarativo com Bundles

A estratégia de deployment foi estabelecida cedo com Databricks Declarative Automation Bundles e posteriormente completada com o Job produtivo.

Os artefatos centrais passaram a ser:

```text
databricks.yml
resources/movie_lakehouse_job.yml
```

Somente recursos pertencentes ao workload são declarados pelo Bundle.
Catálogo, schemas, Volume, storage, identidade e permissões permanecem como condições que precisam existir para a aplicação operar.

A validação do estado declarativo e deployments repetidos mostraram convergência do recurso do Job sem necessidade de reconstrução manual no workspace.

Apenas o target lógico `dev` foi implementado e comprovado. Targets adicionais não foram criados apenas para simular maturidade de ambientes ainda inexistentes.

## 10. CI/CD sem credencial permanente

O CI/CD foi implementado com GitHub Actions utilizando a mesma estratégia declarativa do desenvolvimento local.

O CI valida o Bundle em Pull Requests para `main`. O CD, em `push` para `main` ou execução manual, valida, implanta e executa o Job.

A autenticação utiliza GitHub OIDC com uma identidade técnica no Databricks, sem PAT ou OAuth client secret versionados.

### Problemas que se tornaram conhecimento operacional

Durante a configuração do CI/CD, duas falhas foram particularmente úteis:

- um Application/Client ID incorreto produziu falha de autenticação;
- uma divergência entre o `subject` emitido pelo GitHub e o `subject` esperado pela política de federação produziu rejeição do token.

As correções foram realizadas na configuração da identidade e da federação, sem introduzir PAT, OAuth client secret ou outra credencial permanente como atalho.

Além da autenticação, foi necessário preparar a autorização da identidade técnica utilizada pelo CI/CD. Como parte da preparação de cada ambiente para receber a aplicação, foram concedidos explicitamente no Unity Catalog os privilégios mínimos necessários ao workload.

No cenário validado, foram configurados:

- `USE CATALOG` no catálogo utilizado pela aplicação;
- `USE SCHEMA`, `SELECT`, `MODIFY` e `CREATE TABLE` nos schemas `bronze`, `silver` e `gold`;
- `READ VOLUME` no Volume `bronze.raw`.

Esses grants foram configurados externamente à execução do workload pelo engenheiro responsável pela preparação do ambiente. Eles não são concedidos automaticamente pelo `databricks-infra-bootstrap`, pelo Databricks Asset Bundle ou pelo Lakeflow Job.

Depois de configurados, a identidade técnica consome esses privilégios para validar, implantar e executar a aplicação. Os notebooks produtivos, o Lakeflow Job e o Bundle não executam `GRANT`, não alteram ownership e não ampliam suas próprias permissões durante o processamento.

Essa separação foi reproduzida na segunda fundação utilizada para validar a portabilidade do projeto: a identidade foi associada ao novo workspace e os privilégios necessários ao workload foram configurados para os objetos daquele ambiente antes da execução do pipeline.

## 11. Reprodutibilidade em uma segunda fundação

A validação de reprodutibilidade foi deliberadamente realizada sobre uma segunda fundação Azure Databricks, em vez de depender apenas do workspace que acumulava o histórico de desenvolvimento.

Esse teste revelou acoplamentos físicos que ainda estavam escondidos na configuração:

- workspace fixado no Bundle;
- catálogo físico fixado;
- dependência de profile local específico.

A primeira tentativa de validação no novo ambiente falhou porque a configuração ainda carregava referências físicas associadas ao ambiente anterior. Essa falha foi tratada como evidência de acoplamento e motivou a correção da configuração, em vez de renovar artificialmente o acesso ao ambiente antigo apenas para fazer a validação passar.

### Externalização da configuração física

A correção foi aplicada aos artefatos versionados responsáveis pela configuração, validação e automação da aplicação.

No `databricks.yml`, referências físicas de workspace e catálogo deixaram de ser fixadas no Bundle. O target `dev` permaneceu como configuração lógica versionada, contendo os nomes estáveis utilizados pela aplicação:

```text
bronze_schema = bronze
silver_schema = silver
gold_schema   = gold
raw_volume    = raw
```

O catálogo físico passou a ser fornecido externamente por:

```text
BUNDLE_VAR_catalog
```

Na execução local, o workspace e o contexto de autenticação passaram a ser selecionados por:

```text
DATABRICKS_CONFIG_PROFILE
```

Essas variáveis são fornecidas no contexto de cada comando, por exemplo:

```bash
DATABRICKS_CONFIG_PROFILE=<profile-do-workspace> \
BUNDLE_VAR_catalog=<catalogo-do-ambiente> \
databricks bundle validate -t dev
```

Os scripts `scripts/validate_bundle_prerequisites.sh`, `scripts/validate_platform_contract.sh` e `scripts/provision_platform_prerequisites.sh` foram alinhados ao mesmo modelo, consumindo o contexto físico fornecido externamente em vez de depender de um workspace ou catálogo específico codificado no repositório.

Nos workflows `.github/workflows/ci.yml` e `.github/workflows/cd.yml`, o contexto físico passou a ser fornecido pelas variáveis configuradas no repositório GitHub:

```text
DATABRICKS_HOST
DATABRICKS_CLIENT_ID
DATABRICKS_CATALOG
```

`DATABRICKS_CATALOG` alimenta `BUNDLE_VAR_catalog`, enquanto `DATABRICKS_HOST` e `DATABRICKS_CLIENT_ID` definem o workspace e a identidade utilizados pela autenticação OIDC do GitHub Actions.

Com essa reorganização, a separação ficou explícita:

```text
Configuração lógica versionada
└── databricks.yml
    └── target dev
        ├── bronze_schema = bronze
        ├── silver_schema = silver
        ├── gold_schema   = gold
        └── raw_volume    = raw

Execução local
├── DATABRICKS_CONFIG_PROFILE
└── BUNDLE_VAR_catalog

GitHub Actions
├── DATABRICKS_HOST
├── DATABRICKS_CLIENT_ID
└── DATABRICKS_CATALOG → BUNDLE_VAR_catalog
```

A partir dessa alteração, o mesmo conjunto de artefatos versionados pôde ser utilizado contra a segunda fundação sem codificar no projeto os identificadores físicos daquele ambiente.

### Resultado

A aplicação foi implantada a partir dos artefatos versionados, o Job executou com sucesso e novas execuções completas com os mesmos arquivos raw mantiveram as cardinalidades das 17 tabelas:

```text
2 Bronze
8 Silver
7 Gold
```

O CI e o CD também foram revalidados nesse contexto.

A conclusão é propositalmente limitada: para a entrada raw inalterada e nas condições testadas, a aplicação pôde ser implantada e reexecutada em outra fundação compatível sem crescimento das cardinalidades. Isso não é uma alegação de determinismo universal.

## 12. Estado técnico resultante

Ao final desta evolução, o `movie-lakehouse-2.0` passou a possuir:

- ingestão Bronze com contrato explícito e rastreabilidade;
- Silver normalizada e validada;
- sete produtos Gold com semântica documentada;
- qualidade distribuída pelas camadas e validação end-to-end;
- procedimento de troubleshooting baseado em evidência;
- baseline de performance sem otimização artificial;
- Lakeflow Job produtivo;
- deployment declarativo com Bundle;
- CI/CD com GitHub Actions e OIDC;
- configuração física desacoplada do código produtivo;
- validação de reexecução e reprodução em uma segunda fundação Databricks;
- documentação arquitetural e operacional coerente com o comportamento comprovado.

O projeto não busca demonstrar todos os recursos disponíveis no Databricks. Seu estado atual reflete somente componentes que resolveram necessidades reais observadas durante a construção.

## 13. Limites que permanecem explícitos

Alguns limites são intencionais e fazem parte da defesa técnica da
solução:

- apenas o target lógico `dev` foi implementado;
- as fontes são tratadas como snapshots batch;
- não existe atomicidade global entre materializações independentes;
- o baseline de performance não é um SLA;
- a estabilidade de cardinalidade observada não garante determinismo universal;
- teardown completo da aplicação não foi executado como validação do projeto;
- a fundação Azure/Databricks e os mecanismos de acesso permanecem separados do workload;
- machine learning, recomendação, análise de sentimento e processamento em tempo real não foram adicionados sem necessidade do produto.

Esses limites são documentados para evitar que evidência específica seja apresentada como capacidade mais ampla do que aquela efetivamente comprovada.

---

Para a arquitetura atual, consulte [`architecture.md`](architecture.md). Para operação, deployment e troubleshooting, consulte [`runbook.md`](runbook.md). O [`README.md`](../README.md) permanece como ponto de entrada do projeto.
