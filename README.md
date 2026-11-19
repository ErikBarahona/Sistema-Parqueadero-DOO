# SAGP – Sistema Autónomo de Gestión de Parqueadero

Aplicación web (Django + PostgreSQL) para controlar entradas y salidas de vehículos, visitantes,
permisos y reportes en edificios residenciales sin personal de seguridad.

## Módulos incluidos

| Módulo | Requisitos |
|---|---|
| Inicio de sesión con roles (Administrador, Residente, Auditor), bloqueo tras 5 intentos fallidos, cambio de clave | RF-01 a RF-06 |
| Usuarios, apartamentos y límite de vehículos por apartamento | RF-03, RF-07 a RF-10 |
| Vehículos y usuarios autorizados para retirarlos | RF-11 a RF-14 |
| Portería: entrada y salida con validaciones, intentos no autorizados y alertas | RF-15 a RF-23 |
| Visitantes (límite simultáneo, tiempo máximo, espacio de visitantes) | RF-24 a RF-29 |
| Espacios por tipo y ocupación en tiempo real | RF-30 a RF-36 |
| Permisos con vigencia e historial de cambios | RF-37 a RF-40 |
| Reportes con filtros y exportación a CSV (Excel), historial por vehículo | RF-41 a RF-44, RF-47 |
| Notificaciones dentro del sistema | RF-48, RF-49 |

Pendiente para una segunda versión: exportar a PDF (RF-46 parcial), reportes de ocupación históricos (RF-43),
recuperación de contraseña por correo (RF-04 parcial; hoy la restablece el administrador) y reporte de auditoría.

---

## 1. Ejecutar en tu computador (Windows / PowerShell)

1. Abre esta carpeta en VS Code y, en la terminal:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Copia `.env.example` como `.env` y escribe tu contraseña de PostgreSQL en `DB_PASSWORD`.

3. En pgAdmin crea una base de datos **vacía** llamada `sagp_app`
   (clic derecho en *Databases → Create → Database*).
   No uses la base `sagp` creada con el script SQL: Django crea sus propias tablas con migraciones
   (el mismo modelo físico: 13 tablas, con las mismas restricciones e índices únicos parciales).

4. Crea las tablas y carga los datos de demostración:

```powershell
python manage.py check
python manage.py makemigrations parqueadero
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
```

5. Abre http://127.0.0.1:8000/ e ingresa con:

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `Admin2026*` |
| Auditor | `auditor` | `Admin2026*` |
| Residente | `cperez`, `mgomez`, `arojas` | `Residente2026*` |

> Cambia estas contraseñas antes de usar el sistema con datos reales.

## 2. Guion de pruebas (para la demostración)

1. Ingresa como `cperez` → *Portería* → registra la **entrada** de `ABC123` → queda ocupado el espacio C-01.
2. Intenta registrar de nuevo la entrada de `ABC123` → rechazado (RF-21).
3. Ingresa como `mgomez` → *Portería* → intenta la **salida** de `ABC123` → rechazado y registrado como intento no autorizado (RF-19).
4. Ingresa como `admin` → *Inicio* muestra el intento y la ocupación; *Notificaciones* trae la alerta (RF-23).
5. Como `cperez`, *Visitantes* → registra una visita con placa `JKL321` tipo Carro → usa el espacio V-01 (RF-24 a RF-29).
6. Como `admin`, *Administración → Permisos* → desactiva el permiso de `cperez` → ya no puede registrar entradas (RF-37, RF-38).
7. *Reportes → Entradas y salidas* → filtra por placa y exporta a CSV (RF-41, RF-46, RF-47).

---

## 3. Publicar en DigitalOcean (acceso desde cualquier navegador)

### 3.1 Subir el código a GitHub
Sube la carpeta completa, **incluida `parqueadero/migrations/`** (se genera con `makemigrations`).
El archivo `.env` y la carpeta `venv` NO se suben (ya están en `.gitignore`).

### 3.2 Base de datos
1. DigitalOcean → *Databases → Create → PostgreSQL* (plan básico, región más cercana).
2. Dentro del clúster crea la base `sagp_app`.
3. En *Trusted Sources* agrega tu IP (para el paso 3.4) y, después, tu aplicación.
4. Copia la *Connection string* (`postgresql://usuario:clave@host:puerto/sagp_app?sslmode=require`).

