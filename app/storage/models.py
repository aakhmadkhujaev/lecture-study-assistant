"""Data models returned by the library storage layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Course:
    """A course in the local study library."""

    id: int
    name: str
    created_at: str


@dataclass(frozen=True, slots=True)
class Lecture:
    """A lecture belonging to a course."""

    id: int
    course_id: int
    title: str
    created_at: str


@dataclass(frozen=True, slots=True)
class Material:
    """A material file associated with a lecture."""

    id: int
    lecture_id: int
    original_filename: str
    stored_path: str
    uploaded_at: str
    material_type: str = "original"
