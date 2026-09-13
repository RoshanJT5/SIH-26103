import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


HEADER_MAP = {
    "sr. no.": "source_row_number",
    "sector name": "sector",
    "line ministry": "ministry",
    "implementing agency": "implementing_agency",
    "project code": "project_code",
    "project name": "project_name",
    "original cost (in cr.)": "original_cost_cr",
    "revised cost (in cr.)": "revised_cost_cr",
    "expenditure (in cr.)": "expenditure_cr",
    "physical progress (in %)": "physical_progress_pct",
    "original date of commissioning": "original_commissioning_date",
    "revised date of commissioning": "revised_commissioning_date",
    "sanction date": "sanction_date",
}


class CsvUploadError(ValueError):
    """Raised when an uploaded file is not a supported project CSV."""


@dataclass(frozen=True)
class CsvStructure:
    canonical_columns: list[str]
    source_columns: list[str]
    preamble_rows: int
    record_count: int
    records: list[dict[str, str]]


@dataclass(frozen=True)
class ValidatedProject:
    source_row_number: int
    project_code: str
    project_name: str
    sector: str
    ministry: str
    implementing_agency: str
    original_cost_cr: Decimal
    revised_cost_cr: Decimal | None
    expenditure_cr: Decimal
    physical_progress_pct: Decimal
    original_commissioning_date: date
    revised_commissioning_date: date | None
    sanction_date: date | None
    raw_values: dict[str, str]
    quality_flags: list[dict[str, Any]]


@dataclass(frozen=True)
class ValidationIssue:
    source_row_number: int
    field: str | None
    raw_value: str | None
    issue_code: str
    severity: str
    message: str


@dataclass(frozen=True)
class ValidatedCsv:
    structure: CsvStructure
    projects: list[ValidatedProject]
    issues: list[ValidationIssue]
    rejected_count: int


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def inspect_project_csv(content: bytes) -> CsvStructure:
    if not content:
        raise CsvUploadError("The uploaded CSV is empty.")

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvUploadError("The CSV must use UTF-8 encoding.") from exc

    try:
        rows = list(csv.reader(io.StringIO(decoded, newline=""), strict=True))
    except csv.Error as exc:
        raise CsvUploadError(f"Malformed CSV: {exc}.") from exc

    header_index: int | None = None
    source_columns: list[str] = []
    for index, row in enumerate(rows):
        normalized = [normalize_header(value) for value in row]
        if "sr. no." in normalized and "project code" in normalized:
            header_index = index
            source_columns = row
            break

    if header_index is None:
        raise CsvUploadError("Project CSV header was not found after the optional report preamble.")

    normalized_columns = [normalize_header(value) for value in source_columns]
    duplicate_headers = sorted({name for name in normalized_columns if normalized_columns.count(name) > 1})
    missing_headers = sorted(set(HEADER_MAP) - set(normalized_columns))
    unexpected_headers = sorted(set(normalized_columns) - set(HEADER_MAP))

    problems: list[str] = []
    if duplicate_headers:
        problems.append(f"duplicate headers: {', '.join(duplicate_headers)}")
    if missing_headers:
        problems.append(f"missing headers: {', '.join(missing_headers)}")
    if unexpected_headers:
        problems.append(f"unexpected headers: {', '.join(unexpected_headers)}")
    if len(normalized_columns) != len(HEADER_MAP):
        problems.append(f"expected {len(HEADER_MAP)} columns, found {len(normalized_columns)}")
    if problems:
        raise CsvUploadError("Invalid project CSV schema; " + "; ".join(problems) + ".")

    records: list[dict[str, str]] = []
    for logical_row, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not row or all(not value.strip() for value in row):
            continue
        if len(row) != len(source_columns):
            raise CsvUploadError(
                f"Malformed CSV record {logical_row}: expected {len(source_columns)} fields, found {len(row)}."
            )
        records.append(dict(zip([HEADER_MAP[name] for name in normalized_columns], row, strict=True)))

    return CsvStructure(
        canonical_columns=[HEADER_MAP[name] for name in normalized_columns],
        source_columns=source_columns,
        preamble_rows=header_index,
        record_count=len(records),
        records=records,
    )


def _parse_decimal(value: str, field: str, row_number: int, *, positive: bool = False) -> Decimal:
    cleaned = re.sub(r"(?i)\bcr\.?\b", "", value).replace(",", "").replace("₹", "").strip()
    try:
        number = Decimal(cleaned)
    except InvalidOperation as exc:
        raise CsvUploadError(f"Record {row_number}: {field} is not a valid number.") from exc
    if not number.is_finite() or number < 0 or (positive and number == 0):
        condition = "greater than zero" if positive else "zero or greater"
        raise CsvUploadError(f"Record {row_number}: {field} must be {condition}.")
    return number.quantize(Decimal("0.01"))


def _parse_date(value: str, field: str, row_number: int, *, required: bool) -> date | None:
    stripped = value.strip()
    if not stripped:
        if required:
            raise CsvUploadError(f"Record {row_number}: {field} is required.")
        return None
    try:
        return datetime.strptime(stripped, "%d/%m/%Y").date()
    except ValueError as exc:
        raise CsvUploadError(f"Record {row_number}: {field} must use dd/MM/yyyy.") from exc