### 3.3 Aplicación
1. *App Platform → Create App* → conecta tu repositorio de GitHub (rama `main`).
2. Run command: `gunicorn --worker-tmp-dir /dev/shm sagp_web.wsgi` (HTTP port 8080).
3. Variables de entorno:

| Variable | Valor |
|---|---|
| `DEBUG` | `False` |
| `SECRET_KEY` | una clave larga aleatoria (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DATABASE_URL` | la *Connection string* de la base |
| `ALLOWED_HOSTS` | `.ondigitalocean.app` (y tu dominio, si tienes) |
| `CSRF_TRUSTED_ORIGINS` | `https://*.ondigitalocean.app` |

4. Si los estilos propios no cargan, agrega el comando de build `python manage.py collectstatic --noinput`.

### 3.4 Crear las tablas en la nube
Desde tu computador, apuntando a la base de DigitalOcean (tu IP debe estar en *Trusted Sources*):

```powershell
$env:DATABASE_URL = "postgresql://usuario:clave@host:puerto/sagp_app?sslmode=require"
python manage.py migrate
python manage.py cargar_demo      # opcional: datos de demostración
```

Abre la URL pública de la app: funciona en cualquier navegador y equipo, con HTTPS.

---

## Diseño orientado a objetos

La lógica de negocio vive dentro de las clases del dominio (como en el diagrama de clases) y las vistas
son clases que heredan de una jerarquía común.

| Clase | Métodos principales |
|---|---|
| `Parqueadero` | `consultar_ocupacion()` |
| `Apartamento` | `cupo_disponible()`, `definir_max_vehiculos()`, `dar_de_baja()`, `residentes_activos()` |
| `Usuario` (hereda de `AbstractBaseUser`) | `autenticar()`, `cambiar_clave()`, `activar()`, `desactivar()`, `puede_operar()`, `esta_autorizado_para()`, `registrar_intento_fallido()` |
| `Vehiculo` | `validar_placa()`, `esta_dentro()`, `desactivar()`, `autorizar_usuarios()` |
| `Espacio` | `buscar_libre()`, `ocupar()`, `liberar()`, `bloquear()`, `asignar_apartamento()`, `ocupacion_por_tipo()` |
| `RegistroAcceso` | `registrar_entrada()`, `registrar_salida()`, `validar_salida()`, `finalizar()` |
| `Visitante` | `registrar()`, `tiene_visita_activa()` |
| `RegistroVisita` | `registrar_entrada()`, `registrar_salida()`, `excedida` |
| `Permiso` | `otorgar()`, `activar()`, `desactivar()`, `alternar()`, `vigente` |
| `HistorialPermiso` | `registrar_cambio()` |
| `IntentoNoAutorizado` | `registrar()`, `generar_alerta()` |
| `Notificacion` | `enviar()`, `marcar_leida()`, `marcar_todas_leidas()` |

Jerarquía de las vistas:

```
View (Django)
 ├── RolRequeridoMixin ──► ListaTablaView ──► UsuarioListView, ApartamentoListView, EspacioListView,
 │                      │                      VehiculoListView, PermisoListView, NotificacionListView
 │                      │                  └─► ReporteView ──► ReporteAccesosView, ReporteVisitasView,
 │                      │                                      ReporteIntentosView, ReportePermisosView
 │                      └─► FormularioView ──► UsuarioCrearView/EditarView, ApartamentoCrearView/EditarView,
 │                                             EspacioCrearView/EditarView, VehiculoCrearView/EditarView,
 │                                             PermisoCrearView
 └── PorteriaView, VisitasView, PermisoCambiarView, InicioView, LoginView, LogoutView
```

Conceptos de POO aplicados: **herencia** (`Usuario`, formularios, vistas), **polimorfismo** (cada subclase de
`ListaTablaView` implementa `obtener_filas()`; `Denegado` es un tipo de `ErrorNegocio`), **encapsulamiento**
(las reglas viven en la clase a la que pertenecen) y **asociación/composición** entre las clases del dominio.

## Estructura

```
sagp_web/          configuración (settings.py lee variables de entorno)
parqueadero/
  models.py        13 clases del dominio con sus atributos, relaciones, restricciones y métodos de negocio
  excepciones.py   ErrorNegocio y Denegado
  views.py         vistas como clases (jerarquía de arriba)
  forms.py         formularios y validaciones
  contexto.py      contexto global de plantillas (notificaciones sin leer)
  templates/       plantillas HTML (Bootstrap)
  management/commands/cargar_demo.py   datos de demostración
```
