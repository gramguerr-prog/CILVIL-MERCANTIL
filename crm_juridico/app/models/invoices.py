from datetime import date

from app.database.db import execute, fetch_all, fetch_one, get_connection


def next_correlativo(serie: str) -> int:
    row = fetch_one(
        "SELECT COALESCE(MAX(correlativo), 0) AS m FROM invoices WHERE serie = ?",
        (serie,),
    )
    return int(row["m"] if row else 0) + 1


def format_numero(prefijo: str, serie: str, correlativo: int) -> str:
    base = f"{serie}-{correlativo:04d}"
    return f"{prefijo}{base}" if prefijo else base


def list_invoices(search: str = "", estado: str | None = None) -> list:
    sql = (
        "SELECT i.id, i.numero, i.fecha_emision, i.base_imponible, "
        "i.importe_iva, i.importe_irpf, i.total, i.estado, "
        "cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente, "
        "i.client_id "
        "FROM invoices i JOIN clients cl ON cl.id = i.client_id WHERE 1=1 "
    )
    params: list = []
    if estado:
        sql += "AND i.estado = ? "
        params.append(estado)
    if search:
        sql += "AND (i.numero LIKE ? OR cl.nombre LIKE ? OR cl.apellidos LIKE ?) "
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += "ORDER BY i.fecha_emision DESC, i.correlativo DESC"
    return fetch_all(sql, params)


def get_invoice(invoice_id: int):
    return fetch_one(
        "SELECT i.*, cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente_nombre, "
        "cl.nif AS cliente_nif, cl.direccion AS cliente_direccion, "
        "cl.email AS cliente_email "
        "FROM invoices i JOIN clients cl ON cl.id = i.client_id "
        "WHERE i.id = ?",
        (invoice_id,),
    )


def get_lines(invoice_id: int) -> list:
    return fetch_all(
        "SELECT id, descripcion, cantidad, precio_unitario, subtotal "
        "FROM invoice_lines WHERE invoice_id = ? ORDER BY id",
        (invoice_id,),
    )


def create_invoice(header: dict, lines: list[dict]) -> int:
    """header debe contener numero, serie, correlativo, client_id, case_id,
    fecha_emision, fecha_vencimiento, base_imponible, tipo_iva, importe_iva,
    tipo_irpf, importe_irpf, total, estado, notas."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO invoices(numero, serie, correlativo, client_id, case_id, "
            "fecha_emision, fecha_vencimiento, base_imponible, tipo_iva, "
            "importe_iva, tipo_irpf, importe_irpf, total, estado, notas) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                header["numero"], header["serie"], header["correlativo"],
                header["client_id"], header.get("case_id"),
                header.get("fecha_emision") or date.today().isoformat(),
                header.get("fecha_vencimiento"),
                header["base_imponible"], header["tipo_iva"],
                header["importe_iva"], header["tipo_irpf"],
                header["importe_irpf"], header["total"],
                header.get("estado", "emitida"), header.get("notas"),
            ),
        )
        invoice_id = cur.lastrowid
        for line in lines:
            conn.execute(
                "INSERT INTO invoice_lines(invoice_id, descripcion, cantidad, "
                "precio_unitario, subtotal) VALUES(?, ?, ?, ?, ?)",
                (
                    invoice_id, line["descripcion"], line["cantidad"],
                    line["precio_unitario"], line["subtotal"],
                ),
            )
        conn.commit()
        return invoice_id
    finally:
        conn.close()


def update_invoice(invoice_id: int, header: dict, lines: list[dict]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE invoices SET client_id=?, case_id=?, fecha_emision=?, "
            "fecha_vencimiento=?, base_imponible=?, tipo_iva=?, importe_iva=?, "
            "tipo_irpf=?, importe_irpf=?, total=?, estado=?, notas=? WHERE id=?",
            (
                header["client_id"], header.get("case_id"),
                header.get("fecha_emision"), header.get("fecha_vencimiento"),
                header["base_imponible"], header["tipo_iva"],
                header["importe_iva"], header["tipo_irpf"],
                header["importe_irpf"], header["total"],
                header.get("estado", "emitida"), header.get("notas"),
                invoice_id,
            ),
        )
        conn.execute("DELETE FROM invoice_lines WHERE invoice_id = ?", (invoice_id,))
        for line in lines:
            conn.execute(
                "INSERT INTO invoice_lines(invoice_id, descripcion, cantidad, "
                "precio_unitario, subtotal) VALUES(?, ?, ?, ?, ?)",
                (
                    invoice_id, line["descripcion"], line["cantidad"],
                    line["precio_unitario"], line["subtotal"],
                ),
            )
        conn.commit()
    finally:
        conn.close()


def delete_invoice(invoice_id: int) -> None:
    execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))


def list_invoices_by_client(client_id: int) -> list:
    return fetch_all(
        "SELECT id, numero, fecha_emision, base_imponible, importe_iva, "
        "importe_irpf, total, estado FROM invoices WHERE client_id = ? "
        "ORDER BY fecha_emision DESC, correlativo DESC",
        (client_id,),
    )


def list_payments_by_client(client_id: int) -> list:
    return fetch_all(
        "SELECT p.id, p.fecha, p.importe, p.metodo, p.notas, i.numero "
        "FROM payments p LEFT JOIN invoices i ON i.id = p.invoice_id "
        "WHERE p.client_id = ? ORDER BY p.fecha DESC",
        (client_id,),
    )


def add_payment(client_id: int, importe: float, fecha: str, metodo: str,
                invoice_id: int | None = None, notas: str = "") -> int:
    return execute(
        "INSERT INTO payments(client_id, invoice_id, fecha, importe, metodo, notas) "
        "VALUES(?, ?, ?, ?, ?, ?)",
        (client_id, invoice_id, fecha, importe, metodo, notas),
    )


def delete_payment(payment_id: int) -> None:
    execute("DELETE FROM payments WHERE id = ?", (payment_id,))
