PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    apellidos       TEXT,
    nif             TEXT,
    tipo            TEXT NOT NULL DEFAULT 'particular',   -- particular | empresa | autonomo
    email           TEXT,
    telefono        TEXT,
    direccion       TEXT,
    ciudad          TEXT,
    codigo_postal   TEXT,
    pais            TEXT DEFAULT 'España',
    fecha_alta      TEXT NOT NULL DEFAULT (date('now')),
    irpf_nuevo      INTEGER NOT NULL DEFAULT 0,           -- 1 si aplica retención reducida
    notas           TEXT,
    activo          INTEGER NOT NULL DEFAULT 1,
    -- Situación familiar y patrimonial
    estado_civil     TEXT,                                -- soltero, casado, divorciado...
    regimen_economico TEXT,                               -- gananciales, separación de bienes
    tiene_hijos      INTEGER NOT NULL DEFAULT 0,
    num_hijos        INTEGER NOT NULL DEFAULT 0,
    tiene_vehiculos  INTEGER NOT NULL DEFAULT 0,
    tiene_cuentas    INTEGER NOT NULL DEFAULT 0,
    tiene_hipotecas  INTEGER NOT NULL DEFAULT 0,
    tiene_propiedades INTEGER NOT NULL DEFAULT 0,
    tiene_deudas     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_clients_nombre ON clients(nombre, apellidos);
CREATE INDEX IF NOT EXISTS idx_clients_email  ON clients(email);

-- Hijos del cliente (relevante para familia, sucesiones, custodia)
CREATE TABLE IF NOT EXISTS client_children (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id         INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    nombre            TEXT,
    fecha_nacimiento  TEXT,
    notas             TEXT
);

CREATE INDEX IF NOT EXISTS idx_children_client ON client_children(client_id);

-- Patrimonio y cargas: vehículos, cuentas, hipotecas, propiedades, deudas
CREATE TABLE IF NOT EXISTS client_assets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    categoria     TEXT NOT NULL,   -- vehiculo|cuenta|hipoteca|propiedad|deuda
    descripcion   TEXT NOT NULL,
    identificador TEXT,            -- matrícula, IBAN, ref. catastral, nº préstamo
    entidad       TEXT,            -- banco, financiera, acreedor
    valor         REAL DEFAULT 0,  -- valor estimado, saldo o importe pendiente
    fecha         TEXT,
    notas         TEXT
);

CREATE INDEX IF NOT EXISTS idx_assets_client ON client_assets(client_id, categoria);

CREATE TABLE IF NOT EXISTS cases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    referencia      TEXT,
    titulo          TEXT NOT NULL,
    materia         TEXT,                                  -- civil, mercantil, penal, laboral...
    estado          TEXT NOT NULL DEFAULT 'abierto',       -- abierto | suspendido | cerrado
    juzgado         TEXT,
    numero_autos    TEXT,
    fecha_inicio    TEXT NOT NULL DEFAULT (date('now')),
    fecha_cierre    TEXT,
    descripcion     TEXT
);

CREATE INDEX IF NOT EXISTS idx_cases_client ON cases(client_id);

CREATE TABLE IF NOT EXISTS case_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    fecha       TEXT NOT NULL DEFAULT (datetime('now')),
    tipo        TEXT,                                      -- nota, audiencia, escrito, llamada...
    titulo      TEXT NOT NULL,
    detalle     TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_case ON case_events(case_id, fecha);

CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    case_id         INTEGER REFERENCES cases(id) ON DELETE SET NULL,
    nombre          TEXT NOT NULL,
    ruta_archivo    TEXT NOT NULL,                         -- ruta relativa a data/documents
    tipo_mime       TEXT,
    tamano_bytes    INTEGER,
    fecha_subida    TEXT NOT NULL DEFAULT (datetime('now')),
    fecha_doc       TEXT,                                  -- fecha del documento (puede diferir)
    descripcion     TEXT
);

CREATE INDEX IF NOT EXISTS idx_docs_client ON documents(client_id, fecha_doc);

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    numero          TEXT NOT NULL UNIQUE,                  -- correlativa: AÑO-NNNN o prefijo
    serie           TEXT NOT NULL,
    correlativo     INTEGER NOT NULL,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    case_id         INTEGER REFERENCES cases(id) ON DELETE SET NULL,
    fecha_emision   TEXT NOT NULL DEFAULT (date('now')),
    fecha_vencimiento TEXT,
    base_imponible  REAL NOT NULL DEFAULT 0,
    tipo_iva        REAL NOT NULL DEFAULT 21,              -- porcentaje
    importe_iva     REAL NOT NULL DEFAULT 0,
    tipo_irpf       REAL NOT NULL DEFAULT 0,               -- porcentaje (0 si no aplica)
    importe_irpf    REAL NOT NULL DEFAULT 0,
    total           REAL NOT NULL DEFAULT 0,
    estado          TEXT NOT NULL DEFAULT 'emitida',       -- borrador | emitida | cobrada | parcial | anulada
    notas           TEXT
);

CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_fecha  ON invoices(fecha_emision);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    descripcion     TEXT NOT NULL,
    cantidad        REAL NOT NULL DEFAULT 1,
    precio_unitario REAL NOT NULL DEFAULT 0,
    subtotal        REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_lines_invoice ON invoice_lines(invoice_id);

CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    invoice_id      INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
    fecha           TEXT NOT NULL DEFAULT (date('now')),
    importe         REAL NOT NULL,
    metodo          TEXT,                                  -- transferencia, efectivo, tarjeta...
    notas           TEXT
);

CREATE INDEX IF NOT EXISTS idx_payments_client ON payments(client_id);

CREATE TABLE IF NOT EXISTS expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT NOT NULL DEFAULT (date('now')),
    concepto        TEXT NOT NULL,
    categoria       TEXT,                                  -- alquiler, suministros, material, dietas...
    proveedor       TEXT,
    base_imponible  REAL NOT NULL DEFAULT 0,
    tipo_iva        REAL NOT NULL DEFAULT 21,
    importe_iva     REAL NOT NULL DEFAULT 0,
    total           REAL NOT NULL DEFAULT 0,
    deducible       INTEGER NOT NULL DEFAULT 1,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    case_id         INTEGER REFERENCES cases(id) ON DELETE SET NULL,
    repercutible    INTEGER NOT NULL DEFAULT 0,           -- 1 si se va a facturar al cliente
    notas           TEXT
);

CREATE INDEX IF NOT EXISTS idx_expenses_fecha   ON expenses(fecha);
CREATE INDEX IF NOT EXISTS idx_expenses_client  ON expenses(client_id);

CREATE TABLE IF NOT EXISTS commercial_analyses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    fecha           TEXT NOT NULL DEFAULT (datetime('now')),
    contenido       TEXT NOT NULL,                         -- propuesta comercial generada o editada
    modelo_usado    TEXT
);

CREATE INDEX IF NOT EXISTS idx_analyses_client ON commercial_analyses(client_id);
