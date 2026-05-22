from app.database.db import execute, fetch_all, fetch_one

EXPENSE_FIELDS = [
    "fecha", "concepto", "categoria", "proveedor",
    "base_imponible", "tipo_iva", "importe_iva", "total",
    "deducible", "client_id", "case_id", "repercutible", "notas",
]


def list_expenses(search: str = "", client_id: int | None = None,
                  desde: str | None = None, hasta: str | None = None) -> list:
    sql = (
        "SELECT e.id, e.fecha, e.concepto, e.categoria, e.proveedor, "
        "e.base_imponible, e.importe_iva, e.total, e.deducible, "
        "e.repercutible, e.client_id, "
        "cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente "
        "FROM expenses e LEFT JOIN clients cl ON cl.id = e.client_id WHERE 1=1 "
    )
    params: list = []
    if client_id is not None:
        sql += "AND e.client_id = ? "
        params.append(client_id)
    if desde:
        sql += "AND e.fecha >= ? "
        params.append(desde)
    if hasta:
        sql += "AND e.fecha <= ? "
        params.append(hasta)
    if search:
        sql += "AND (e.concepto LIKE ? OR e.proveedor LIKE ? OR e.categoria LIKE ?) "
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += "ORDER BY e.fecha DESC, e.id DESC"
    return fetch_all(sql, params)


def get_expense(expense_id: int):
    return fetch_one("SELECT * FROM expenses WHERE id = ?", (expense_id,))


def create_expense(data: dict) -> int:
    cols = ",".join(EXPENSE_FIELDS)
    placeholders = ",".join(["?"] * len(EXPENSE_FIELDS))
    values = [data.get(f) for f in EXPENSE_FIELDS]
    return execute(
        f"INSERT INTO expenses({cols}) VALUES({placeholders})", values
    )


def update_expense(expense_id: int, data: dict) -> None:
    set_clause = ", ".join(f"{f} = ?" for f in EXPENSE_FIELDS)
    values = [data.get(f) for f in EXPENSE_FIELDS] + [expense_id]
    execute(f"UPDATE expenses SET {set_clause} WHERE id = ?", values)


def delete_expense(expense_id: int) -> None:
    execute("DELETE FROM expenses WHERE id = ?", (expense_id,))


def list_expenses_by_client(client_id: int) -> list:
    return fetch_all(
        "SELECT id, fecha, concepto, categoria, proveedor, base_imponible, "
        "importe_iva, total, repercutible FROM expenses WHERE client_id = ? "
        "ORDER BY fecha DESC",
        (client_id,),
    )
