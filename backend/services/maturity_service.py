"""
Maturity Tracking Service for AICTE FDR Portal.

Phase 6: Maturity Tracking and Renewal Monitoring
Provides:
- Calculation of days remaining to maturity
- Multi-tier categorization (Active, Expiring Soon, Matured, Renewal Pending, Renewed, Released)
- Aggregated maturity statistics and summaries
- Filtered queries for expiring and matured instruments
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_
from models import db, FDRRecord, Institution
from utils.time import local_business_date


def calculate_fdr_maturity_metrics(fdr, reference_date=None):
    """
    Compute days remaining, category, and urgency level for an FDRRecord.
    """
    if reference_date is None:
        reference_date = local_business_date()

    days_remaining = (fdr.maturity_date - reference_date).days

    # Category determination
    if fdr.status == FDRRecord.STATUS_RENEWED:
        category = "RENEWED"
        urgency = "NONE"
    elif fdr.status == FDRRecord.STATUS_RELEASED:
        category = "RELEASED"
        urgency = "NONE"
    elif fdr.status == FDRRecord.STATUS_MATURED:
        category = "MATURED"
        urgency = "CRITICAL_MATURED"
    elif fdr.status == getattr(FDRRecord, "STATUS_PENDING_RENEWAL", "PENDING_RENEWAL") or fdr.workflow_status == FDRRecord.WORKFLOW_RENEWAL_SUBMITTED:
        category = "RENEWAL_PENDING"
        urgency = "WARNING_PENDING_REVIEW"
    elif days_remaining <= 0:
        category = "MATURED"
        urgency = "CRITICAL_MATURED"
    elif days_remaining <= 7:
        category = "EXPIRING_SOON"
        urgency = "CRITICAL_7D"
    elif days_remaining <= 15:
        category = "EXPIRING_SOON"
        urgency = "WARNING_15D"
    elif days_remaining <= 30:
        category = "EXPIRING_SOON"
        urgency = "ATTENTION_30D"
    else:
        category = "ACTIVE"
        urgency = "NORMAL"

    return {
        "days_remaining": days_remaining,
        "category": category,
        "urgency": urgency,
    }


def get_maturity_summary(institution_id=None, reference_date=None):
    """
    Calculate high-level maturity counts and financial summaries.
    Enforces institution scoping if institution_id is provided.
    """
    if reference_date is None:
        reference_date = local_business_date()

    query = FDRRecord.query
    if institution_id is not None:
        query = query.filter(FDRRecord.institution_id == institution_id)

    all_records = query.all()

    total_records = len(all_records)
    total_active = 0
    expiring_soon_count = 0
    expiring_30d = 0
    expiring_15d = 0
    expiring_7d = 0
    total_matured = 0
    total_renewed = 0
    total_released = 0
    renewal_pending = 0
    total_deposit_amount = Decimal("0.00")
    expiring_deposit_amount = Decimal("0.00")

    for fdr in all_records:
        amt = fdr.deposit_amount or Decimal("0.00")
        total_deposit_amount += amt
        metrics = calculate_fdr_maturity_metrics(fdr, reference_date)
        cat = metrics["category"]
        days = metrics["days_remaining"]

        if cat == "RENEWED":
            total_renewed += 1
        elif cat == "RELEASED":
            total_released += 1
        elif cat == "RENEWAL_PENDING":
            renewal_pending += 1
        elif cat == "MATURED":
            total_matured += 1
        elif cat == "EXPIRING_SOON":
            expiring_soon_count += 1
            total_active += 1
            expiring_deposit_amount += amt
            if days <= 7:
                expiring_7d += 1
            if days <= 15:
                expiring_15d += 1
            if days <= 30:
                expiring_30d += 1
        elif cat == "ACTIVE":
            total_active += 1

    return {
        "institution_id": institution_id,
        "reference_date": reference_date.isoformat(),
        "total_records": total_records,
        "total_active": total_active,
        "total_matured": total_matured,
        "total_renewed": total_renewed,
        "total_released": total_released,
        "renewal_pending": renewal_pending,
        "categories": {
            "active_count": total_active,
            "expiring_soon_count": expiring_soon_count,
            "matured_count": total_matured,
            "renewal_pending_count": renewal_pending,
            "renewed_count": total_renewed,
            "released_count": total_released,
        },
        "expiring_soon_breakdown": {
            "within_30_days": expiring_30d,
            "within_15_days": expiring_15d,
            "within_7_days": expiring_7d,
        },
        "financial_summary": {
            "total_deposit_amount": float(total_deposit_amount),
            "total_deposit_formatted": f"INR {total_deposit_amount:,.2f}",
            "expiring_soon_deposit_amount": float(expiring_deposit_amount),
            "expiring_soon_deposit_formatted": f"INR {expiring_deposit_amount:,.2f}",
        },
    }


def get_expiring_fdrs(
    institution_id=None,
    days_ahead=30,
    status=None,
    date_from=None,
    date_to=None,
    page=1,
    per_page=10,
    reference_date=None,
    category=None,
):
    """
    Retrieve paginated expiring and matured FDRs with maturity metrics.
    """
    if reference_date is None:
        reference_date = local_business_date()

    query = FDRRecord.query

    # Tenant isolation
    if institution_id is not None:
        query = query.filter(FDRRecord.institution_id == institution_id)

    # Exclude already renewed or released instruments from expiring alerts
    query = query.filter(
        FDRRecord.status.notin_([FDRRecord.STATUS_RENEWED, FDRRecord.STATUS_RELEASED])
    )

    # Date filters
    if date_from:
        query = query.filter(FDRRecord.maturity_date >= date_from)
    if date_to:
        query = query.filter(FDRRecord.maturity_date <= date_to)
    elif days_ahead is not None:
        cutoff = reference_date + timedelta(days=int(days_ahead))
        query = query.filter(FDRRecord.maturity_date <= cutoff)

    # Status filter
    if status:
        query = query.filter(FDRRecord.status == status.strip().upper())

    normalized_category = category.strip().upper() if category else None

    # Order by nearest maturity date
    query = query.order_by(FDRRecord.maturity_date.asc(), FDRRecord.id.asc())

    # Category is derived from a calendar date and lifecycle/workflow state,
    # so apply it before pagination to keep total/pages/data consistent.
    if normalized_category:
        candidates = query.all()
        matching = [
            item for item in candidates
            if calculate_fdr_maturity_metrics(item, reference_date)["category"] == normalized_category
        ]
        total = len(matching)
        start = max(page - 1, 0) * per_page
        selected = matching[start:start + per_page]
        total_pages = (total + per_page - 1) // per_page if total else 0
        has_next = start + per_page < total
        has_prev = page > 1 and total > 0
    else:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        total = pagination.total
        selected = pagination.items
        total_pages = pagination.pages
        has_next = pagination.has_next
        has_prev = pagination.has_prev

    enriched_items = []
    for item in selected:
        item_dict = item.to_dict()
        metrics = calculate_fdr_maturity_metrics(item, reference_date)
        item_dict.update(metrics)
        enriched_items.append(item_dict)

    return {
        "status": "success",
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
        "data": enriched_items,
    }
