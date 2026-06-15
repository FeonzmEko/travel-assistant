import io
import re
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_LEFT, TA_RIGHT  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.lib.units import cm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.cidfonts import UnicodeCIDFont  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
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

# 行程手册视觉系统：单一主色（松绿青）+ 赤陶橙点缀，避免炫技渐变
_C_PRIMARY = colors.HexColor("#0F5C57")
_C_PRIMARY_DARK = colors.HexColor("#0A3F3B")
_C_ACCENT = colors.HexColor("#C2703D")
_C_INK = colors.HexColor("#22302E")
_C_MUTED = colors.HexColor("#6B7B79")
_C_STRIPE = colors.HexColor("#EAF3F1")
_C_PAPER = colors.HexColor("#F4F1EA")
_C_LINE = colors.HexColor("#DCE6E4")
_C_ON_PRIMARY = colors.HexColor("#FFFFFF")
_C_ON_PRIMARY_SOFT = colors.HexColor("#CFE6E2")


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


def _fmt_amount(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def _parse_budget_breakdown(raw: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for chunk in re.split(r"[,，、]", raw):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = re.split(r"[:：]", chunk, maxsplit=1)
        if len(parts) == 2:
            items.append((parts[0].strip(), parts[1].strip()))
        else:
            items.append((chunk, ""))
    return items


def _make_styles(font_name: str) -> dict[str, ParagraphStyle]:
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName=font_name,
            fontSize=23,
            leading=30,
            textColor=_C_ON_PRIMARY,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName=font_name,
            fontSize=11,
            leading=18,
            textColor=_C_ON_PRIMARY_SOFT,
        ),
        "stat_num": ParagraphStyle(
            "stat_num",
            fontName=font_name,
            fontSize=17,
            leading=20,
            alignment=TA_LEFT,
            textColor=_C_PRIMARY,
        ),
        "stat_label": ParagraphStyle(
            "stat_label",
            fontName=font_name,
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
            textColor=_C_MUTED,
        ),
        "section": ParagraphStyle(
            "section",
            fontName=font_name,
            fontSize=13,
            leading=18,
            textColor=_C_PRIMARY_DARK,
        ),
        "day_num": ParagraphStyle(
            "day_num",
            fontName=font_name,
            fontSize=13,
            leading=17,
            textColor=_C_ON_PRIMARY,
        ),
        "day_date": ParagraphStyle(
            "day_date",
            fontName=font_name,
            fontSize=9,
            leading=12,
            textColor=_C_ON_PRIMARY_SOFT,
        ),
        "day_weather": ParagraphStyle(
            "day_weather",
            fontName=font_name,
            fontSize=9.5,
            leading=14,
            alignment=TA_RIGHT,
            textColor=_C_ON_PRIMARY,
        ),
        "time": ParagraphStyle(
            "time",
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=_C_PRIMARY,
        ),
        "spot": ParagraphStyle(
            "spot",
            fontName=font_name,
            fontSize=11,
            leading=15,
            textColor=_C_INK,
        ),
        "meta": ParagraphStyle(
            "meta",
            fontName=font_name,
            fontSize=8.5,
            leading=12,
            textColor=_C_MUTED,
        ),
        "notes": ParagraphStyle(
            "notes",
            fontName=font_name,
            fontSize=8.5,
            leading=12.5,
            textColor=_C_MUTED,
        ),
        "cost": ParagraphStyle(
            "cost",
            fontName=font_name,
            fontSize=10.5,
            leading=14,
            alignment=TA_RIGHT,
            textColor=_C_ACCENT,
        ),
        "cost_free": ParagraphStyle(
            "cost_free",
            fontName=font_name,
            fontSize=9,
            leading=14,
            alignment=TA_RIGHT,
            textColor=_C_MUTED,
        ),
        "budget_cat": ParagraphStyle(
            "budget_cat",
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=_C_INK,
        ),
        "budget_amt": ParagraphStyle(
            "budget_amt",
            fontName=font_name,
            fontSize=10,
            leading=14,
            alignment=TA_RIGHT,
            textColor=_C_INK,
        ),
    }


def _cover_card(trip: Trip, s: dict[str, ParagraphStyle], width: float) -> Table:
    date_line = f"{trip.start_date.isoformat()}  →  {trip.end_date.isoformat()}"
    inner = [
        [Paragraph(_pdf_text(trip.title), s["cover_title"])],
        [Spacer(1, 0.18 * cm)],
        [Paragraph(f"目的地 · {_pdf_text(trip.destination)}", s["cover_sub"])],
        [Paragraph(f"行程日期 · {date_line}", s["cover_sub"])],
    ]
    table = Table(inner, colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _C_PRIMARY),
                ("LEFTPADDING", (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                ("TOPPADDING", (0, 0), (0, 0), 20),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 20),
                ("TOPPADDING", (0, 1), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 0),
            ]
        )
    )
    return table


