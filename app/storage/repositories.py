"""SQLite repository operations for library entities."""

import sqlite3

from app.storage.models import Course, Lecture, Material


def _course_from_row(row: sqlite3.Row) -> Course:
    return Course(id=row["id"], name=row["name"], created_at=row["created_at"])


def _lecture_from_row(row: sqlite3.Row) -> Lecture:
    return Lecture(
        id=row["id"],
        course_id=row["course_id"],
        title=row["title"],
        created_at=row["created_at"],
    )


def _material_from_row(row: sqlite3.Row) -> Material:
    return Material(
        id=row["id"],
        lecture_id=row["lecture_id"],
        original_filename=row["original_filename"],
        stored_path=row["stored_path"],
        uploaded_at=row["uploaded_at"],
    )


def list_courses(connection: sqlite3.Connection) -> list[Course]:
    rows = connection.execute(
        "SELECT id, name, created_at FROM courses ORDER BY name"
    ).fetchall()
    return [_course_from_row(row) for row in rows]


def get_course(connection: sqlite3.Connection, course_id: int) -> Course | None:
    row = connection.execute(
        "SELECT id, name, created_at FROM courses WHERE id = ?",
        (course_id,),
    ).fetchone()
    return _course_from_row(row) if row else None


def insert_course(connection: sqlite3.Connection, name: str) -> Course:
    cursor = connection.execute("INSERT INTO courses (name) VALUES (?)", (name,))
    row = connection.execute(
        "SELECT id, name, created_at FROM courses WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return _course_from_row(row)


def list_lectures(connection: sqlite3.Connection, course_id: int) -> list[Lecture]:
    rows = connection.execute(
        """
        SELECT id, course_id, title, created_at
        FROM lectures
        WHERE course_id = ?
        ORDER BY title
        """,
        (course_id,),
    ).fetchall()
    return [_lecture_from_row(row) for row in rows]


def get_lecture(connection: sqlite3.Connection, lecture_id: int) -> Lecture | None:
    row = connection.execute(
        "SELECT id, course_id, title, created_at FROM lectures WHERE id = ?",
        (lecture_id,),
    ).fetchone()
    return _lecture_from_row(row) if row else None


def insert_lecture(
    connection: sqlite3.Connection,
    course_id: int,
    title: str,
) -> Lecture:
    cursor = connection.execute(
        "INSERT INTO lectures (course_id, title) VALUES (?, ?)",
        (course_id, title),
    )
    row = connection.execute(
        """
        SELECT id, course_id, title, created_at
        FROM lectures
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return _lecture_from_row(row)


def list_materials(connection: sqlite3.Connection, lecture_id: int) -> list[Material]:
    rows = connection.execute(
        """
        SELECT id, lecture_id, original_filename, stored_path, uploaded_at
        FROM materials
        WHERE lecture_id = ?
        ORDER BY uploaded_at, id
        """,
        (lecture_id,),
    ).fetchall()
    return [_material_from_row(row) for row in rows]


def get_material(connection: sqlite3.Connection, material_id: int) -> Material | None:
    row = connection.execute(
        """
        SELECT id, lecture_id, original_filename, stored_path, uploaded_at
        FROM materials
        WHERE id = ?
        """,
        (material_id,),
    ).fetchone()
    return _material_from_row(row) if row else None


def insert_material(
    connection: sqlite3.Connection,
    lecture_id: int,
    original_filename: str,
    stored_path: str,
) -> Material:
    cursor = connection.execute(
        """
        INSERT INTO materials (lecture_id, original_filename, stored_path)
        VALUES (?, ?, ?)
        """,
        (lecture_id, original_filename, stored_path),
    )
    row = connection.execute(
        """
        SELECT id, lecture_id, original_filename, stored_path, uploaded_at
        FROM materials
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return _material_from_row(row)
