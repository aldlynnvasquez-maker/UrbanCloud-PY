"""Almacenamiento privado; nunca expone rutas de archivos al cliente."""

from pathlib import Path

from app.configuracion.ajustes import ajustes


class Almacenamiento:
    def guardar(self, clave: str, contenido: bytes, mime: str) -> None:
        raise NotImplementedError

    def leer(self, clave: str) -> bytes:
        raise NotImplementedError

    def eliminar(self, clave: str) -> None:
        raise NotImplementedError


class Local(Almacenamiento):
    def __init__(self, raiz: str):
        self.raiz = Path(raiz).resolve()

    def _ruta(self, clave: str) -> Path:
        ruta = (self.raiz / clave).resolve()
        if not ruta.is_relative_to(self.raiz):
            raise ValueError("Ruta de almacenamiento no válida")
        return ruta

    def guardar(self, clave: str, contenido: bytes, mime: str) -> None:
        ruta = self._ruta(clave)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)

    def leer(self, clave: str) -> bytes:
        return self._ruta(clave).read_bytes()

    def eliminar(self, clave: str) -> None:
        self._ruta(clave).unlink(missing_ok=True)


class S3(Almacenamiento):
    def __init__(self, bucket: str, endpoint: str):
        import boto3
        self.bucket = bucket
        self.cliente = boto3.client("s3", endpoint_url=endpoint or None)

    def guardar(self, clave: str, contenido: bytes, mime: str) -> None:
        self.cliente.put_object(Bucket=self.bucket, Key=clave, Body=contenido, ContentType=mime)

    def leer(self, clave: str) -> bytes:
        return self.cliente.get_object(Bucket=self.bucket, Key=clave)["Body"].read()

    def eliminar(self, clave: str) -> None:
        self.cliente.delete_object(Bucket=self.bucket, Key=clave)


def almacenamiento() -> Almacenamiento:
    config = ajustes()
    if config.storage_backend == "local":
        return Local(config.storage_root)
    if config.storage_backend == "s3" and config.s3_bucket:
        return S3(config.s3_bucket, config.s3_endpoint_url)
    raise RuntimeError("STORAGE_BACKEND debe ser local o s3 con S3_BUCKET configurado")
