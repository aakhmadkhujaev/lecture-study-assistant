"""Streamlit views for the course and lecture library."""

from pathlib import Path

import streamlit as st

from config.settings import Settings

from app.ai.generator import StudyGuideGenerationError
from app.ai.provider import AIProviderError
from app.ai.schemas import StudyGuide
from app.ai.service import (
    StudyGuideAlreadyExistsError,
    StudyGuidePersistenceError,
    generate_lecture_study_guide,
    load_study_guide,
)
from app.pdf.service import generate_lecture_study_guide_pdf, study_guide_pdf_path
from app.services.library_service import (
    LibraryError,
    create_course,
    create_lecture,
    delete_course,
    delete_lecture,
    extract_material_content,
    get_course_by_id,
    get_courses,
    get_lecture_by_id,
    get_lectures,
    get_materials,
    initialize_library,
    upload_material,
)
from app.visuals.renderer import render_visual_text


def render_library(settings: Settings) -> None:
    """Render the active library view."""
    try:
        initialize_library(settings)
    except LibraryError as error:
        st.error(str(error))
        return

    st.session_state.setdefault("library_page", "courses")
    page = st.session_state["library_page"]
    if page == "course":
        _render_course_page(settings)
    elif page == "lecture":
        _render_lecture_page(settings)
    else:
        _render_courses_page(settings)


def _render_courses_page(settings: Settings) -> None:
    st.header("Courses")
    st.write("Choose a course to view its lectures or create a new course.")

    if st.button("Create Course", type="primary"):
        st.session_state["show_create_course"] = True

    if st.session_state.get("show_create_course", False):
        with st.form("create_course_form"):
            course_name = st.text_input("Course name")
            submitted = st.form_submit_button("Save Course")
        if submitted:
            try:
                course = create_course(settings, course_name)
            except LibraryError as error:
                st.error(str(error))
            else:
                st.session_state["show_create_course"] = False
                st.session_state["selected_course_id"] = course.id
                st.session_state["library_page"] = "course"
                st.rerun()

    try:
        courses = get_courses(settings)
    except LibraryError as error:
        st.error(str(error))
        return

    st.subheader("Existing courses")
    if not courses:
        st.info("No courses have been created yet.")
        return

    for course in courses:
        if st.button(course.name, key=f"open-course-{course.id}", use_container_width=True):
            st.session_state["selected_course_id"] = course.id
            st.session_state["library_page"] = "course"
            st.rerun()


def _render_course_page(settings: Settings) -> None:
    course_id = st.session_state.get("selected_course_id")
    if course_id is None:
        _go_to_courses()
        return

    try:
        course = get_course_by_id(settings, course_id)
        lectures = get_lectures(settings, course.id)
    except LibraryError as error:
        st.error(str(error))
        if st.button("Back to Courses"):
            _go_to_courses()
        return

    if st.button("Back to Courses"):
        _go_to_courses()
        return

    st.header(course.name)
    st.caption("Lectures in this course")

    if st.button("Create Lecture", type="primary"):
        st.session_state["show_create_lecture"] = True

    if st.session_state.get("show_create_lecture", False):
        with st.form("create_lecture_form"):
            lecture_title = st.text_input("Lecture name or number")
            submitted = st.form_submit_button("Save Lecture")
        if submitted:
            try:
                create_lecture(settings, course.id, lecture_title)
            except LibraryError as error:
                st.error(str(error))
            else:
                st.session_state["show_create_lecture"] = False
                st.rerun()

    if not lectures:
        st.info("No lectures have been created for this course yet.")
    else:
        for lecture in lectures:
            if st.button(
                lecture.title,
                key=f"open-lecture-{lecture.id}",
                use_container_width=True,
            ):
                st.session_state["selected_lecture_id"] = lecture.id
                st.session_state["library_page"] = "lecture"
                st.rerun()

    st.divider()
    st.subheader("Delete course")
    confirmed = st.checkbox(
        "I understand that deleting this course removes its lectures and stored files.",
        key=f"confirm-delete-course-{course.id}",
    )
    if confirmed and st.button("Delete Course", key=f"delete-course-{course.id}"):
        try:
            delete_course(settings, course.id)
        except LibraryError as error:
            st.error(str(error))
        else:
            _go_to_courses()


