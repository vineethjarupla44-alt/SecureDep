"""
Automated Alert Generation and Scheduling Service for AICTE FDR Portal.

Phase 6: Alert Persistence and Scheduling
Scans FDR records and generates multi-stage maturity alerts (30d, 15d, 7d, Matured, Overdue).
Enforces absolute idempotency via unique idempotency_key to prevent duplicate notifications
on repeated job executions or multi-worker deployments.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime, timedelta
from flask import current_app
from sqlalchemy.exc import IntegrityError
from config import Config
from models import db, FDRRecord, FDRAlert, User
from utils.time import local_business_date


def send_email_notification(to_email, subject, body):
    """
    Safely send email if SMTP credentials and configuration are explicitly supplied.
    Never crashes or sends fake emails if SMTP is disabled.
    """
    mail_enabled = current_app.config.get("MAIL_ENABLED", getattr(Config, "MAIL_ENABLED", False))
    if not mail_enabled:
        return False, "Email delivery is disabled in configuration."

    smtp_server = current_app.config.get("MAIL_SERVER", getattr(Config, "MAIL_SERVER", "localhost"))
    smtp_port = current_app.config.get("MAIL_PORT", getattr(Config, "MAIL_PORT", 25))
    smtp_user = current_app.config.get("MAIL_USERNAME", getattr(Config, "MAIL_USERNAME", ""))
    smtp_pass = current_app.config.get("MAIL_PASSWORD", getattr(Config, "MAIL_PASSWORD", ""))
    sender = current_app.config.get("MAIL_DEFAULT_SENDER", getattr(Config, "MAIL_DEFAULT_SENDER", "alerts@aicte-india.org"))

    if not smtp_server or not to_email:
        return False, "Incomplete SMTP configuration or missing recipient."

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        if current_app.config.get("MAIL_USE_TLS", getattr(Config, "MAIL_USE_TLS", False)):
            server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)

        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        return True, "Email sent successfully."
    except Exception as exc:
        return False, f"Failed to send email: {str(exc)}"


def scan_and_generate_maturity_alerts(reference_date=None):
    """
    Repeatable, idempotent alert generation job.

    Rules:
    - 30 Days Alert: 16 to 30 days remaining
    - 15 Days Alert: 8 to 15 days remaining
    - 7 Days Alert : 1 to 7 days remaining
    - Matured Alert: days <= 0
    - Overdue Alert: Pending renewal unresolved for > 14 days after maturity

    Idempotency:
        Each alert has a deterministic key:
        f"fdr_{fdr.id}_{alert_type}_{fdr.maturity_date}"
        If this key exists in `fdr_alerts`, it is skipped.
    """
    if reference_date is None:
        reference_date = local_business_date()

    # Query all active FDRs (exclude RENEWED, RELEASED, and PENDING_RENEWAL)
    active_fdrs = FDRRecord.query.filter(
        FDRRecord.status.notin_([
            FDRRecord.STATUS_RENEWED,
            FDRRecord.STATUS_RELEASED,
            FDRRecord.STATUS_PENDING_RENEWAL,
        ])
    ).all()

    created_alerts = []
    skipped_duplicates = 0

    for fdr in active_fdrs:
        days_left = (fdr.maturity_date - reference_date).days
        amount_fmt = f"INR {fdr.deposit_amount:,.2f}" if fdr.deposit_amount else "INR 0.00"

        # Determine which alert types apply for this FDR on reference_date
        alerts_to_check = []

        if 16 <= days_left <= 30:
            alerts_to_check.append({
                "type": FDRAlert.TYPE_EXPIRING_30,
                "title": f"FDR Expiring in 30 Days: {fdr.fdr_number}",
                "message": (
                    f"Fixed Deposit Receipt '{fdr.fdr_number}' from {fdr.issuing_bank} "
                    f"amounting to {amount_fmt} will mature on {fdr.maturity_date.isoformat()} "
                    f"({days_left} days remaining). Please prepare renewal or extension documentation."
                ),
            })
        elif 8 <= days_left <= 15:
            alerts_to_check.append({
                "type": FDRAlert.TYPE_EXPIRING_15,
                "title": f"FDR Expiring in 15 Days: {fdr.fdr_number}",
                "message": (
                    f"URGENT: Fixed Deposit Receipt '{fdr.fdr_number}' will mature in {days_left} days "
                    f"on {fdr.maturity_date.isoformat()}. Initiate bank renewal immediately."
                ),
            })
        elif 1 <= days_left <= 7:
            alerts_to_check.append({
                "type": FDRAlert.TYPE_EXPIRING_7,
                "title": f"CRITICAL: FDR Expiring in {days_left} Days: {fdr.fdr_number}",
                "message": (
                    f"CRITICAL ACTION REQUIRED: FDR '{fdr.fdr_number}' matures on {fdr.maturity_date.isoformat()} "
                    f"({days_left} days left). Submit replacement FDR to avoid institutional compliance notice."
                ),
            })
        elif days_left <= 0:
            # FDR is matured
            alerts_to_check.append({
                "type": FDRAlert.TYPE_MATURED,
                "title": f"FDR Matured: {fdr.fdr_number}",
                "message": (
                    f"Fixed Deposit Receipt '{fdr.fdr_number}' reached maturity on {fdr.maturity_date.isoformat()}. "
                    f"Compliance status requires submission of renewal deposit receipt."
                ),
            })

            # Check if renewal is overdue (matured > 14 days ago without resolved renewal)
            if days_left <= -14 and fdr.workflow_status != FDRRecord.WORKFLOW_RENEWAL_APPROVED:
                alerts_to_check.append({
                    "type": FDRAlert.TYPE_RENEWAL_OVERDUE,
                    "title": f"COMPLIANCE OVERDUE: Matured FDR {fdr.fdr_number}",
                    "message": (
                        f"Non-compliance warning: FDR '{fdr.fdr_number}' matured {abs(days_left)} days ago. "
                        f"No approved renewal has been recorded."
                    ),
                })

        # Process each eligible alert idempotently
        for alert_spec in alerts_to_check:
            a_type = alert_spec["type"]
            idempotency_key = f"fdr_{fdr.id}_{a_type}_{fdr.maturity_date.isoformat()}"

            # Check existing duplicate
            existing_id = db.session.query(FDRAlert.id).filter_by(idempotency_key=idempotency_key).scalar()
            if existing_id:
                skipped_duplicates += 1
                continue

            # Create Alert
            alert = FDRAlert(
                fdr_record_id=fdr.id,
                institution_id=fdr.institution_id,
                alert_type=a_type,
                due_date=fdr.maturity_date,
                recipient_role="institution_user",
                delivery_channel=FDRAlert.CHANNEL_IN_PORTAL,
                delivery_status=FDRAlert.STATUS_SENT,
                idempotency_key=idempotency_key,
                title=alert_spec["title"],
                message=alert_spec["message"],
                created_at=datetime.utcnow(),
            )
            try:
                # Flush in a savepoint so concurrent workers racing on the
                # unique key are treated as a duplicate instead of aborting
                # the whole scan transaction.
                with db.session.begin_nested():
                    db.session.add(alert)
                    db.session.flush()
                created_alerts.append(alert)
            except IntegrityError:
                skipped_duplicates += 1
                continue

            # Optional email notification
            if current_app.config.get("MAIL_ENABLED", getattr(Config, "MAIL_ENABLED", False)):
                inst_email = fdr.institution.contact_email if fdr.institution else None
                if inst_email:
                    sent, _ = send_email_notification(inst_email, alert.title, alert.message)
                    if sent:
                        alert.delivery_channel = FDRAlert.CHANNEL_EMAIL

    if created_alerts:
        db.session.commit()

    return {
        "status": "success",
        "reference_date": reference_date.isoformat(),
        "total_scanned_fdrs": len(active_fdrs),
        "alerts_created": len(created_alerts),
        "skipped_duplicates": skipped_duplicates,
        "created_alert_ids": [a.id for a in created_alerts],
    }


def create_release_workflow_alert(
    release_req,
    event_type,
    remarks=None,
    target_role="institution_user",
    recipient_user_id=None,
):
    """
    Create an idempotent in-portal notification and optional email for Phase 7
    release/refund workflow actions (submission, scrutiny, corrections, approval, rejection, closure).

    Args:
        release_req (FDRReleaseRequest): The subject release/refund request.
        event_type (str): FDRAlert event type constant.
        remarks (str, optional): Official remarks or justification.
        target_role (str): 'institution_user', 'aicte_official', or 'administrator'.
        recipient_user_id (int, optional): Specific recipient user.

    Returns:
        tuple (FDRAlert or None, bool is_new)
    """
    fdr = release_req.fdr_record
    fdr_number = fdr.fdr_number if fdr else f"ID-{release_req.fdr_record_id}"
    req_number = release_req.request_number
    amount_str = f"INR {release_req.requested_amount:,.2f}" if release_req.requested_amount else "INR 0.00"

    title_map = {
        FDRAlert.TYPE_RELEASE_SUBMITTED: f"New Release Request Submitted: {req_number}",
        FDRAlert.TYPE_RELEASE_PENDING_SCRUTINY: f"Release Request Pending Scrutiny: {req_number}",
        FDRAlert.TYPE_RELEASE_CORRECTION: f"Action Required: Corrections Requested for {req_number}",
        FDRAlert.TYPE_RELEASE_RECOMMENDED: f"Scrutiny Complete: {req_number} Recommended for Approval",
        FDRAlert.TYPE_RELEASE_APPROVED: f"Release Request Approved: {req_number}",
        FDRAlert.TYPE_RELEASE_REJECTED: f"Release Request Rejected: {req_number}",
        FDRAlert.TYPE_RELEASE_CLOSED: f"Security Deposit Released: {req_number} Closed",
        FDRAlert.TYPE_RELEASE_OVERDUE: f"ESCALATION: Release Request Overdue: {req_number}",
    }

    title = title_map.get(event_type, f"Release Notification: {req_number}")

    message_lines = [
        f"Release/Refund Request '{req_number}' for FDR '{fdr_number}' ({amount_str}).",
        f"Current Status: {release_req.status}.",
    ]
    if remarks:
        message_lines.append(f"Remarks: {remarks}")

    message = "\n".join(message_lines)

    # Unique deterministic idempotency key
    status_suffix = release_req.status
    ts_str = (
        release_req.updated_at.strftime("%Y%m%d%H%M%S")
        if release_req.updated_at
        else release_req.created_at.strftime("%Y%m%d%H%M%S")
    )
    idempotency_key = f"rel_{release_req.id}_{event_type}_{status_suffix}_{ts_str}"

    existing = db.session.query(FDRAlert).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        return existing, False

    alert = FDRAlert(
        fdr_record_id=release_req.fdr_record_id,
        release_request_id=release_req.id,
        institution_id=release_req.institution_id,
        alert_type=event_type,
        due_date=fdr.maturity_date if fdr else None,
        recipient_role=target_role,
        recipient_user_id=recipient_user_id,
        delivery_channel=FDRAlert.CHANNEL_IN_PORTAL,
        delivery_status=FDRAlert.STATUS_SENT,
        idempotency_key=idempotency_key,
        title=title,
        message=message,
        created_at=datetime.utcnow(),
    )
    db.session.add(alert)

    # Optional email delivery
    if current_app.config.get("MAIL_ENABLED", getattr(Config, "MAIL_ENABLED", False)):
        inst_email = release_req.institution.contact_email if release_req.institution else None
        if inst_email:
            sent, _ = send_email_notification(inst_email, alert.title, alert.message)
            if sent:
                alert.delivery_channel = FDRAlert.CHANNEL_EMAIL

    return alert, True


def scan_and_generate_release_overdue_alerts(reference_date=None, overdue_days=7):
    """
    Scan for unresolved release requests lingering in scrutiny or review stages
    for longer than `overdue_days`, generating escalation alerts to AICTE officials.

    Returns:
        dict: Scan statistics.
    """
    from models.release import FDRReleaseRequest

    if reference_date is None:
        reference_date = local_business_date()

    cutoff_datetime = datetime.combine(reference_date - timedelta(days=overdue_days), datetime.min.time())

    # Query active workflow requests pending action older than cutoff
    pending_statuses = [
        FDRReleaseRequest.STATUS_PENDING_SCRUTINY,
        FDRReleaseRequest.STATUS_UNDER_REVIEW,
        FDRReleaseRequest.STATUS_RECOMMENDED_FOR_APPROVAL,
    ]

    lingering_requests = FDRReleaseRequest.query.filter(
        FDRReleaseRequest.status.in_(pending_statuses),
        FDRReleaseRequest.updated_at <= cutoff_datetime,
    ).all()

    alerts_created = []
    skipped_duplicates = 0

    for req in lingering_requests:
        idempotency_key = f"rel_{req.id}_OVERDUE_{reference_date.isoformat()}"
        existing = db.session.query(FDRAlert.id).filter_by(idempotency_key=idempotency_key).scalar()
        if existing:
            skipped_duplicates += 1
            continue

        days_pending = (reference_date - req.updated_at.date()).days if req.updated_at else overdue_days
        title = f"ESCALATION: Release Request {req.request_number} Pending for {days_pending} Days"
        message = (
            f"Release request '{req.request_number}' (FDR '{req.fdr_record.fdr_number if req.fdr_record else req.fdr_record_id}') "
            f"has been in '{req.status}' state since {req.updated_at.strftime('%Y-%m-%d')}. "
            f"Immediate review action required."
        )

        alert = FDRAlert(
            fdr_record_id=req.fdr_record_id,
            release_request_id=req.id,
            institution_id=req.institution_id,
            alert_type=FDRAlert.TYPE_RELEASE_OVERDUE,
            due_date=req.fdr_record.maturity_date if req.fdr_record else None,
            recipient_role="aicte_official",
            delivery_channel=FDRAlert.CHANNEL_IN_PORTAL,
            delivery_status=FDRAlert.STATUS_SENT,
            idempotency_key=idempotency_key,
            title=title,
            message=message,
            created_at=datetime.utcnow(),
        )
        db.session.add(alert)
        alerts_created.append(alert)

    if alerts_created:
        db.session.commit()

    return {
        "status": "success",
        "reference_date": reference_date.isoformat(),
        "total_scanned_requests": len(lingering_requests),
        "alerts_created": len(alerts_created),
        "skipped_duplicates": skipped_duplicates,
    }
