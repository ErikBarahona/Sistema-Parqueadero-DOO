from __future__ import annotations
from datetime import date, datetime, time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .espacio_parqueadero import EspacioParqueadero
    from .vehiculo import Vehiculo


class Ingreso:
    """Registro de entrada/salida de un vehículo."""

    _historial: list[Ingreso] = []   # almacenamiento en memoria

    def __init__(self, id_ingreso: int, id_usuario: int, id_espacio: int,
                 id_vehiculo: int, fecha: date = None,
                 hora_entrada: time = None, hora_salida: time = None):
        self.id_ingreso = id_ingreso
        self.id_usuario = id_usuario      # FK -> Usuario
        self.id_espacio = id_espacio      # FK -> EspacioParqueadero
        self.id_vehiculo = id_vehiculo    # FK -> Vehiculo
        self.fecha = fecha
        self.hora_entrada = hora_entrada
        self.hora_salida = hora_salida

    def registrar_ingreso(self, espacio: EspacioParqueadero = None,
                          vehiculo: Vehiculo = None) -> None:
        """Registra fecha/hora de entrada y ocupa el espacio si se envía."""
        if espacio:
            espacio.asignar_espacio(vehiculo)
        ahora = datetime.now()
        self.fecha = ahora.date()
        self.hora_entrada = ahora.time().replace(microsecond=0)
        Ingreso._historial.append(self)

    def registrar_salida(self, espacio: EspacioParqueadero = None) -> None:
        """Registra hora de salida y libera el espacio si se envía."""
        if self.hora_entrada is None:
            raise ValueError("No se puede registrar salida sin un ingreso previo.")
        if self.hora_salida is not None:
            raise ValueError("La salida ya fue registrada.")
        self.hora_salida = datetime.now().time().replace(microsecond=0)
        if espacio:
            espacio.liberar_espacio()

    @classmethod
    def consultar_historial(cls, id_usuario: int = None,
                            id_vehiculo: int = None) -> list[Ingreso]:
        """Devuelve el historial, opcionalmente filtrado."""
        resultado = cls._historial
        if id_usuario is not None:
            resultado = [i for i in resultado if i.id_usuario == id_usuario]
        if id_vehiculo is not None:
            resultado = [i for i in resultado if i.id_vehiculo == id_vehiculo]
        return list(resultado)

    def __repr__(self) -> str:
        return (f"Ingreso({self.id_ingreso}, usuario={self.id_usuario}, espacio={self.id_espacio}, "
                f"vehiculo={self.id_vehiculo}, {self.fecha} {self.hora_entrada}-{self.hora_salida})")
