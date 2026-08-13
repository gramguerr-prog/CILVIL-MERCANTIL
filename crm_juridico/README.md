# CRM Jurídico

Aplicación de escritorio local (Windows y macOS) para gestión integral de despacho de abogados:

- Fichas de clientes con datos personales, contactos y correos.
- Situación familiar y patrimonial de cada cliente: estado civil, régimen económico,
  hijos (con edad calculada y aviso de menores), vehículos, cuentas corrientes,
  hipotecas, propiedades y deudas, con cálculo de activo, pasivo y patrimonio neto.
- Seguimiento de asuntos jurídicos por cliente con timeline.
- Documentos asociados a cada cliente/asunto, ordenados cronológicamente.
- Facturación con IVA, retenciones IRPF (estilo *declarando.es*), numeración correlativa y fecha de emisión.
- Gastos generales del despacho y gastos imputados a cada cliente.
- Balance económico y análisis del despacho (ingresos, gastos, beneficio, IVA repercutido/soportado, IRPF retenido).
- Estado de deuda por cliente: lo que te debe y lo que te ha pagado.
- Asistente de IA con dos motores seleccionables: **Ollama** (local, ningún dato
  sale del equipo) o **Claude** (API de Anthropic, análisis mejores pero las
  consultas viajan al proveedor). Hace consultas jurídicas, analiza el perfil de
  cada cliente, resume documentos y responde preguntas sobre ellos.
- **Auditoría automática** de los datos del despacho: facturas vencidas, huecos y
  duplicados en la numeración, retenciones de IRPF mal aplicadas, totales
  descuadrados, asuntos parados con riesgo de prescripción, gastos repercutibles
  sin facturar y fichas incompletas o duplicadas. La detección es determinista
  (reglas en código); la IA solo prioriza y explica el plan de acción.
- Análisis comercial por cliente para detectar oportunidades de servicios legales
  adicionales, cruzando su situación familiar y patrimonial con los asuntos ya
  gestionados (p. ej. hijos menores → testamento; hipoteca → revisión de cláusulas;
  deudas → Ley de Segunda Oportunidad).

## Requisitos

- Python 3.10 o superior.
- [Ollama](https://ollama.com/download) instalado en local con un modelo descargado (por ejemplo `llama3.1` o `qwen2.5`):
  ```
  ollama pull llama3.1
  ```
  El agente de IA funciona aunque Ollama no esté instalado; en ese caso esa pestaña mostrará un aviso, el resto del programa funciona igualmente.

## Instalación

### Windows

```powershell
cd crm_juridico
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### macOS

```bash
cd crm_juridico
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Inteligencia artificial

En *Ajustes > Inteligencia artificial* eliges el motor:

| | Ollama (por defecto) | Claude |
|---|---|---|
| Dónde corre | Tu ordenador | Servidores de Anthropic |
| Datos del cliente | No salen del equipo | Viajan al proveedor |
| Coste | Gratis | Por uso (se muestra en pantalla) |
| Calidad | Correcta | Claramente superior |
| Requisitos | `ollama pull llama3.1` | Clave de API |

**Advertencia para el ejercicio profesional.** Enviar datos de clientes a un
proveedor externo afecta al secreto profesional y al RGPD: necesitarás un
contrato de encargado del tratamiento con el proveedor y valorar la
confidencialidad de cada asunto. Por eso el programa viene con el motor local
activado de fábrica, y el botón *Ver datos enviados* de la pestaña «Cliente»
muestra exactamente qué se transmitiría antes de hacer ninguna consulta.

**Clave de API.** Puedes escribirla en Ajustes (se guarda sin cifrar en la
carpeta de datos) o, mejor, definir la variable de entorno
`ANTHROPIC_API_KEY`, que tiene preferencia.

Con Claude, el programa usa caché de prompts: la parte fija de las
instrucciones se reutiliza entre consultas y su coste baja alrededor de un 90 %
a partir de la segunda.

## Icono en el escritorio

Para abrir el CRM sin entrar en la carpeta, ejecuta **una sola vez**:

- **Windows**: `crear_acceso_directo_windows.bat` → crea *CRM Juridico* en el Escritorio.
- **macOS**: `crear_acceso_directo_macos.command` → crea *CRM Juridico.app* en el
  Escritorio, que puedes arrastrar al Dock.

En Windows el programa arranca sin ventana de consola de fondo.

## Usar el mismo despacho desde varios ordenadores

En *Ajustes > Carpeta de datos* puedes mover la carpeta de datos a una carpeta
sincronizada (OneDrive, iCloud Drive, Dropbox, Google Drive). Apuntando los dos
equipos a la misma carpeta, ambos ven los mismos clientes, documentos y facturas.

Pasos:

1. En el primer equipo: *Ajustes > Carpeta de datos > Cambiar carpeta…* y elige
   una carpeta dentro de tu servicio de sincronización.
2. Copia allí el contenido de la carpeta `data` anterior.
3. Reinicia el programa y comprueba que tus clientes siguen ahí.
4. En el segundo equipo: instala el programa y repite el paso 1 apuntando a la
   misma carpeta sincronizada.

**Regla imprescindible**: no tengas el programa abierto en los dos equipos a la
vez. La base de datos es un único archivo SQLite; si dos equipos escriben a la
vez, el servicio de sincronización creará copias en conflicto y puedes perder
trabajo. Ciérralo en un equipo, espera a que termine de sincronizar, y ábrelo
en el otro.

La ruta elegida se guarda en `ruta_datos.txt`, que el actualizador respeta: cada
equipo mantiene su propia configuración.

## Actualizar el programa

Para pasar a la última versión sin descargar ni descomprimir nada a mano, sin
que se acumulen carpetas y **sin tocar tus datos**:

- **Windows**: ejecuta `actualizar_windows.bat`
- **macOS**: ejecuta `actualizar_macos.command`

Descargan la última versión y sobrescriben los archivos del programa en la
misma carpeta. La carpeta `data/` (clientes, documentos y facturas) queda
intacta. Cierra el programa antes de actualizar.

## Estructura de datos

- Todo se guarda en `data/crm.db` (SQLite).
- Los documentos se copian a `data/documents/<cliente_id>/`.
- Las facturas PDF se generan en `data/invoices_pdf/`.

Puedes hacer backup copiando la carpeta `data/` completa.

## Notas fiscales (España)

Tipos por defecto editables desde *Ajustes*:

- IVA general: 21 %
- IVA reducido: 10 %
- IVA superreducido: 4 %
- Retención IRPF profesional general: 15 %
- Retención IRPF profesional nuevo (primeros 3 años): 7 %

Las retenciones IRPF solo se aplican cuando el cliente está marcado como *empresa/autónomo* (B2B). Para clientes particulares (B2C), no se aplica retención.
