import re


class Vehiculo:

    PATRON_CARRO = re.compile(r"^[A-Z]{3}\d{3}$")      
    PATRON_MOTO = re.compile(r"^[A-Z]{3}\d{2}[A-Z]$")   

    def __init__(self, id_vehiculo: int, placa: str, marca: str,
                 color: str, tipo_vehiculo: str):
        self.id_vehiculo = id_vehiculo
        self.placa = placa
        self.marca = marca
        self.color = color
        self.tipo_vehiculo = tipo_vehiculo

    def validar_placa(self) -> bool:
       
        placa = self.placa.upper().replace(" ", "").replace("-", "")
        return bool(self.PATRON_CARRO.match(placa) or self.PATRON_MOTO.match(placa))

    def actualizar_datos(self, placa: str = None, marca: str = None,
                         color: str = None, tipo_vehiculo: str = None) -> None:

        if placa is not None:
            self.placa = placa
        if marca is not None:
            self.marca = marca
        if color is not None:
            self.color = color
        if tipo_vehiculo is not None:
            self.tipo_vehiculo = tipo_vehiculo

    def __repr__(self) -> str:
        return f"Vehiculo({self.placa}, {self.marca}, {self.color}, {self.tipo_vehiculo})"
