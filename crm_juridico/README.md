# CRM Jurídico

Aplicación de escritorio local (Windows y macOS) para gestión integral de despacho de abogados:

- Fichas de clientes con datos personales, contactos y correos.
- Seguimiento de asuntos jurídicos por cliente con timeline.
- Documentos asociados a cada cliente/asunto, ordenados cronológicamente.
- Facturación con IVA, retenciones IRPF (estilo *declarando.es*), numeración correlativa y fecha de emisión.
- Gastos generales del despacho y gastos imputados a cada cliente.
- Balance económico y análisis del despacho (ingresos, gastos, beneficio, IVA repercutido/soportado, IRPF retenido).
- Estado de deuda por cliente: lo que te debe y lo que te ha pagado.
- Agente de IA local (vía [Ollama](https://ollama.com)) para hacer preguntas y resumir documentos sin enviar datos a la nube.
- Análisis comercial por cliente para detectar oportunidades de servicios legales adicionales.

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
