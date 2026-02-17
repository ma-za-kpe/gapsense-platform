"""
School Registration API

Endpoints for school self-service registration and invitation code generation.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models.schools import GESSchool, School, SchoolInvitation
from gapsense.engagement.invitation_codes import generate_invitation_code

router = APIRouter(prefix="/schools", tags=["schools"])


# Pydantic models
class GESSchoolResponse(BaseModel):
    """GES school search result."""

    ges_id: int
    name: str
    region: str
    district: str
    school_type: str

    class Config:
        from_attributes = True


class SchoolSearchResponse(BaseModel):
    """School search API response."""

    schools: list[GESSchoolResponse]


class SchoolRegistrationRequest(BaseModel):
    """School registration form data."""

    school_name: str = Field(..., min_length=3, max_length=300)
    ges_school_id: int | None = None
    headmaster_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+233\d{9}$")  # Ghana phone format
    num_teachers: int = Field(..., ge=1, le=1000)


class SchoolRegistrationResponse(BaseModel):
    """School registration success response."""

    invitation_code: str
    message: str
    school_id: str


@router.get("/search", response_model=SchoolSearchResponse)
async def search_ges_schools(
    q: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SchoolSearchResponse:
    """
    Search GES schools for autocomplete.

    Returns up to 10 matching schools from GES database.
    """
    # Validate query
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # Search GES schools (case-insensitive, partial match)
    stmt = select(GESSchool).where(GESSchool.name.ilike(f"%{q}%")).limit(10)
    result = await db.execute(stmt)
    schools = result.scalars().all()

    return SchoolSearchResponse(schools=[GESSchoolResponse.model_validate(s) for s in schools])


@router.post("/register", response_model=SchoolRegistrationResponse, status_code=201)
async def register_school(
    data: SchoolRegistrationRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SchoolRegistrationResponse:
    """
    Register a new school and generate invitation code.

    Creates:
    - School record
    - Invitation code for teachers to join

    Returns invitation code for headmaster to share with teachers.
    """
    # Get district_id from GES school if provided
    district_id = None
    if data.ges_school_id:
        # Verify GES school exists
        stmt = select(GESSchool).where(GESSchool.ges_id == data.ges_school_id)
        result = await db.execute(stmt)
        ges_school = result.scalar_one_or_none()

        if not ges_school:
            raise HTTPException(
                status_code=404, detail=f"GES school with ID {data.ges_school_id} not found"
            )

        # Get or create district based on GES data
        # For MVP, we'll use a default district if not found
        # TODO: Implement proper district resolution from GES data
        from gapsense.core.models.schools import District, Region

        # Get default region/district (assuming MVP setup)
        district_stmt = select(District).limit(1)
        district_result = await db.execute(district_stmt)
        district = district_result.scalar_one_or_none()
        if district:
            district_id = district.id
        else:
            # Create default district if none exists (MVP fallback)
            region_stmt = select(Region).limit(1)
            region_result = await db.execute(region_stmt)
            region = region_result.scalar_one_or_none()
            if region:
                district = District(region_id=region.id, name="Default District")
                db.add(district)
                await db.flush()
                district_id = district.id

    if not district_id:
        raise HTTPException(
            status_code=400,
            detail="Could not determine district. Please provide region/district information.",
        )

    # Create school record
    school = School(
        name=data.school_name,
        district_id=district_id,
        school_type="jhs",  # Default type, can be made dynamic
        ges_school_id=data.ges_school_id,
        registered_by=data.headmaster_name,
        registered_at=datetime.now(UTC).isoformat(),
        phone=data.phone,
        is_active=True,
    )
    db.add(school)
    await db.flush()  # Get school.id

    # Generate invitation code
    invitation_code = await generate_invitation_code(data.school_name)

    # Create invitation record
    invitation = SchoolInvitation(
        school_id=school.id,
        invitation_code=invitation_code,
        created_by=data.headmaster_name,
        max_teachers=data.num_teachers,
        teachers_joined=0,
        is_active=True,
    )
    db.add(invitation)

    await db.commit()
    await db.refresh(school)
    await db.refresh(invitation)

    # Success message
    message = (
        f"School '{data.school_name}' successfully registered! "
        f"Share invitation code {invitation_code} with your teachers to join."
    )

    return SchoolRegistrationResponse(
        invitation_code=invitation_code,
        message=message,
        school_id=str(school.id),
    )
