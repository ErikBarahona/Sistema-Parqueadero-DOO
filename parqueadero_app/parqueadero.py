from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .espacio_parqueadero import EspacioParqueadero
    from .usuario import Usuario


class Parqueadero:
    """Entidad principal: agrupa espacios y usuarios."""

    def __init__(self, id_parqueadero: int, razon_social: str, ubicacion: str,
                 capacidad: int, telefono: str, correo: str):
        self.id_parqueadero = id_parqueadero
        self.razon_social = razon_social
        self.ubicacion = ubicacion
        self.capacidad = capacidad
        self.telefono = telefono
        self.correo = correo
        self.abierto = False                       # lo usa Usuario.abrir/cerrar
        self.espacios: list[EspacioParqueadero] = []
        self.usuarios: list[Usuario] = []

    def registrar_usuario(self, usuario: Usuario) -> None:
        usuario.id_parqueadero = self.id_parqueadero
        self.usuarios.append(usuario)

    def registrar_espacio(self, espacio: EspacioParqueadero) -> None:
        if len(self.espacios) >= self.capacidad:
            raise ValueError("Se alcanzó la capacidad máxima del parqueadero.")
        if any(e.id_espacio == espacio.id_espacio for e in self.espacios):
            raise ValueError(f"Ya existe el espacio {espacio.id_espacio}.")
        espacio.id_parqueadero = self.id_parqueadero
        self.espacios.append(espacio)

    def actualizar_espacio(self, id_espacio: int, **cambios) -> EspacioParqueadero:
        permitidos = {"seccion", "estado", "tipo_vehiculo"}
        espacio = next((e for e in self.espacios if e.id_espacio == id_espacio), None)
        if espacio is None:
            raise LookupError(f"No existe el espacio {id_espacio}.")
        for campo, valor in cambios.items():
            if campo not in permitidos:
                raise ValueError(f"Campo no actualizable: {campo}")
            if campo == "estado":
                espacio.actualizar_estado(valor)
            else:
                setattr(espacio, campo, valor)
        return espacio

    def consultar_disponibilidad(self, tipo_vehiculo: str = None) -> list[EspacioParqueadero]:
        libres = [e for e in self.espacios if e.consultar_disponibilidad()]
        if tipo_vehiculo:
            libres = [e for e in libres if e.tipo_vehiculo == tipo_vehiculo]
        return libres

    def generar_reporte(self) -> str:
        total = len(self.espacios)
        libres = len(self.consultar_disponibilidad())
        ocupados = total - libres
        return (
            f"=== Reporte: {self.razon_social} ===\n"
            f"Ubicación: {self.ubicacion}\n"
            f"Capacidad: {self.capacidad}\n"
            f"Espacios registrados: {total}\n"
            f"Disponibles: {libres} | Ocupados: {ocupados}\n"
            f"Usuarios registrados: {len(self.usuarios)}\n"
            f"Estado: {'Abierto' if self.abierto else 'Cerrado'}"
        )

    def __repr__(self) -> str:
        return f"Parqueadero({self.id_parqueadero}, {self.razon_social})"
