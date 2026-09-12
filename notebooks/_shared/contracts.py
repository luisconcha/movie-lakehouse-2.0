""" Contratos estruturais de dados do movie-lakehouse-2.0 """

from dataclasses import dataclass

from pyspark.sql.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


@dataclass(frozen=True)
class DataContract:
    """descrição estrutural de uma relação/produto de dados"""

    name: str
    grain: str
    key: tuple[str, ...]
    schema: StructType


# --------------------------------------------------
# Bronze
# --------------------------------------------------

BRONZE_MOVIES_SOURCE_FIELDS = (
    "budget",
    "genres",
    "homepage",
    "id",
    "keywords",
    "original_language",
    "original_title",
    "overview",
    "popularity",
    "production_companies",
    "production_countries",
    "release_date",
    "revenue",
    "runtime",
    "spoken_languages",
    "status",
    "tagline",
    "title",
    "vote_average",
    "vote_count",
)

BRONZE_CREDITS_SOURCE_FIELDS = (
    "movie_id",
    "title",
    "cast",
    "crew",
)


def _bronze_schema(source_fields: tuple[str, ...]) -> StructType:
    """monta schema Bronze preservando campos de origem como STRING"""

    return StructType(
        [
            *[
                StructField(field_name, StringType(), nullable=True)
                for field_name in source_fields
            ],
            StructField("_source_file", StringType(), nullable=False),
            StructField("_ingested_at", TimestampType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    )


BRONZE_MOVIES = DataContract(
    name="movies",
    grain="uma linha recebida da fonte movies",
    key=("id",),
    schema=_bronze_schema(BRONZE_MOVIES_SOURCE_FIELDS),
)

BRONZE_CREDITS = DataContract(
    name="credits",
    grain="uma linha recebida da fonte credits",
    key=("movie_id",),
    schema=_bronze_schema(BRONZE_CREDITS_SOURCE_FIELDS),
)


# --------------------------------------------------
# Silver
# --------------------------------------------------

SILVER_MOVIE = DataContract(
    name="movie",
    grain="uma linha por movie_id",
    key=("movie_id",),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("budget", LongType(), nullable=False),
            StructField("homepage", StringType(), nullable=True),
            StructField("original_language", StringType(), nullable=False),
            StructField("original_title", StringType(), nullable=False),
            StructField("overview", StringType(), nullable=True),
            StructField("popularity", DoubleType(), nullable=False),
            StructField("release_date", DateType(), nullable=True),
            StructField("revenue", LongType(), nullable=False),
            StructField("runtime", DoubleType(), nullable=True),
            StructField("status", StringType(), nullable=False),
            StructField("tagline", StringType(), nullable=True),
            StructField("title", StringType(), nullable=False),
            StructField("vote_average", DoubleType(), nullable=False),
            StructField("vote_count", LongType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)

SILVER_MOVIE_GENRE = DataContract(
    name="movie_genre",
    grain="uma associação observada entre filme e gênero",
    key=("movie_id", "genre_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("genre_id", LongType(), nullable=False),
            StructField("genre_name", StringType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)

SILVER_MOVIE_KEYWORD = DataContract(
    name="movie_keyword",
    grain="uma associação observada entre filme e keyword",
    key=("movie_id", "keyword_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("keyword_id", LongType(), nullable=False),
            StructField("keyword_name", StringType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)

SILVER_MOVIE_PRODUCTION_COMPANY = DataContract(
    name="movie_production_company",
    grain="uma associação observada entre filme e produtora",
    key=("movie_id", "company_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("company_id", LongType(), nullable=False),
            StructField("company_name", StringType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)

SILVER_MOVIE_PRODUCTION_COUNTRY = DataContract(
    name="movie_production_country",
    grain="uma associação observada entre filme e país de produção",
    key=("movie_id", "country_code"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("country_code", StringType(), nullable=False),
            StructField("country_name", StringType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)

SILVER_MOVIE_SPOKEN_LANGUAGE = DataContract(
    name="movie_spoken_language",
    grain="uma associação observada entre filme e idioma falado",
    key=("movie_id", "language_code"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("language_code", StringType(), nullable=False),
            StructField("language_name", StringType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)

SILVER_CAST_CREDIT = DataContract(
    name="cast_credit",
    grain="um elemento observado do array de cast",
    key=("movie_id", "credit_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("credit_id", StringType(), nullable=False),
            StructField("person_id", LongType(), nullable=False),
            StructField("person_name", StringType(), nullable=False),
            StructField("cast_id", LongType(), nullable=True),
            StructField("character", StringType(), nullable=True),
            StructField("gender", LongType(), nullable=True),
            StructField("cast_order", LongType(), nullable=True),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)

SILVER_CREW_CREDIT = DataContract(
    name="crew_credit",
    grain="um elemento observado do array de crew",
    key=("movie_id", "credit_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("credit_id", StringType(), nullable=False),
            StructField("person_id", LongType(), nullable=False),
            StructField("person_name", StringType(), nullable=False),
            StructField("gender", LongType(), nullable=True),
            StructField("department", StringType(), nullable=False),
            StructField("job", StringType(), nullable=False),
            StructField("_ingestion_id", StringType(), nullable=False),
        ]
    ),
)


# --------------------------------------------------
# Gold
# --------------------------------------------------

_GOLD_MOVIE_METRIC_FIELDS = (
    StructField("title", StringType(), nullable=False),
    StructField("release_date", DateType(), nullable=True),
    StructField("release_year", IntegerType(), nullable=True),
    StructField("budget", LongType(), nullable=False),
    StructField("revenue", LongType(), nullable=False),
    StructField("commercial_metrics_eligible", BooleanType(), nullable=False),
    StructField("profit", LongType(), nullable=True),
    StructField("roi", DoubleType(), nullable=True),
    StructField("popularity", DoubleType(), nullable=False),
    StructField("vote_average", DoubleType(), nullable=False),
    StructField("vote_count", LongType(), nullable=False),
)


GOLD_MOVIE_PERFORMANCE = DataContract(
    name="movie_performance",
    grain="uma linha por movie_id",
    key=("movie_id",),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("title", StringType(), nullable=False),
            StructField("original_title", StringType(), nullable=False),
            StructField("release_date", DateType(), nullable=True),
            StructField("release_year", IntegerType(), nullable=True),
            StructField("original_language", StringType(), nullable=False),
            StructField("status", StringType(), nullable=False),
            StructField("budget", LongType(), nullable=False),
            StructField("revenue", LongType(), nullable=False),
            StructField("commercial_metrics_eligible", BooleanType(), nullable=False),
            StructField("profit", LongType(), nullable=True),
            StructField("roi", DoubleType(), nullable=True),
            StructField("popularity", DoubleType(), nullable=False),
            StructField("vote_average", DoubleType(), nullable=False),
            StructField("vote_count", LongType(), nullable=False),
        ]
    ),
)

GOLD_MOVIE_GENRE_PERFORMANCE = DataContract(
    name="movie_genre_performance",
    grain="uma linha por associação movie_id e genre_id",
    key=("movie_id", "genre_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("genre_id", LongType(), nullable=False),
            StructField("genre_name", StringType(), nullable=False),
            *_GOLD_MOVIE_METRIC_FIELDS,
        ]
    ),
)

GOLD_MOVIE_COMPANY_PERFORMANCE = DataContract(
    name="movie_company_performance",
    grain="uma linha por associação movie_id e company_id",
    key=("movie_id", "company_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("company_id", LongType(), nullable=False),
            StructField("company_name", StringType(), nullable=False),
            *_GOLD_MOVIE_METRIC_FIELDS,
        ]
    ),
)

GOLD_MOVIE_COUNTRY_PERFORMANCE = DataContract(
    name="movie_country_performance",
    grain="uma linha por associação movie_id e country_code",
    key=("movie_id", "country_code"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("country_code", StringType(), nullable=False),
            StructField("country_name", StringType(), nullable=False),
            StructField("original_language", StringType(), nullable=False),
            *_GOLD_MOVIE_METRIC_FIELDS,
        ]
    ),
)

GOLD_MOVIE_LANGUAGE_PROFILE = DataContract(
    name="movie_language_profile",
    grain="uma linha por movie_id, language_role e language_code",
    key=("movie_id", "language_role", "language_code"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("language_role", StringType(), nullable=False),
            StructField("language_code", StringType(), nullable=False),
            StructField("language_name", StringType(), nullable=True),
            *_GOLD_MOVIE_METRIC_FIELDS,
        ]
    ),
)

GOLD_MOVIE_KEYWORD_PERFORMANCE = DataContract(
    name="movie_keyword_performance",
    grain="uma linha por associação movie_id e keyword_id",
    key=("movie_id", "keyword_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("keyword_id", LongType(), nullable=False),
            StructField("keyword_name", StringType(), nullable=False),
            *_GOLD_MOVIE_METRIC_FIELDS,
        ]
    ),
)

GOLD_MOVIE_CREDIT_PARTICIPATION = DataContract(
    name="movie_credit_participation",
    grain="uma linha por participação/crédito de uma pessoa em um filme",
    key=("movie_id", "participation_type", "credit_id"),
    schema=StructType(
        [
            StructField("movie_id", LongType(), nullable=False),
            StructField("title", StringType(), nullable=False),
            StructField("participation_type", StringType(), nullable=False),
            StructField("credit_id", StringType(), nullable=False),
            StructField("person_id", LongType(), nullable=False),
            StructField("person_name", StringType(), nullable=False),
            StructField("character", StringType(), nullable=True),
            StructField("cast_order", LongType(), nullable=True),
            StructField("department", StringType(), nullable=True),
            StructField("job", StringType(), nullable=True),
        ]
    ),
)


BRONZE_CONTRACTS = (
    BRONZE_MOVIES,
    BRONZE_CREDITS,
)

SILVER_CONTRACTS = (
    SILVER_MOVIE,
    SILVER_MOVIE_GENRE,
    SILVER_MOVIE_KEYWORD,
    SILVER_MOVIE_PRODUCTION_COMPANY,
    SILVER_MOVIE_PRODUCTION_COUNTRY,
    SILVER_MOVIE_SPOKEN_LANGUAGE,
    SILVER_CAST_CREDIT,
    SILVER_CREW_CREDIT,
)

GOLD_CONTRACTS = (
    GOLD_MOVIE_PERFORMANCE,
    GOLD_MOVIE_GENRE_PERFORMANCE,
    GOLD_MOVIE_CREDIT_PARTICIPATION,
    GOLD_MOVIE_COMPANY_PERFORMANCE,
    GOLD_MOVIE_COUNTRY_PERFORMANCE,
    GOLD_MOVIE_LANGUAGE_PROFILE,
    GOLD_MOVIE_KEYWORD_PERFORMANCE,
)
