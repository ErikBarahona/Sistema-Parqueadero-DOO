from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vehiculo import Vehiculo


class EspacioParqueadero:
    """Espacio individual dentro de un parqueadero."""

    DISPONIBLE = "Disponible"
    OCUPADO = "Ocupado"
    ESTADOS_VALIDOS = (DISPONIBLE, OCUPADO)

    def __init__(self, id_espacio: int, seccion: str, tipo_vehiculo: str,
                 estado: str = DISPONIBLE, id_parqueadero: int = None):
        self.id_espacio = id_espacio
        self.id_parqueadero = id_parqueadero  
        self.seccion = seccion
        self.tipo_vehiculo = tipo_vehiculo
        self.estado = estado

    def actualizar_estado(self, nuevo_estado: str) -> None:
        if nuevo_estado not in self.ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido. Use uno de: {self.ESTADOS_VALIDOS}")
        self.estado = nuevo_estado

    def asignar_espacio(self, vehiculo: Vehiculo = None) -> None:
        """Marca el espacio como ocupado (valida tipo de vehículo si se envía)."""
        if not self.consultar_disponibilidad():
            raise ValueError(f"El espacio {self.id_espacio} no está disponible.")
        if vehiculo and vehiculo.tipo_vehiculo != self.tipo_vehiculo:
            raise ValueError(
                f"El espacio es para {self.tipo_vehiculo}, no para {vehiculo.tipo_vehiculo}."
            )
        self.estado = self.OCUPADO

    def liberar_espacio(self) -> None:
        self.estado = self.DISPONIBLE

    def consultar_disponibilidad(self) -> bool:
        return self.estado == self.DISPONIBLE

    def __repr__(self) -> str:
        return f"EspacioParqueadero({self.id_espacio}, {self.seccion}, {self.tipo_vehiculo}, {self.estado})"
