import io
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import (  # type: ignore[import-untyped]
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import cm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.cidfonts import UnicodeCIDFont  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.crud.trip import create_trip, delete_trip, get_trip, get_user_trips
from backend.database import get_db
from backend.models.trip import Trip
from backend.models.user import User
from backend.schemas.trip import TripCreate, TripOut

router = APIRouter(prefix="/api/trips", tags=["trips"])
_PDF_FONT_NAME: str | None = None


def _check_ownership(trip: Trip, user: User) -> None:
    if trip.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该行程"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trip_endpoint(
    trip_in: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    trip = await create_trip(db, current_user.id, trip_in)
    return {"trip_id": trip.id}


@router.get("")
async def list_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    trips = await get_user_trips(db, current_user.id)
    items = []
    for t in trips:
        items.append(
            {
                "id": t.id,
                "title": t.title,
                "destination": t.destination,
                "start_date": t.start_date.isoformat(),
                "end_date": t.end_date.isoformat(),
            }
        )
    return {"total": len(items), "items": items}


@router.get("/{trip_id}")
async def get_trip_detail(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripOut:
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
) -> dict[str, str]:
    trip = await get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="行程不存在")
    _check_ownership(trip, current_user)
    await delete_trip(db, trip)
    return {"message": "行程已删除"}


def _build_pdf(trip: Trip) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    font_name = _resolve_pdf_font()

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
    elements.append(Paragraph(_pdf_text(trip.title), title_style))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"目的地：{_pdf_text(trip.destination)}", body_style))
    elements.append(
        Paragraph(
            f"日期：{trip.start_date.isoformat()} ~ {trip.end_date.isoformat()}",
            body_style,
        )
    )
    if trip.budget_total is not None:
        elements.append(Paragraph(f"预算：{trip.budget_total}", body_style))
    if trip.budget_breakdown:
        elements.append(
            Paragraph(f"预算明细：{_pdf_text(trip.budget_breakdown)}", body_style)
        )
    elements.append(Spacer(1, 0.8 * cm))

    for day in sorted(trip.days, key=lambda d: d.day_index):
        elements.append(
            Paragraph(f"第 {day.day_index} 天 - {day.date.isoformat()}", heading_style)
        )
        if day.weather:
            elements.append(Paragraph(f"天气：{_pdf_text(day.weather)}", body_style))
        for act in sorted(day.activities, key=lambda a: a.order_index):
            line = f"  {act.order_index}. {_pdf_text(act.spot_name)}"
            if act.time_slot:
                line += f" ({_pdf_text(act.time_slot)})"
            if act.transport:
                line += f" [交通：{_pdf_text(act.transport)}]"
            if act.estimated_cost is not None:
                line += f" - 费用：{act.estimated_cost}"
            elements.append(Paragraph(line, body_style))
            if act.notes:
                elements.append(
                    Paragraph(f"     备注：{_pdf_text(act.notes)}", body_style)
                )
        elements.append(Spacer(1, 0.4 * cm))

    doc.build(elements)
    return buffer.getvalue()


def _resolve_pdf_font() -> str:
    global _PDF_FONT_NAME
    if _PDF_FONT_NAME is not None:
        return _PDF_FONT_NAME

    try:
        pdfmetrics.getFont("SimSun")
        _PDF_FONT_NAME = "SimSun"
        return "SimSun"
    except KeyError:
        try:
            pdfmetrics.registerFont(TTFont("SimSun", "simsun.ttc"))
            _PDF_FONT_NAME = "SimSun"
            return "SimSun"
        except Exception:
            try:
                pdfmetrics.getFont("STSong-Light")
            except KeyError:
                pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            _PDF_FONT_NAME = "STSong-Light"
            return "STSong-Light"


def _pdf_text(value: object) -> str:
    return escape(str(value))


@router.get("/{trip_id}/export")
async def export_trip_pdf(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
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
