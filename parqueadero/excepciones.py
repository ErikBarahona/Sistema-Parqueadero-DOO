"""Excepciones de negocio del SAGP."""


class ErrorNegocio(Exception):
    """Operación rechazada por una regla de negocio (el mensaje se muestra al usuario)."""


class Denegado(ErrorNegocio):
    """Rechazo por falta de autorización: además se registra como intento no autorizado."""

    def __init__(self, tipo, mensaje):
        super().__init__(mensaje)
        self.tipo = tipo