def _render_lecture_page(settings: Settings) -> None:
    lecture_id = st.session_state.get("selected_lecture_id")
    if lecture_id is None:
        _go_to_courses()
        return

    try:
        lecture = get_lecture_by_id(settings, lecture_id)
        course = get_course_by_id(settings, lecture.course_id)
        materials = get_materials(settings, lecture.id)
    except LibraryError as error:
        st.error(str(error))
        if st.button("Back to Courses"):
            _go_to_courses()
        return

    if st.button(f"Back to {course.name}"):
        st.session_state["selected_course_id"] = course.id
        st.session_state["library_page"] = "course"
        st.rerun()

    st.header(lecture.title)
    st.caption(course.name)

    _render_study_guide_controls(settings, lecture.id)

    _render_material_category(settings, lecture.id, materials, "original", "Original Material")
    _render_material_category(settings, lecture.id, materials, "guided", "Guided Material")

    extracted_document = st.session_state.get("extracted_document")
    extracted_material_id = st.session_state.get("extracted_material_id")
    if extracted_document is not None and extracted_material_id in {
        material.id for material in materials
    }:
        st.subheader(f"Extracted content: {extracted_document.filename}")
        if extracted_document.extraction_method == "ocr":
            st.info("This material includes OCR-extracted content.")
        for section in extracted_document.sections:
            source_label = (
                f"{section.source_type.title()} {section.source_index}"
            )
            with st.expander(source_label, expanded=True):
                st.text(section.text)

    _render_material_uploader(settings, lecture.id, "original", "Upload Original")
    _render_material_uploader(settings, lecture.id, "guided", "Upload Guided Material")

    st.divider()
    st.subheader("Delete lecture")
    confirmed = st.checkbox(
        "I understand that deleting this lecture removes its stored files.",
        key=f"confirm-delete-lecture-{lecture.id}",
    )
    if confirmed and st.button("Delete Lecture", key=f"delete-lecture-{lecture.id}"):
        try:
            delete_lecture(settings, lecture.id)
        except LibraryError as error:
            st.error(str(error))
        else:
            st.session_state["selected_course_id"] = course.id
            st.session_state["library_page"] = "course"
            st.rerun()


def _render_study_guide_controls(settings: Settings, lecture_id: int) -> None:
    """Render generation, regeneration confirmation, and saved guide output."""
    try:
        saved_guide = load_study_guide(settings, lecture_id)
    except StudyGuidePersistenceError as error:
        st.error(str(error))
        saved_guide = None

    st.subheader("Study Guide")
    if saved_guide is not None:
        st.success("A structured study guide is saved for this lecture.")
        regenerate = st.checkbox(
            "I understand that regeneration replaces the existing Study_Guide.json.",
            key=f"confirm-regenerate-{lecture_id}",
        )
    else:
        regenerate = False

    if st.button("Generate Study Guide", key=f"generate-guide-{lecture_id}"):
        try:
            guide, path = generate_lecture_study_guide(
                settings,
                lecture_id,
                overwrite=regenerate,
            )
        except StudyGuideAlreadyExistsError as error:
            st.warning(str(error))
        except LibraryError as error:
            st.error(str(error))
        except (AIProviderError, StudyGuideGenerationError, StudyGuidePersistenceError) as error:
            st.error(str(error))
        except Exception:
            st.error("The study guide could not be generated. Check the application logs.")
        else:
            st.session_state[f"study-guide-{lecture_id}"] = guide
            st.success(f"Study guide saved to {path.name}.")

    guide = st.session_state.get(f"study-guide-{lecture_id}", saved_guide)
    if guide is not None:
        pdf_path = study_guide_pdf_path(settings, lecture_id)
        overwrite_pdf = False
        if pdf_path.exists():
            overwrite_pdf = st.checkbox(
                "I understand that generating the PDF replaces the existing Study_Guide.pdf.",
                key=f"confirm-regenerate-pdf-{lecture_id}",
            )
        if st.button("Generate PDF", key=f"generate-pdf-{lecture_id}"):
            try:
                generated_pdf_path = generate_lecture_study_guide_pdf(
                    settings,
                    lecture_id,
                    overwrite=overwrite_pdf,
                )
            except FileExistsError as error:
                st.warning(str(error))
            except (LibraryError, StudyGuidePersistenceError, OSError) as error:
                st.error(str(error))
            else:
                st.success(f"PDF saved to {generated_pdf_path}.")
        _render_pdf_download(pdf_path)
        _render_study_guide(guide)
    else:
        st.info("Generate a Study Guide before creating its PDF.")


def _render_pdf_download(pdf_path: Path) -> None:
    """Offer the persisted PDF for download without regenerating it."""
    if not pdf_path.exists():
        st.info("Generate the PDF first to download the Study Guide PDF.")
        return
    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError as error:
        st.error(f"The Study Guide PDF could not be read: {error}")
        return
    st.download_button(
        "Download Study Guide PDF",
        data=pdf_bytes,
        file_name="Study_Guide.pdf",
        mime="application/pdf",
        key=f"download-study-guide-pdf-{pdf_path}",
    )


