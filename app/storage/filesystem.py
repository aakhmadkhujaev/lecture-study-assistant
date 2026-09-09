"""Filesystem paths and safe material storage."""

from pathlib import Path


_INVALID_DIRECTORY_CHARACTERS = set('<>:"/\\|?*')


def validate_directory_name(value: str) -> str:
    """Return a safe, trimmed course or lecture directory name."""
    name = value.strip()
    if not name or name in {".", ".."}:
        raise ValueError("Name must contain at least one valid character.")
    if name[-1] in {".", " "}:
        raise ValueError("Name cannot end with a period or space.")
    if any(character in _INVALID_DIRECTORY_CHARACTERS or ord(character) < 32 for character in name):
        raise ValueError("Name contains characters that cannot be used in a folder name.")
    return name


def lecture_directory(storage_root: Path, course_name: str, lecture_name: str) -> Path:
    """Return the stable directory for a course lecture."""
    return storage_root / "courses" / course_name / lecture_name


def ensure_lecture_directory(
    storage_root: Path,
    course_name: str,
    lecture_name: str,
) -> Path:
    """Create or reuse a lecture directory and both material directories."""
    directory = lecture_directory(storage_root, course_name, lecture_name)
    (directory / "Original").mkdir(parents=True, exist_ok=True)
    (directory / "Guided_Material").mkdir(parents=True, exist_ok=True)
    return directory


def store_material(
    storage_root: Path,
    course_name: str,
    lecture_name: str,
    original_filename: str,
    content: bytes,
    material_type: str = "original",
) -> str:
    """Store content without overwriting an existing filename.

    Returns a path relative to ``storage_root`` for database persistence.
    """
    directory = ensure_lecture_directory(storage_root, course_name, lecture_name)
    filename = Path(original_filename).name
    if not filename or filename in {".", ".."}:
        raise ValueError("Uploaded file must have a valid filename.")

    if material_type not in {"original", "guided"}:
        raise ValueError("Material type must be 'original' or 'guided'.")
    material_directory = directory / (
        "Original" if material_type == "original" else "Guided_Material"
    )
    material_directory.mkdir(parents=True, exist_ok=True)
    candidate = material_directory / filename
    counter = 1
    while True:
        try:
            with candidate.open("xb") as output_file:
                output_file.write(content)
            break
        except FileExistsError:
            candidate = material_directory / (
                f"{Path(filename).stem} ({counter}){Path(filename).suffix}"
            )
            counter += 1

    return candidate.relative_to(storage_root).as_posix()
