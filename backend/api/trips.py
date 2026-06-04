import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.crud.trip import create_trip, delete_trip, get_trip, get_user_trips
from backend.database import get_db
from backend.models.user import User
from backend.schemas.trip import TripCreate, TripOut

router = APIRouter(prefix="/api/trips", tags=["trips"])


def _check_ownership(trip, user: User) -> None:
    if trip.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该行程"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trip_endpoint(
    trip_in: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = await create_trip(db, current_user.id, trip_in)
    return {"trip_id": trip.id}


@router.get("")
async def list_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trips = await get_user_trips(db, current_user.id)
    items = []
    for t in trips:
        items.append({
            "id": t.id,
            "title": t.title,
            "destination": t.destination,
            "start_date": t.start_date.isoformat(),
            "end_date": t.end_date.isoformat(),
        })
    return {"total": len(items), "items": items}


@router.get("/{trip_id}")
async def get_trip_detail(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = await get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="行程不存在")
    _check_ownership(trip, current_user)
    return TripOut.model_validate(trip)


@router.delete("/{trip_id}")
async def delete_trip_endpoint(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = await get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="行程不存在")
    _check_ownership(trip, current_user)
    await delete_trip(db, trip)
    return {"message": "行程已删除"}


def _build_pdf(trip) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    try:
        pdfmetrics.getFont("SimSun")
    except KeyError:
        try:
            pdfmetrics.registerFont(TTFont("SimSun", "simsun.ttc"))
        except Exception:
            pass

    font_name = "SimSun" if "SimSun" in pdfmetrics.getRegisteredFontNames() else "Helvetica"

    title_style = ParagraphStyle(
        "TripTitle", parent=styles["Title"], fontName=font_name, fontSize=18
    )
    heading_style = ParagraphStyle(
        "TripHeading", parent=styles["Heading2"], fontName=font_name, fontSize=14
    )
    body_style = ParagraphStyle(
        "TripBody", parent=styles["Normal"], fontName=font_name, fontSize=11
    )

    elements = []
    elements.append(Paragraph(trip.title, title_style))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"Destination: {trip.destination}", body_style))
    elements.append(Paragraph(
        f"Date: {trip.start_date.isoformat()} ~ {trip.end_date.isoformat()}", body_style
    ))
    if trip.budget_total is not None:
        elements.append(Paragraph(f"Budget: {trip.budget_total}", body_style))
    if trip.budget_breakdown:
        elements.append(Paragraph(f"Breakdown: {trip.budget_breakdown}", body_style))
    elements.append(Spacer(1, 0.8 * cm))

    for day in sorted(trip.days, key=lambda d: d.day_index):
        elements.append(Paragraph(
            f"Day {day.day_index} - {day.date.isoformat()}", heading_style
        ))
        if day.weather:
            elements.append(Paragraph(f"Weather: {day.weather}", body_style))
        for act in sorted(day.activities, key=lambda a: a.order_index):
            line = f"  {act.order_index}. {act.spot_name}"
            if act.time_slot:
                line += f" ({act.time_slot})"
            if act.transport:
                line += f" [Transport: {act.transport}]"
            if act.estimated_cost is not None:
                line += f" - Cost: {act.estimated_cost}"
            elements.append(Paragraph(line, body_style))
            if act.notes:
                elements.append(Paragraph(f"     Notes: {act.notes}", body_style))
        elements.append(Spacer(1, 0.4 * cm))

    doc.build(elements)
    return buffer.getvalue()


@router.get("/{trip_id}/export")
async def export_trip_pdf(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = await get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="行程不存在")
    _check_ownership(trip, current_user)
    pdf_bytes = _build_pdf(trip)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="trip_{trip_id}.pdf"'},
    )