def _render_material_category(
    settings: Settings,
    lecture_id: int,
    materials: list[object],
    material_type: str,
    title: str,
) -> None:
    st.subheader(title)
    category_materials = [item for item in materials if item.material_type == material_type]
    if not category_materials:
        st.info(f"No {material_type} materials have been uploaded for this lecture.")
        return
    for material in category_materials:
        material_column, action_column = st.columns([3, 1])
        material_column.write(material.original_filename)
        material_column.caption(f"{material.material_type.title()} • {material.stored_path}")
        if action_column.button(
            "Extract Content",
            key=f"extract-material-{material.id}",
        ):
            try:
                document = extract_material_content(settings, material.id)
            except LibraryError as error:
                st.error(f"{material.original_filename}: {error}")
            else:
                st.session_state["extracted_document"] = document
                st.session_state["extracted_material_id"] = material.id
                method = document.extraction_method
                if method == "ocr":
                    st.info(
                        "Text extraction found no readable text for part of this material. OCR was used."
                    )
                st.rerun()


def _render_material_uploader(
    settings: Settings,
    lecture_id: int,
    material_type: str,
    label: str,
) -> None:
    uploaded_files = st.file_uploader(
        f"{label}: choose PDF, DOCX, or PPTX files",
        type=["pdf", "docx", "pptx"],
        accept_multiple_files=True,
        key=f"upload-{material_type}-materials-{lecture_id}",
    )
    if not uploaded_files or not st.button(
        label,
        key=f"save-{material_type}-materials-{lecture_id}",
    ):
        return
    saved_count = 0
    for uploaded_file in uploaded_files:
        try:
            upload_material(
                settings,
                lecture_id,
                uploaded_file.name,
                uploaded_file.getvalue(),
                material_type=material_type,
            )
        except LibraryError as error:
            st.error(f"{uploaded_file.name}: {error}")
        else:
            saved_count += 1
    if saved_count:
        st.success(f"Saved {saved_count} {material_type} material(s).")
        st.rerun()


def _render_study_guide(guide: StudyGuide) -> None:
    """Display the structured guide without converting it to Markdown/PDF."""
    if guide.lecture_overview.strip():
        st.markdown("### Lecture Overview")
        st.write(guide.lecture_overview)
    _render_text_list("Learning Objectives", guide.learning_objectives)
    _render_mental_model(guide)
    _render_concepts(guide)
    _render_definitions(guide)
    _render_formulas(guide)
    _render_real_world_applications(guide)
    _render_engineering_connections(guide)
    _render_exam_topics(guide)
    _render_confusions(guide)
    _render_questions(guide)
    _render_text_list("Quick Revision", guide.quick_revision)
    _render_gaps(guide)
    _render_visual_models(guide)
    if guide.sources:
        with st.expander("Sources"):
            for source in guide.sources:
                st.write(f"{source.filename} - {source.source_type} {source.source_index}")


def _render_visual_models(guide: StudyGuide) -> None:
    if not guide.visual_models:
        return
    st.subheader("Visual Mental Models")
    for visual in guide.visual_models:
        with st.expander(visual.title, expanded=True):
            st.write(f"Purpose: {visual.purpose}")
            st.code(render_visual_text(visual), language="text")
            st.write(visual.explanation)
            _render_references(visual.source_references)


def _render_mental_model(guide: StudyGuide) -> None:
    mental_model = guide.mental_model
    if not _has_meaningful_content(
        mental_model.core_idea,
        mental_model.components,
        mental_model.relationships,
        mental_model.how_it_works,
        mental_model.key_takeaway,
    ):
        return
    with st.expander("Mental Model", expanded=True):
        if mental_model.core_idea.strip():
            st.markdown("**Core idea**")
            st.write(mental_model.core_idea)
        if mental_model.components:
            st.markdown("**Components**")
            _render_text_list_values(mental_model.components)
        if mental_model.relationships:
            st.markdown("**Relationships**")
            _render_text_list_values(mental_model.relationships)
        if mental_model.how_it_works.strip():
            st.markdown("**How it works**")
            st.write(mental_model.how_it_works)
        if mental_model.key_takeaway.strip():
            st.markdown("**Key takeaway**")
            st.write(mental_model.key_takeaway)