def validate_project_csv(content: bytes) -> ValidatedCsv:
    structure = inspect_project_csv(content)
    projects: list[ValidatedProject] = []
    issues: list[ValidationIssue] = []
    seen_codes: dict[str, dict[str, str]] = {}
    rejected_count = 0

    for position, raw in enumerate(structure.records, start=1):
        source_row = position
        try:
            source_row = int(raw["source_row_number"].strip())
        except (ValueError, TypeError):
            issues.append(ValidationIssue(position, "source_row_number", raw.get("source_row_number"), "invalid_source_row_number", "error", "Source row number must be an integer."))
            rejected_count += 1
            continue

        required_text = ["sector", "ministry", "implementing_agency", "project_code", "project_name"]
        missing = [field for field in required_text if not raw[field].strip()]
        if missing:
            for field in missing:
                issues.append(ValidationIssue(source_row, field, raw[field], "missing_required_value", "error", f"{field} is required."))
            rejected_count += 1
            continue

        code = raw["project_code"].strip()
        if code in seen_codes:
            issue_code = "duplicate_project_code" if raw == seen_codes[code] else "conflicting_duplicate_project_code"
            issues.append(ValidationIssue(source_row, "project_code", code, issue_code, "error", "Project code occurs more than once in this dataset."))
            rejected_count += 1
            continue
        seen_codes[code] = raw

        row_issues: list[ValidationIssue] = []
        try:
            original_cost = _parse_decimal(raw["original_cost_cr"], "original_cost_cr", source_row, positive=True)
            revised_cost = None if not raw["revised_cost_cr"].strip() else _parse_decimal(raw["revised_cost_cr"], "revised_cost_cr", source_row)
            expenditure = _parse_decimal(raw["expenditure_cr"], "expenditure_cr", source_row)
            progress = _parse_decimal(raw["physical_progress_pct"], "physical_progress_pct", source_row)
            if progress > 100:
                raise CsvUploadError(f"Record {source_row}: physical_progress_pct must be between zero and 100.")
            original_date = _parse_date(raw["original_commissioning_date"], "original_commissioning_date", source_row, required=True)
            revised_date = _parse_date(raw["revised_commissioning_date"], "revised_commissioning_date", source_row, required=False)
            sanction_date = _parse_date(raw["sanction_date"], "sanction_date", source_row, required=False)
        except CsvUploadError as exc:
            message = str(exc)
            field_match = re.search(r": ([a-z_]+) ", message)
            field = field_match.group(1) if field_match else None
            row_issues.append(ValidationIssue(source_row, field, raw.get(field) if field else None, "invalid_field_value", "error", message))
            issues.extend(row_issues)
            rejected_count += 1
            continue

        def flag(field: str, raw_value: str, code_name: str, severity: str, message: str) -> None:
            row_issues.append(ValidationIssue(source_row, field, raw_value, code_name, severity, message))

        if revised_cost is None:
            flag("revised_cost_cr", raw["revised_cost_cr"], "missing_revised_cost", "warning", "Revised cost is unavailable.")
        elif revised_cost == 0:
            flag("revised_cost_cr", raw["revised_cost_cr"], "zero_revised_cost", "warning", "Zero revised cost must be treated as unavailable for revised-budget calculations.")
        if expenditure == 0:
            flag("expenditure_cr", raw["expenditure_cr"], "zero_expenditure", "info", "Reported expenditure is zero.")
        if progress == 0:
            flag("physical_progress_pct", raw["physical_progress_pct"], "zero_physical_progress", "info", "Reported physical progress is zero.")
        if revised_date is None:
            flag("revised_commissioning_date", raw["revised_commissioning_date"], "missing_revised_commissioning_date", "warning", "Revised commissioning date is unavailable.")
        elif revised_date < original_date:
            flag("revised_commissioning_date", raw["revised_commissioning_date"], "revised_date_before_original", "warning", "Revised commissioning date precedes the original date.")
        if sanction_date is None:
            flag("sanction_date", raw["sanction_date"], "missing_sanction_date", "warning", "Sanction date is unavailable.")
        elif sanction_date > original_date:
            flag("sanction_date", raw["sanction_date"], "sanction_after_original_commissioning", "warning", "Sanction date follows the original commissioning date.")

        reported_budget = revised_cost if revised_cost is not None and revised_cost > 0 else original_cost
        if expenditure > reported_budget:
            flag("expenditure_cr", raw["expenditure_cr"], "expenditure_above_reported_budget", "warning", "Expenditure exceeds the usable reported budget.")

        issues.extend(row_issues)
        projects.append(
            ValidatedProject(
                source_row_number=source_row,
                project_code=code,
                project_name=raw["project_name"].strip(),
                sector=raw["sector"].strip(),
                ministry=raw["ministry"].strip(),
                implementing_agency=raw["implementing_agency"].strip(),
                original_cost_cr=original_cost,
                revised_cost_cr=revised_cost,
                expenditure_cr=expenditure,
                physical_progress_pct=progress,
                original_commissioning_date=original_date,
                revised_commissioning_date=revised_date,
                sanction_date=sanction_date,
                raw_values=raw,
                quality_flags=[{"field": item.field, "code": item.issue_code, "severity": item.severity, "message": item.message} for item in row_issues],
            )
        )

    return ValidatedCsv(structure=structure, projects=projects, issues=issues, rejected_count=rejected_count)
