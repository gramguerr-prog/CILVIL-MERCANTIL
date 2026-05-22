from app.database.db import execute, fetch_all, fetch_one

CLIENT_FIELDS = [
    "nombre", "apellidos", "nif", "tipo", "email", "telefono",
    "direccion", "ciudad", "codigo_postal", "pais",
    "irpf_nuevo", "notas", "activo",
]


def list_clients(search: str = "", only_active: bool = False) -> list:
    sql = (
        "SELECT id, nombre, apellidos, nif, tipo, email, telefono, "
        "ciudad, fecha_alta, activo FROM clients WHERE 1=1 "
    )
    params: list = []
    if only_active:
        sql += "AND activo = 1 "
    if search:
        sql += (
            "AND (nombre LIKE ? OR apellidos LIKE ? OR nif LIKE ? "
            "OR email LIKE ?) "
        )
        like = f"%{search}%"
        params.extend([like, like, like, like])
    sql += "ORDER BY nombre COLLATE NOCASE, apellidos COLLATE NOCASE"
    return fetch_all(sql, params)


def get_client(client_id: int):
    return fetch_one("SELECT * FROM clients WHERE id = ?", (client_id,))


def create_client(data: dict) -> int:
    cols = ",".join(CLIENT_FIELDS)
    placeholders = ",".join(["?"] * len(CLIENT_FIELDS))
    values = [data.get(f) for f in CLIENT_FIELDS]
    return execute(
        f"INSERT INTO clients({cols}) VALUES({placeholders})", values
    )


def update_client(client_id: int, data: dict) -> None:
    set_clause = ", ".join(f"{f} = ?" for f in CLIENT_FIELDS)
    values = [data.get(f) for f in CLIENT_FIELDS] + [client_id]
    execute(f"UPDATE clients SET {set_clause} WHERE id = ?", values)


def delete_client(client_id: int) -> None:
    execute("DELETE FROM clients WHERE id = ?", (client_id,))


def list_emails() -> list:
    return fetch_all(
        "SELECT id, nombre, apellidos, email FROM clients "
        "WHERE email IS NOT NULL AND email <> '' "
        "ORDER BY nombre COLLATE NOCASE"
    )


def client_balance(client_id: int) -> dict:
    """Devuelve facturado, cobrado, pendiente para un cliente."""
    row = fetch_one(
        "SELECT COALESCE(SUM(total), 0) AS facturado "
        "FROM invoices WHERE client_id = ? AND estado <> 'anulada'",
        (client_id,),
    )
    facturado = float(row["facturado"] if row else 0)
    row = fetch_one(
        "SELECT COALESCE(SUM(importe), 0) AS cobrado "
        "FROM payments WHERE client_id = ?",
        (client_id,),
    )
    cobrado = float(row["cobrado"] if row else 0)
    return {
        "facturado": facturado,
        "cobrado": cobrado,
        "pendiente": facturado - cobrado,
    }
