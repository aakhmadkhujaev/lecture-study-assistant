"""Streamlit entry point for Lecture Study Assistant."""

from app.ui.home import render_home


def main() -> None:
    """Render the application."""
    render_home()


if __name__ == "__main__":
    main()
