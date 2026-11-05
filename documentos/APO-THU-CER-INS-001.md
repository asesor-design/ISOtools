---
codigo: APO-THU-CER-INS-001
titulo: Instructivo de control de certificados (Streamlit)
version: 1.1
fecha: 01/09/2026
drive: 1faquucN4VVVMXvrfuOMZMv8ZkD5giA_C
formato: docx
dueno: Gestión y Control
padre: APO-THU-MAN-001
relacion: Deriva
revision: Cada 2 años
resumen: Cómo registrar personas y cargar certificados (alturas, eléctrico, médico, HSE) en la app Streamlit, y qué significa el semáforo verde, amarillo y rojo.
---

# Instructivo de control de certificados (Streamlit)

## Objetivo

Establecer las directrices paso a paso para el control, almacenamiento y monitoreo de los certificados de competencias y habilitaciones (trabajo en alturas, riesgo eléctrico, certificados médicos, entre otros) tanto de colaboradores directos de STARTEC S.A. como de terceros (contratistas), mediante el uso del Sistema Automatizado de Gestión de Datos basado en Streamlit.

## Alcance

Este instructivo es de aplicación obligatoria para el ingreso, validación y seguimiento de toda la documentación habilitante requerida para autorizar a colaboradores y personal externo a ejecutar trabajos operativos o administrativos de riesgo dentro de las instalaciones o proyectos de STARTEC S.A.

## Responsables

- **Gestión y Control:** administrar el sistema Streamlit, validar la autenticidad de los certificados subidos y gestionar los permisos de acceso al repositorio.
- **Jefa de Operaciones y Supervisores de campo:** asegurar que ningún colaborador o contratista inicie labores sin que sus certificados figuren en estado "Vigente" en el sistema.
- **Terceros (contratistas y proveedores):** proveer la documentación habilitante actualizada (física o digital) a su contraparte en STARTEC antes del inicio de cualquier obra o servicio.

## Herramientas y sistemas

- **Plataforma:** aplicación web desarrollada en Streamlit para la gestión documental de Recursos Humanos y Seguridad Industrial.
- **Repositorio:** base de datos y almacenamiento en la nube enlazada a la aplicación para el resguardo de los documentos en formato PDF o imagen.

## Instrucciones del proceso

### 5.1 Acceso al sistema

1. Ingresar a la URL oficial de la aplicación Streamlit proporcionada por el proveedor de soporte tecnológico de STARTEC S.A.
2. Iniciar sesión utilizando las credenciales corporativas autorizadas (usuario y contraseña).
3. Seleccionar el módulo "Gestión de Certificados y Competencias" en el panel lateral.

### 5.2 Registro y actualización de personal

1. Hacer clic en el botón "Nuevo Registro".
2. Seleccionar el tipo de personal: Colaborador Directo, o Tercero / Contratista.
3. Completar los campos obligatorios: Nombres, Cédula/RUT, Empresa (si es tercero), Cargo y Proyecto asignado.

### 5.3 Carga y clasificación de certificados habilitantes

Por cada perfil creado, se deben adjuntar los documentos correspondientes. Los certificados exigibles incluyen, pero no se limitan a:

- Certificado de Riesgo en Alturas
- Certificación de Riesgo Eléctrico / Etiquetado y Bloqueo (LOTO)
- Certificado Médico Ocupacional (aptitud laboral)
- Inducción de Seguridad Industrial (HSE)

Paso a paso de carga:

1. En el perfil del trabajador, seleccionar el tipo de certificado en el menú desplegable.
2. Ingresar la Fecha de Emisión y la Fecha de Vencimiento indicadas en el documento físico.
3. Arrastrar o cargar el archivo digital (PDF) en la zona de carga.
4. Presionar "Guardar y Cargar Documento".

### 5.4 Monitoreo de alertas y vencimientos

El sistema evalúa automáticamente las fechas de vencimiento de los documentos.

| Estado | Significado | Qué hacer |
|---|---|---|
| VERDE · Vigente | Más de 30 días de validez. | El personal está habilitado para laborar. |
| AMARILLO · Próximo a vencer | Vence en menos de 30 días. | El sistema alerta; notificar al colaborador o contratista para renovar. |
| ROJO · Vencido / No apto | Caducado o no cargado. | Prohibido ejecutar labores hasta actualizar y validar el documento. |

## Matriz de riesgos y controles asociados

| Riesgo identificado | Nivel | Medida de control (automatizada) |
|---|---|---|
| Accidentes por personal no calificado operando (terceros o propios) | ALTO | Bloqueo automático de asignación de tareas si el certificado está en estado rojo (vencido). |
| Pérdida de trazabilidad de los documentos físicos | MEDIO | Centralización obligatoria de copias digitales en el repositorio de la plataforma web. |

## Indicadores de gestión (dashboard)

El sistema proporciona un panel de métricas en tiempo real que debe ser revisado semanalmente:

- **% de cumplimiento documental:** (Personal con certificados vigentes / Total de personal activo en proyectos) × 100.
- **Tasa de terceros habilitados:** monitoreo específico para asegurar el cumplimiento del proceso de compras y contratación (cláusula 8.4).

## Registros generados

| Código del registro | Nombre del registro | Soporte | Retención |
|---|---|---|---|
| APO-THU-CER-REG-001 | Base de datos de personal y estado de certificados | Digital (Streamlit / base de datos) | Permanente (histórico) |
| APO-THU-CER-REG-002 | Repositorio de certificados (PDF) | Nube / servidor de la app | Vigencia + 3 años |
