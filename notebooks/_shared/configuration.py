"""
Configuração centralizada da aplicação movie-lakehouse-2.0.
Este módulo define a interface de configuração consumida pela aplicação.
Os valores dependentes de ambiente devem ser fornecidos externamente pelo mecanismo de deployment/execução. A forma física de injeção desses valores
será definida na etapa apropriada de deployment.

"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class AppConfig:
    """configuração lógica da aplicação, sem validar recursos no Unity Catalog"""

    catalog: str
    bronze_schema: str | None = None
    silver_schema: str | None = None
    gold_schema: str | None = None
    raw_volume: str | None = None

    def __post_init__(self) -> None:
        self._validate_value("catalog", self.catalog)

        for field_name, value in (
            ("bronze_schema", self.bronze_schema),
            ("silver_schema", self.silver_schema),
            ("gold_schema", self.gold_schema),
            ("raw_volume", self.raw_volume),
        ):
            if value is not None:
                self._validate_value(field_name, value)

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)

    @staticmethod
    def _validate_value(name: str, value: str) -> None:
        if not str(value).strip():
            raise ValueError(f"Configuração inválida: {name} não pode ser vazio.")

    @staticmethod
    def _require(name: str, value: str | None) -> str:
        if value is None:
            raise ValueError(f"Configuração necessária não fornecida: {name}")
        return value

    @property
    def bronze_namespace(self) -> str:
        schema = self._require("bronze_schema", self.bronze_schema)
        return f"{self.catalog}.{schema}"

    @property
    def silver_namespace(self) -> str:
        schema = self._require("silver_schema", self.silver_schema)
        return f"{self.catalog}.{schema}"

    @property
    def gold_namespace(self) -> str:
        schema = self._require("gold_schema", self.gold_schema)
        return f"{self.catalog}.{schema}"

    @property
    def raw_volume_path(self) -> str:
        schema = self._require("bronze_schema", self.bronze_schema)
        volume = self._require("raw_volume", self.raw_volume)

        return f"/Volumes/{self.catalog}/{schema}/{volume}"
