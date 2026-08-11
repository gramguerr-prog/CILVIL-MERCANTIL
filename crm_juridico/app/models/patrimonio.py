"""Hijos, patrimonio y cargas de cada cliente."""
from app.database.db import execute, fetch_all, fetch_one

# categoria -> (etiqueta, etiqueta identificador, etiqueta entidad, etiqueta valor)
CATEGORIAS = {
    "vehiculo": ("Vehículos", "Matrícula", "Financiera", "Valor estimado"),
    "cuenta": ("Cuentas corrientes", "IBAN", "Banco", "Saldo aproximado"),
    "hipoteca": ("Hipotecas", "Nº préstamo", "Banco", "Capital pendiente"),
    "propiedad": ("Propiedades", "Ref. catastral", "Registro", "Valor estimado"),
    "deuda": ("Deudas", "Nº expediente", "Acreedor", "Importe pendiente"),
}

# Título en singular para los cuadros de diálogo de alta/edición.
SINGULAR = {
    "vehiculo": "Vehículo",
    "cuenta": "Cuenta corriente",
    "hipoteca": "Hipoteca",
    "propiedad": "Propiedad",
    "deuda": "Deuda",
}

# categoria -> columna del flag en la tabla clients
FLAG_BY_CATEGORIA = {
    "vehiculo": "tiene_vehiculos",
    "cuenta": "tiene_cuentas",
    "hipoteca": "tiene_hipotecas",
    "propiedad": "tiene_propiedades",
    "deuda": "tiene_deudas",
}

ASSET_FIELDS = [
    "client_id", "categoria", "descripcion", "identificador",
    "entidad", "valor", "fecha", "notas",
]


# ---------- Hijos ----------

def list_children(client_id: int) -> list:
    return fetch_all(
        "SELECT id, nombre, fecha_nacimiento, notas FROM client_children "
        "WHERE client_id = ? ORDER BY fecha_nacimiento, id",
        (client_id,),
    )


def get_child(child_id: int):
    return fetch_one("SELECT * FROM client_children WHERE id = ?", (child_id,))


def create_child(client_id: int, nombre: str, fecha_nacimiento: str | None,
                 notas: str = "") -> int:
    new_id = execute(
        "INSERT INTO client_children(client_id, nombre, fecha_nacimiento, notas) "
        "VALUES(?, ?, ?, ?)",
        (client_id, nombre, fecha_nacimiento, notas),
    )
    _sync_children_flags(client_id)
    return new_id


def update_child(child_id: int, nombre: str, fecha_nacimiento: str | None,
                 notas: str = "") -> None:
    execute(
        "UPDATE client_children SET nombre = ?, fecha_nacimiento = ?, notas = ? "
        "WHERE id = ?",
        (nombre, fecha_nacimiento, notas, child_id),
    )


def delete_child(child_id: int) -> None:
    row = get_child(child_id)
    execute("DELETE FROM client_children WHERE id = ?", (child_id,))
    if row is not None:
        _sync_children_flags(row["client_id"])


def _sync_children_flags(client_id: int) -> None:
    """Mantiene tiene_hijos / num_hijos coherentes con la lista de hijos."""
    row = fetch_one(
        "SELECT COUNT(*) AS n FROM client_children WHERE client_id = ?",
        (client_id,),
    )
    n = int(row["n"] if row else 0)
    if n > 0:
        execute(
            "UPDATE clients SET tiene_hijos = 1, num_hijos = ? WHERE id = ?",
            (n, client_id),
        )
    else:
        # Se conserva el flag manual, pero el contador vuelve a 0.
        execute("UPDATE clients SET num_hijos = 0 WHERE id = ?", (client_id,))


# ---------- Patrimonio y cargas ----------

def list_assets(client_id: int, categoria: str | None = None) -> list:
    sql = (
        "SELECT id, categoria, descripcion, identificador, entidad, valor, "
        "fecha, notas FROM client_assets WHERE client_id = ? "
    )
    params: list = [client_id]
    if categoria:
        sql += "AND categoria = ? "
        params.append(categoria)
    sql += "ORDER BY categoria, id"
    return fetch_all(sql, params)


def get_asset(asset_id: int):
    return fetch_one("SELECT * FROM client_assets WHERE id = ?", (asset_id,))


def create_asset(data: dict) -> int:
    cols = ",".join(ASSET_FIELDS)
    placeholders = ",".join(["?"] * len(ASSET_FIELDS))
    values = [data.get(f) for f in ASSET_FIELDS]
    new_id = execute(
        f"INSERT INTO client_assets({cols}) VALUES({placeholders})", values
    )
    _sync_asset_flag(data["client_id"], data["categoria"])
    return new_id


def update_asset(asset_id: int, data: dict) -> None:
    fields = [f for f in ASSET_FIELDS if f != "client_id"]
    set_clause = ", ".join(f"{f} = ?" for f in fields)
    values = [data.get(f) for f in fields] + [asset_id]
    execute(f"UPDATE client_assets SET {set_clause} WHERE id = ?", values)


def delete_asset(asset_id: int) -> None:
    row = get_asset(asset_id)
    execute("DELETE FROM client_assets WHERE id = ?", (asset_id,))
    if row is not None:
        _sync_asset_flag(row["client_id"], row["categoria"])


def _sync_asset_flag(client_id: int, categoria: str) -> None:
    """Marca el checkbox correspondiente cuando existe al menos un elemento."""
    flag = FLAG_BY_CATEGORIA.get(categoria)
    if not flag:
        return
    row = fetch_one(
        "SELECT COUNT(*) AS n FROM client_assets WHERE client_id = ? AND categoria = ?",
        (client_id, categoria),
    )
    if int(row["n"] if row else 0) > 0:
        execute(f"UPDATE clients SET {flag} = 1 WHERE id = ?", (client_id,))


def patrimonio_summary(client_id: int) -> dict:
    """Totales por categoría más activo, pasivo y patrimonio neto estimado."""
    rows = fetch_all(
        "SELECT categoria, COUNT(*) AS n, COALESCE(SUM(valor), 0) AS total "
        "FROM client_assets WHERE client_id = ? GROUP BY categoria",
        (client_id,),
    )
    por_categoria = {
        r["categoria"]: {"n": int(r["n"]), "total": float(r["total"])}
        for r in rows
    }
    activo = sum(
        por_categoria.get(c, {}).get("total", 0.0)
        for c in ("vehiculo", "cuenta", "propiedad")
    )
    pasivo = sum(
        por_categoria.get(c, {}).get("total", 0.0)
        for c in ("hipoteca", "deuda")
    )
    return {
        "por_categoria": por_categoria,
        "activo": round(activo, 2),
        "pasivo": round(pasivo, 2),
        "neto": round(activo - pasivo, 2),
    }
