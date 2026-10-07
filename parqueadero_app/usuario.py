from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parqueadero import Parqueadero
    from .vehiculo import Vehiculo


class Usuario:
    """Residente que usa el parqueadero."""

    def __init__(self, id_usuario: int, nombre: str, apellido: str, cedula: str,
                 correo: str, apartamento: str, id_parqueadero: int = None):
        self.id_usuario = id_usuario
        self.id_parqueadero = id_parqueadero  
        self.nombre = nombre
        self.apellido = apellido
        self.cedula = cedula
        self.correo = correo
        self.apartamento = apartamento
        self.sesion_activa = False
        self.visitantes: list[Vehiculo] = []

    def iniciar_sesion(self) -> None:
        self.sesion_activa = True

    def cerrar_sesion(self) -> None:
        self.sesion_activa = False

    def _exigir_sesion(self) -> None:
        if not self.sesion_activa:
            raise PermissionError("Debe iniciar sesión para realizar esta acción.")

    def registrar_visitantes(self, vehiculo: Vehiculo) -> None:
      
        self._exigir_sesion()
        if not vehiculo.validar_placa():
            raise ValueError(f"Placa inválida: {vehiculo.placa}")
        self.visitantes.append(vehiculo)

    def abrir_parqueadero(self, parqueadero: Parqueadero) -> None:
        self._exigir_sesion()
        parqueadero.abierto = True

    def cerrar_parqueadero(self, parqueadero: Parqueadero) -> None:
        self._exigir_sesion()
        parqueadero.abierto = False

    def __repr__(self) -> str:
        return f"Usuario({self.id_usuario}, {self.nombre} {self.apellido}, apto {self.apartamento})"
