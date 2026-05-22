from app.database.db import execute, fetch_all, fetch_one

CASE_FIELDS = [
    "client_id", "referencia", "titulo", "materia", "estado",
    "juzgado", "numero_autos", "fecha_inicio", "fecha_cierre", "descripcion",
]


def list_cases_by_client(client_id: int) -> list:
    return fetch_all(
        "SELECT id, referencia, titulo, materia, estado, fecha_inicio, fecha_cierre "
        "FROM cases WHERE client_id = ? ORDER BY fecha_inicio DESC",
        (client_id,),
    )


def list_all_cases(search: str = "") -> list:
    sql = (
        "SELECT c.id, c.referencia, c.titulo, c.materia, c.estado, "
        "c.fecha_inicio, cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente "
        "FROM cases c JOIN clients cl ON cl.id = c.client_id WHERE 1=1 "
    )
    params: list = []
    if search:
        sql += "AND (c.titulo LIKE ? OR c.referencia LIKE ? OR cl.nombre LIKE ?) "
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += "ORDER BY c.fecha_inicio DESC"
    return fetch_all(sql, params)


def get_case(case_id: int):
    return fetch_one("SELECT * FROM cases WHERE id = ?", (case_id,))


def create_case(data: dict) -> int:
    cols = ",".join(CASE_FIELDS)
    placeholders = ",".join(["?"] * len(CASE_FIELDS))
    values = [data.get(f) for f in CASE_FIELDS]
    return execute(
        f"INSERT INTO cases({cols}) VALUES({placeholders})", values
    )


def update_case(case_id: int, data: dict) -> None:
    set_clause = ", ".join(f"{f} = ?" for f in CASE_FIELDS)
    values = [data.get(f) for f in CASE_FIELDS] + [case_id]
    execute(f"UPDATE cases SET {set_clause} WHERE id = ?", values)


def delete_case(case_id: int) -> None:
    execute("DELETE FROM cases WHERE id = ?", (case_id,))


# Eventos / seguimiento

def list_events(case_id: int) -> list:
    return fetch_all(
        "SELECT id, fecha, tipo, titulo, detalle FROM case_events "
        "WHERE case_id = ? ORDER BY fecha DESC",
        (case_id,),
    )


def add_event(case_id: int, tipo: str, titulo: str, detalle: str, fecha: str | None = None) -> int:
    if fecha:
        return execute(
            "INSERT INTO case_events(case_id, fecha, tipo, titulo, detalle) "
            "VALUES(?, ?, ?, ?, ?)",
            (case_id, fecha, tipo, titulo, detalle),
        )
    return execute(
        "INSERT INTO case_events(case_id, tipo, titulo, detalle) VALUES(?, ?, ?, ?)",
        (case_id, tipo, titulo, detalle),
    )


def delete_event(event_id: int) -> None:
    execute("DELETE FROM case_events WHERE id = ?", (event_id,))


def list_events_by_client(client_id: int) -> list:
    return fetch_all(
        "SELECT e.id, e.fecha, e.tipo, e.titulo, e.detalle, "
        "c.titulo AS caso FROM case_events e "
        "JOIN cases c ON c.id = e.case_id "
        "WHERE c.client_id = ? ORDER BY e.fecha DESC",
        (client_id,),
    )
