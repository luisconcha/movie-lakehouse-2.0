"""
Configuração centralizada da aplicação movie-lakehouse-2.0.
Este módulo define a interface de configuração consumida pela aplicação.
Os valores dependentes de ambiente devem ser fornecidos externamente pelo mecanismo de deployment/execução. A forma física de injeção desses valores
será definida na etapa apropriada de deployment.

"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """configuração dependente de ambiente consumida pela aplicação"""

    catalog: str
    bronze_schema: str
    silver_schema: str
    gold_schema: str
    raw_volume: str

    def __post_init__(self) -> None:
        """Falha explicitamente quando um parâmetro obrigatório não é fornecido."""
        for field_name, value in (
            ("catalog", self.catalog),
            ("bronze_schema", self.bronze_schema),
            ("silver_schema", self.silver_schema),
            ("gold_schema", self.gold_schema),
            ("raw_volume", self.raw_volume),
        ):
            if value is None or not str(value).strip():
                raise ValueError(
                    f"Configuração obrigatória não fornecida: {field_name}"
                )

    @property
    def bronze_namespace(self) -> str:
        return f"{self.catalog}.{self.bronze_schema}"

    @property
    def silver_namespace(self) -> str:
        return f"{self.catalog}.{self.silver_schema}"

    @property
    def gold_namespace(self) -> str:
        return f"{self.catalog}.{self.gold_schema}"

    @property
    def raw_volume_path(self) -> str:
        return f"/Volumes/{self.catalog}/{self.bronze_schema}/{self.raw_volume}"