def _overview_cards(
    trip: Trip, s: dict[str, ParagraphStyle], width: float
) -> Table:
    days = list(trip.days)
    day_count = len(days)
    spot_count = sum(len(d.activities) for d in days)
    if trip.budget_total is not None:
        budget_text = f"¥{_fmt_amount(trip.budget_total)}"
    else:
        budget_text = "—"

    gap = 0.35 * cm
    card_w = (width - 2 * gap) / 3

    def card(num: str, label: str) -> Table:
        inner = Table(
            [[Paragraph(num, s["stat_num"])], [Paragraph(label, s["stat_label"])]],
            colWidths=[card_w],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), _C_PAPER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ("TOPPADDING", (0, 0), (0, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 1),
                    ("TOPPADDING", (0, 1), (0, 1), 0),
                    ("BOTTOMPADDING", (0, 1), (0, 1), 14),
                    ("LINEBEFORE", (0, 0), (0, -1), 2.2, _C_ACCENT),
                ]
            )
        )
        return inner

    row = [
        [
            card(f"{day_count} 天", "行程天数"),
            card(f"{spot_count} 处", "途经景点"),
            card(budget_text, "预算总额"),
        ]
    ]
    outer = Table(row, colWidths=[card_w, card_w, card_w], spaceBefore=0)
    outer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), gap),
                ("RIGHTPADDING", (1, 0), (1, 0), gap),
                ("RIGHTPADDING", (2, 0), (2, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return outer


def _budget_table(
    breakdown: str, s: dict[str, ParagraphStyle], width: float
) -> Table:
    items = _parse_budget_breakdown(breakdown)
    rows = [
        [
            Paragraph(_pdf_text(cat), s["budget_cat"]),
            Paragraph(_pdf_text(amt), s["budget_amt"]),
        ]
        for cat, amt in items
    ]
    table = Table(rows, colWidths=[width * 0.66, width * 0.34])
    table.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _C_STRIPE]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _C_LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, _C_LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _day_header(day: object, s: dict[str, ParagraphStyle], width: float) -> Table:
    left = [
        Paragraph(f"第 {day.day_index} 天", s["day_num"]),  # type: ignore[attr-defined]
        Paragraph(day.date.isoformat(), s["day_date"]),  # type: ignore[attr-defined]
    ]
    weather = _pdf_text(day.weather) if day.weather else ""  # type: ignore[attr-defined]
    right = Paragraph(weather, s["day_weather"])
    table = Table([[left, right]], colWidths=[width * 0.62, width * 0.38])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _C_PRIMARY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 16),
                ("RIGHTPADDING", (-1, 0), (-1, 0), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def _activities_table(
    day: object, s: dict[str, ParagraphStyle], width: float
) -> Table:
    time_w = 3.05 * cm
    cost_w = 2.2 * cm
    content_w = width - time_w - cost_w

    rows = []
    for act in sorted(day.activities, key=lambda a: a.order_index):  # type: ignore[attr-defined]
        time_text = _pdf_text(act.time_slot) if act.time_slot else ""
        time_cell = Paragraph(time_text, s["time"])

        content_flow: list[object] = [
            Paragraph(
                f'<font color="#C2703D">{act.order_index}</font>  '
                f"{_pdf_text(act.spot_name)}",
                s["spot"],
            )
        ]
        if act.transport:
            content_flow.append(
                Paragraph(f"交通 · {_pdf_text(act.transport)}", s["meta"])
            )
        if act.notes:
            content_flow.append(Paragraph(_pdf_text(act.notes), s["notes"]))

        if act.estimated_cost is None:
            cost_cell = Paragraph("—", s["cost_free"])
        elif float(act.estimated_cost) == 0:
            cost_cell = Paragraph("免费", s["cost_free"])
        else:
            cost_cell = Paragraph(f"¥{_fmt_amount(act.estimated_cost)}", s["cost"])

        rows.append([time_cell, content_flow, cost_cell])

    table = Table(rows, colWidths=[time_w, content_w, cost_w])
    table.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _C_STRIPE]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _C_LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def _draw_footer(canvas: object, doc: object) -> None:
    canvas.saveState()  # type: ignore[attr-defined]
    width, _ = A4
    font_name = _resolve_pdf_font()
    canvas.setStrokeColor(_C_LINE)  # type: ignore[attr-defined]
    canvas.setLineWidth(0.5)  # type: ignore[attr-defined]
    canvas.line(1.6 * cm, 1.35 * cm, width - 1.6 * cm, 1.35 * cm)  # type: ignore[attr-defined]
    canvas.setFont(font_name, 8)  # type: ignore[attr-defined]
    canvas.setFillColor(_C_MUTED)  # type: ignore[attr-defined]
    canvas.drawString(1.6 * cm, 1.0 * cm, "智能旅行助手 · 行程手册")  # type: ignore[attr-defined]
    canvas.drawRightString(  # type: ignore[attr-defined]
        width - 1.6 * cm, 1.0 * cm, f"第 {doc.page} 页"  # type: ignore[attr-defined]
    )
    canvas.restoreState()  # type: ignore[attr-defined]


def _build_pdf(trip: Trip) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.9 * cm,
        title=_pdf_text(trip.title),
    )
    width = doc.width
    font_name = _resolve_pdf_font()
    s = _make_styles(font_name)

    elements: list[object] = []
    elements.append(_cover_card(trip, s, width))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(_overview_cards(trip, s, width))
    elements.append(Spacer(1, 0.7 * cm))

    if trip.budget_breakdown:
        elements.append(Paragraph("预算明细", s["section"]))
        elements.append(Spacer(1, 0.25 * cm))
        elements.append(_budget_table(trip.budget_breakdown, s, width))
        elements.append(Spacer(1, 0.7 * cm))

    elements.append(Paragraph("每日行程", s["section"]))
    elements.append(Spacer(1, 0.3 * cm))

    for day in sorted(trip.days, key=lambda d: d.day_index):
        block = [
            _day_header(day, s, width),
            _activities_table(day, s, width),
            Spacer(1, 0.5 * cm),
        ]
        elements.append(KeepTogether(block))

    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
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
