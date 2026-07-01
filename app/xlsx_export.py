from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

LOCATION_META = {
    "weinzelt": {
        "label": "Weinzelt",
        "header_style": 2,
    },
    "bierwagen": {
        "label": "Bierwagen",
        "header_style": 3,
    },
    "other": {
        "label": "Sonstiges",
        "header_style": 4,
    },
}

GERMAN_WEEKDAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]

GERMAN_WEEKDAY_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

GERMAN_MONTHS = [
    "Januar",
    "Februar",
    "Maerz",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def build_shift_plan_xlsx(
    shifts: List[Any],
    assignments: Optional[Iterable[Any]] = None,
    exported_at: Optional[datetime] = None,
) -> bytes:
    day_plans = _build_day_plans(shifts, assignments)
    generated_at = exported_at or datetime.now()

    workbook_buffer = BytesIO()
    with ZipFile(workbook_buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _build_content_types_xml(len(day_plans)))
        archive.writestr("_rels/.rels", _build_root_rels_xml())
        archive.writestr("docProps/app.xml", _build_app_props_xml(day_plans))
        archive.writestr("docProps/core.xml", _build_core_props_xml(generated_at))
        archive.writestr("xl/workbook.xml", _build_workbook_xml(day_plans))
        archive.writestr("xl/_rels/workbook.xml.rels", _build_workbook_rels_xml(len(day_plans)))
        archive.writestr("xl/styles.xml", _build_styles_xml())

        for index, day_plan in enumerate(day_plans, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _build_sheet_xml(day_plan, generated_at),
            )

    return workbook_buffer.getvalue()


def _build_day_plans(shifts: List[Any], assignments: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    assignment_map = _build_assignment_map(assignments)
    day_map: Dict[str, Dict[str, Any]] = {}

    for shift in shifts:
        if not getattr(shift, "is_active", True):
            continue

        planner_day = _get_planner_day_start(shift)
        day_key = planner_day.date().isoformat()
        day_plan = day_map.setdefault(
            day_key,
            {
                "day_date": planner_day.date(),
                "slots": {},
                "location_keys": set(),
            },
        )

        slot_key = (
            _get_sort_minutes(shift.start_time),
            shift.start_time.hour,
            shift.start_time.minute,
            shift.end_time.hour,
            shift.end_time.minute,
        )
        slot = day_plan["slots"].setdefault(
            slot_key,
            {
                "sort_minutes": slot_key[0],
                "time_label": _format_slot_time_label(shift.start_time, shift.end_time),
                "locations": {},
            },
        )

        location_key = _get_shift_location_key(shift.title)
        day_plan["location_keys"].add(location_key)
        slot["locations"][location_key] = {
            "capacity": shift.capacity or "",
            "entries": _get_shift_entries(shift, assignment_map),
        }

    ordered_day_plans: List[Dict[str, Any]] = []
    for day_key in sorted(day_map.keys()):
        day_plan = day_map[day_key]
        location_columns = _build_location_columns(day_plan["location_keys"])
        slots = [
            day_plan["slots"][slot_key]
            for slot_key in sorted(day_plan["slots"].keys())
        ]
        ordered_day_plans.append(
            {
                "day_date": day_plan["day_date"],
                "location_columns": location_columns,
                "slots": slots,
            }
        )

    if not ordered_day_plans:
        ordered_day_plans.append(
            {
                "day_date": date.today(),
                "location_columns": _build_location_columns({"weinzelt", "bierwagen"}),
                "slots": [],
            }
        )

    return ordered_day_plans


def _build_assignment_map(assignments: Optional[Iterable[Any]]) -> Optional[Dict[int, List[Dict[str, Any]]]]:
    if assignments is None:
        return None

    assignment_map: Dict[int, List[Dict[str, Any]]] = {}
    for assignment in assignments:
        if hasattr(assignment, "model_dump"):
            normalized = assignment.model_dump()
        elif isinstance(assignment, dict):
            normalized = assignment
        else:
            normalized = {
                "shift_id": getattr(assignment, "shift_id"),
                "username": getattr(assignment, "username"),
                "assigned_via": getattr(assignment, "assigned_via"),
                "group_name": getattr(assignment, "group_name", None),
            }

        assignment_map.setdefault(normalized["shift_id"], []).append(normalized)

    return assignment_map


def _get_shift_entries(shift: Any, assignment_map: Optional[Dict[int, List[Dict[str, Any]]]]) -> List[str]:
    if assignment_map is not None:
        shift_assignments = assignment_map.get(shift.id, [])
        grouped_entries: "OrderedDict[str, List[str]]" = OrderedDict()
        individual_entries: List[str] = []

        for assignment in shift_assignments:
            username = assignment.get("username", "")
            if assignment.get("assigned_via") == "group" and assignment.get("group_name"):
                grouped_entries.setdefault(assignment["group_name"], []).append(username)
            else:
                individual_entries.append(username)

        entries: List[str] = []
        for usernames in grouped_entries.values():
            entries.extend(usernames)
        entries.extend(individual_entries)
        return entries

    grouped_user_ids = set()
    entries = []

    for group in getattr(shift, "groups", []) or []:
        for user in getattr(group, "users", []) or []:
            if not getattr(user, "is_active", True) or getattr(user, "is_coordinator", False):
                continue
            grouped_user_ids.add(user.id)
            entries.append(user.username)

    for user in getattr(shift, "users", []) or []:
        if not getattr(user, "is_active", True) or getattr(user, "is_coordinator", False):
            continue
        if user.id in grouped_user_ids:
            continue
        entries.append(user.username)

    return entries


def _build_location_columns(location_keys: Iterable[str]) -> List[Dict[str, Any]]:
    present_keys = set(location_keys)
    ordered_keys = []

    for key in ("weinzelt", "bierwagen"):
        if key in present_keys:
            ordered_keys.append(key)

    extra_keys = sorted(key for key in present_keys if key not in {"weinzelt", "bierwagen"})
    ordered_keys.extend(extra_keys)

    columns = []
    for key in ordered_keys:
        meta = LOCATION_META.get(key, LOCATION_META["other"])
        columns.append(
            {
                "key": key,
                "label": meta["label"] if key in LOCATION_META else key.title(),
                "header_style": meta["header_style"] if key in LOCATION_META else LOCATION_META["other"]["header_style"],
            }
        )

    return columns


def _build_sheet_xml(day_plan: Dict[str, Any], generated_at: datetime) -> str:
    location_columns = day_plan["location_columns"]
    total_columns = len(location_columns) * 5 + max(0, len(location_columns) - 1)
    last_column_name = _column_name(total_columns)

    rows = []
    merges = []

    title_text = f"{_format_day_label(day_plan['day_date'])} | Stand: {_format_timestamp(generated_at)}"
    rows.append(_row_xml(1, [(1, title_text, 1)], height=24))
    merges.append(f"A1:{last_column_name}1")

    header_cells = []
    for block_index, location in enumerate(location_columns):
        start_column = 1 + block_index * 6
        end_column = start_column + 4
        for column in range(start_column, end_column + 1):
            header_cells.append(
                (column, location["label"] if column == start_column else "", location["header_style"])
            )
        merges.append(f"{_cell_ref(start_column, 3)}:{_cell_ref(end_column, 3)}")
    rows.append(_row_xml(3, header_cells, height=20))

    subheader_cells = []
    for block_index in range(len(location_columns)):
        start_column = 1 + block_index * 6
        subheader_cells.extend(
            [
                (start_column, "Zeit", 5),
                (start_column + 1, "Namen", 5),
                (start_column + 2, "", 5),
                (start_column + 3, "", 5),
                (start_column + 4, "Pers.", 5),
            ]
        )
        merges.append(
            f"{_cell_ref(start_column + 1, 4)}:{_cell_ref(start_column + 3, 4)}"
        )
    rows.append(_row_xml(4, subheader_cells, height=18))

    current_row = 5
    for slot in day_plan["slots"]:
        slot_cells = []
        for block_index, location in enumerate(location_columns):
            start_column = 1 + block_index * 6
            shift = slot["locations"].get(location["key"])
            print_columns = _build_print_columns(shift["entries"] if shift else [])
            capacity = shift["capacity"] if shift else ""

            slot_cells.extend(
                [
                    (start_column, slot["time_label"], 6),
                    (start_column + 1, print_columns[0], 7),
                    (start_column + 2, print_columns[1], 7),
                    (start_column + 3, print_columns[2], 7),
                    (start_column + 4, capacity, 8, isinstance(capacity, int)),
                ]
            )
        rows.append(_row_xml(current_row, slot_cells, height=36))
        current_row += 1

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:{last_column_name}{max(current_row - 1, 4)}"/>
  <sheetViews>
    <sheetView workbookViewId="0"/>
  </sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  {_build_cols_xml(location_columns)}
  <sheetData>
    {''.join(rows)}
  </sheetData>
  <mergeCells count="{len(merges)}">
    {''.join(f'<mergeCell ref="{merge_ref}"/>' for merge_ref in merges)}
  </mergeCells>
</worksheet>"""


def _build_cols_xml(location_columns: List[Dict[str, Any]]) -> str:
    col_entries = []
    current_index = 1

    for block_index, _location in enumerate(location_columns):
        col_entries.extend(
            [
                (current_index, 12),
                (current_index + 1, 18),
                (current_index + 2, 18),
                (current_index + 3, 18),
                (current_index + 4, 8),
            ]
        )
        current_index += 5

        if block_index < len(location_columns) - 1:
            col_entries.append((current_index, 3))
            current_index += 1

    return "<cols>" + "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in col_entries
    ) + "</cols>"


def _row_xml(row_index: int, cells: List[tuple], height: Optional[int] = None) -> str:
    row_height = f' ht="{height}" customHeight="1"' if height else ""
    cell_xml = []

    for cell in cells:
        column_index, value, style_id, *rest = cell
        is_number = bool(rest[0]) if rest else False
        cell_xml.append(_cell_xml(column_index, row_index, value, style_id, is_number))

    return f'<row r="{row_index}"{row_height}>{"".join(cell_xml)}</row>'


def _cell_xml(column_index: int, row_index: int, value: Any, style_id: int, is_number: bool = False) -> str:
    ref = _cell_ref(column_index, row_index)

    if is_number and value not in ("", None):
        return f'<c r="{ref}" s="{style_id}"><v>{value}</v></c>'

    text = escape(str(value or ""))
    preserve = ' xml:space="preserve"' if "\n" in text or text.startswith(" ") or text.endswith(" ") else ""
    return f'<c r="{ref}" s="{style_id}" t="inlineStr"><is><t{preserve}>{text}</t></is></c>'


def _cell_ref(column_index: int, row_index: int) -> str:
    return f"{_column_name(column_index)}{row_index}"


def _column_name(column_index: int) -> str:
    name = []
    index = column_index
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        name.append(chr(65 + remainder))
    return "".join(reversed(name))


def _build_print_columns(entries: List[str]) -> List[str]:
    columns = [[], [], []]

    for index, entry in enumerate(entries[:6]):
        columns[index % 3].append(entry)

    return ["\n".join(column_entries) for column_entries in columns]


def _get_planner_day_start(shift: Any) -> datetime:
    shift_start = shift.start_time
    if shift_start.hour < 6:
        return shift_start - timedelta(days=1)
    return shift_start


def _get_shift_location_key(title: str) -> str:
    normalized_title = title.lower()
    if "wein" in normalized_title:
        return "weinzelt"
    if "bier" in normalized_title:
        return "bierwagen"
    return "other"


def _get_sort_minutes(date_time: datetime) -> int:
    hours = date_time.hour
    minutes = date_time.minute
    return (hours + 24 if hours < 6 else hours) * 60 + minutes


def _format_slot_time_label(start_time: datetime, end_time: datetime) -> str:
    return f"{start_time:%H:%M} -\n{end_time:%H:%M}"


def _format_day_label(day_value: date) -> str:
    weekday = GERMAN_WEEKDAYS[day_value.weekday()]
    month = GERMAN_MONTHS[day_value.month - 1]
    return f"{weekday}, {day_value.day:02d}. {month} {day_value.year}"


def _format_sheet_name(day_value: date) -> str:
    weekday = GERMAN_WEEKDAY_SHORT[day_value.weekday()]
    return f"{weekday} {day_value.day:02d}.{day_value.month:02d}."


def _format_timestamp(date_value: datetime) -> str:
    return date_value.strftime("%d.%m.%Y, %H:%M")


def _build_content_types_xml(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]

    overrides.extend(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {''.join(overrides)}
</Types>"""


def _build_root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def _build_app_props_xml(day_plans: List[Dict[str, Any]]) -> str:
    sheet_titles = "".join(
        f"<vt:lpstr>{escape(_format_sheet_name(day_plan['day_date']))}</vt:lpstr>"
        for day_plan in day_plans
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Open Flair Schichtplaner</Application>
  <TitlesOfParts>
    <vt:vector size="{len(day_plans)}" baseType="lpstr">{sheet_titles}</vt:vector>
  </TitlesOfParts>
</Properties>"""


def _build_core_props_xml(generated_at: datetime) -> str:
    timestamp = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Open Flair Schichtplan</dc:title>
  <dc:creator>Open Flair Schichtplaner</dc:creator>
  <cp:lastModifiedBy>Open Flair Schichtplaner</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>"""


def _build_workbook_xml(day_plans: List[Dict[str, Any]]) -> str:
    sheets_xml = "".join(
        f'<sheet name="{escape(_format_sheet_name(day_plan["day_date"]))}" sheetId="{index}" r:id="rId{index}"/>'
        for index, day_plan in enumerate(day_plans, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{sheets_xml}</sheets>
</workbook>"""


def _build_workbook_rels_xml(sheet_count: int) -> str:
    sheet_rels = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    styles_rel_id = sheet_count + 1
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {sheet_rels}
  <Relationship Id="rId{styles_rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _build_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3">
    <font>
      <sz val="11"/>
      <name val="Calibri"/>
      <family val="2"/>
    </font>
    <font>
      <b/>
      <sz val="11"/>
      <name val="Calibri"/>
      <family val="2"/>
    </font>
    <font>
      <b/>
      <sz val="14"/>
      <name val="Calibri"/>
      <family val="2"/>
    </font>
  </fonts>
  <fills count="7">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFDE8F1"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE5F7FD"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF3F4F6"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF7F7F7"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFAFAFA"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="3">
    <border>
      <left/><right/><top/><bottom/><diagonal/>
    </border>
    <border>
      <left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/><diagonal/>
    </border>
    <border>
      <left style="thin"/><right style="thin"/><top style="thin"/><bottom style="medium"/><diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="9">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">
      <alignment horizontal="left" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="6" borderId="2" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="2" xfId="0" applyBorder="1" applyAlignment="1">
      <alignment horizontal="left" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="2" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>"""