def _render_real_world_applications(guide: StudyGuide) -> None:
    applications = [
        application
        for application in guide.real_world_applications
        if _has_meaningful_content(
            application.title,
            application.problem,
            application.solution,
            application.why_this_concept,
            application.impact,
        )
    ]
    if not applications:
        return
    with st.expander("Real-World Applications", expanded=True):
        for application in applications:
            st.markdown(f"**{application.title}**")
            st.write(f"Problem: {application.problem}")
            st.write(f"Solution: {application.solution}")
            st.write(f"Why this concept: {application.why_this_concept}")
            st.write(f"Impact: {application.impact}")
            _render_references(application.source_references)


def _render_engineering_connections(guide: StudyGuide) -> None:
    connections = [
        connection
        for connection in guide.engineering_connections
        if _has_meaningful_content(
            connection.concept,
            connection.real_world_problem,
            connection.engineering_decision,
            connection.implementation,
            connection.trade_offs,
        )
    ]
    if not connections:
        return
    with st.expander("Engineering Connections", expanded=True):
        for connection in connections:
            st.markdown(f"**{connection.concept}**")
            st.write(f"Real-world problem: {connection.real_world_problem}")
            st.write(f"Engineering decision: {connection.engineering_decision}")
            st.write(f"Implementation: {connection.implementation}")
            st.write(f"Trade-offs: {connection.trade_offs}")
            _render_references(connection.source_references)


def _render_text_list(title: str, values: list[str]) -> None:
    if not values:
        return
    with st.expander(title, expanded=True):
        for value in values:
            st.write(f"- {value}")


def _render_text_list_values(values: list[str]) -> None:
    for value in values:
        if value.strip():
            st.write(f"- {value}")


def _has_meaningful_content(*values: str | list[str]) -> bool:
    return any(
        value.strip() if isinstance(value, str) else any(item.strip() for item in value)
        for value in values
    )


def _render_concepts(guide: StudyGuide) -> None:
    if not guide.key_concepts:
        return
    with st.expander("Key Concepts", expanded=True):
        for item in guide.key_concepts:
            st.markdown(f"**{item.name}** ({item.importance})")
            st.write(item.definition)
            st.write(item.explanation)
            if item.example:
                st.write(f"Example: {item.example}")
            if item.use_when:
                st.write(f"Use when: {item.use_when}")
            if item.avoid_when:
                st.write(f"Avoid when: {item.avoid_when}")
            _render_references(item.source_references)


def _render_definitions(guide: StudyGuide) -> None:
    if not guide.definitions:
        return
    with st.expander("Important Definitions"):
        for item in guide.definitions:
            st.markdown(f"**{item.term}**: {item.simple_definition}")
            _render_references(item.source_references)


def _render_formulas(guide: StudyGuide) -> None:
    if not guide.formulas:
        return
    with st.expander("Formulas & Algorithms"):
        for item in guide.formulas:
            st.markdown(f"**{item.formula}**")
            st.write(item.meaning)
            _render_references(item.source_references)


def _render_exam_topics(guide: StudyGuide) -> None:
    if not guide.exam_topics:
        return
    with st.expander("Important for Revision"):
        for item in guide.exam_topics:
            st.markdown(f"**{item.topic}**: {item.why_important}")
            _render_references(item.source_references)


def _render_confusions(guide: StudyGuide) -> None:
    if not guide.common_confusions:
        return
    with st.expander("Common Confusions"):
        for item in guide.common_confusions:
            st.markdown(f"**{item.topic}**")
            st.write(f"Confusion: {item.confusion}")
            st.write(f"Clarification: {item.clarification}")
            _render_references(item.source_references)


def _render_questions(guide: StudyGuide) -> None:
    if not guide.practice_questions:
        return
    with st.expander("Practice Questions"):
        for item in guide.practice_questions:
            st.markdown(f"**{item.question_type}: {item.question}**")
            st.write(f"Model answer: {item.model_answer}")
            _render_references(item.source_references)


def _render_gaps(guide: StudyGuide) -> None:
    if not guide.knowledge_gaps:
        return
    with st.expander("Knowledge Gaps"):
        for item in guide.knowledge_gaps:
            st.markdown(f"**{item.topic}**")
            st.write(item.reason)
            st.write(f"Missing: {item.what_is_missing}")
            st.write(f"Recommended action: {item.recommended_action}")
            _render_references(item.source_references)


def _render_references(references: list[object]) -> None:
    labels = [
        f"{reference.filename} - {reference.source_type} {reference.source_index}"
        for reference in references
    ]
    if labels:
        st.caption("Sources: " + "; ".join(labels))


def _go_to_courses() -> None:
    st.session_state["library_page"] = "courses"
    st.session_state.pop("selected_course_id", None)
    st.session_state.pop("selected_lecture_id", None)
    st.rerun()
