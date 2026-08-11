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
- Agente de IA local (vía [Ollama](https://ollama.com)) para hacer preguntas y resumir documentos sin enviar datos a la nube.
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
