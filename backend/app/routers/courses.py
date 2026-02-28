from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.routers.textbooks import _job_status

router = APIRouter(prefix="/api/courses", tags=["courses"])

MATH_LIBRARY_NAME = "Math Library"


def get_storage():
    from app.services.storage import MetadataStore
    return MetadataStore()


async def get_math_library_id(storage) -> Optional[str]:
    """Get the ID of the protected Math Library course."""
    courses = await storage.list_courses()
    for c in courses:
        if c['name'] == MATH_LIBRARY_NAME:
            return c['id']
    return None


class CourseCreateRequest(BaseModel):
    name: str


class CourseUpdateRequest(BaseModel):
    name: str


@router.post("/", status_code=200)
async def create_course(body: CourseCreateRequest):
    """Create a new course. Returns the created course."""
    storage = get_storage()
    await storage.initialize()

    # Check for duplicates BEFORE calling create_course (INSERT OR IGNORE won't error)
    existing = await storage.list_courses()
    for c in existing:
        if c['name'] == body.name:
            raise HTTPException(status_code=409, detail="A course with that name already exists")

    course_id = await storage.create_course(body.name)
    course = await storage.get_course(course_id)
    if not course:
        raise HTTPException(status_code=500, detail="Failed to retrieve created course")
    return course


@router.get("/", response_model=list)
async def list_courses():
    """List all courses with textbook and material counts."""
    storage = get_storage()
    await storage.initialize()

    courses = await storage.list_courses()
    result = []
    for c in courses:
        textbooks = await storage.get_course_textbooks(c['id'])
        materials = await storage.list_university_materials(c['id'])
        result.append({
            "id": c['id'],
            "name": c['name'],
            "created_at": c['created_at'],
            "textbook_count": len(textbooks),
            "material_count": len(materials),
        })
    return result


@router.get("/{course_id}")
async def get_course(course_id: str):
    """Get a single course by ID with counts."""
    storage = get_storage()
    await storage.initialize()

    course = await storage.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    textbooks = await storage.get_course_textbooks(course_id)
    materials = await storage.list_university_materials(course_id)
    return {
        "id": course['id'],
        "name": course['name'],
        "created_at": course['created_at'],
        "textbook_count": len(textbooks),
        "material_count": len(materials),
    }


@router.put("/{course_id}")
async def update_course(course_id: str, body: CourseUpdateRequest):
    """Update course name. Blocks renaming the Math Library."""
    storage = get_storage()
    await storage.initialize()

    course = await storage.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course['name'] == MATH_LIBRARY_NAME:
        raise HTTPException(status_code=403, detail="Cannot rename the Math Library course")

    # Check if new name already taken by another course
    existing = await storage.list_courses()
    for c in existing:
        if c['name'] == body.name and c['id'] != course_id:
            raise HTTPException(status_code=409, detail="A course with that name already exists")

    updated = await storage.update_course(course_id, body.name)
    return updated


@router.delete("/{course_id}")
async def delete_course(course_id: str):
    """Cascade delete a course. Blocks deleting the Math Library or courses with active uploads."""
    storage = get_storage()
    await storage.initialize()

    course = await storage.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course['name'] == MATH_LIBRARY_NAME:
        raise HTTPException(status_code=403, detail="Cannot delete the Math Library course")

    # Check for active uploads
    course_textbooks = await storage.get_course_textbooks(course_id)
    course_textbook_ids = {tb['id'] for tb in course_textbooks}
    active_jobs = [
        job_id for job_id, status_info in _job_status.items()
        if status_info.get('status') == 'processing'
        and status_info.get('textbook_id') in course_textbook_ids
    ]
    if active_jobs:
        raise HTTPException(status_code=409, detail="Cannot delete course while textbooks are being uploaded")

    await storage.delete_course(course_id)
    return {"message": "Course deleted successfully"}
