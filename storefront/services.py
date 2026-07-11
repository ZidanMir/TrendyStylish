import base64
import json
import logging
import re
import secrets
from urllib import error, parse, request as urlrequest

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone


logger = logging.getLogger(__name__)

PHONE_SESSION_KEY = "phone_verification"
VERIFIED_PHONE_SESSION_KEY = "verified_signup_phone"
EMAIL_SESSION_KEY = "email_verification"


class VerificationError(Exception):
    pass


def normalize_bangladesh_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("880"):
        phone = f"+{digits}"
    elif digits.startswith("0"):
        phone = f"+880{digits[1:]}"
    elif len(digits) == 10 and digits.startswith("1"):
        phone = f"+880{digits}"
    else:
        raise VerificationError("Enter a valid Bangladesh mobile number.")

    if not re.fullmatch(r"\+8801[3-9]\d{8}", phone):
        raise VerificationError("Enter a valid Bangladesh mobile number.")
    return phone


def _now_timestamp():
    return int(timezone.now().timestamp())


def _new_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _check_resend_limit(state):
    if state and _now_timestamp() - state.get("sent_at", 0) < settings.VERIFICATION_RESEND_SECONDS:
        raise VerificationError("Please wait one minute before requesting another code.")


def _twilio_request(path, data):
    username = settings.TWILIO_API_KEY or settings.TWILIO_ACCOUNT_SID
    password = settings.TWILIO_API_SECRET or settings.TWILIO_AUTH_TOKEN
    if not username or not password or not settings.TWILIO_VERIFY_SERVICE_SID:
        raise VerificationError("Phone verification service is not configured.")

    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    endpoint = f"https://verify.twilio.com/v2/Services/{settings.TWILIO_VERIFY_SERVICE_SID}/{path}"
    api_request = urlrequest.Request(
        endpoint,
        data=parse.urlencode(data).encode(),
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(api_request, timeout=10) as response:
            return json.loads(response.read().decode())
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Twilio verification request failed: %s", type(exc).__name__)
        raise VerificationError("Verification service is temporarily unavailable.") from exc


def send_phone_code(session, phone_value, channel):
    if channel not in {"sms", "call"}:
        raise VerificationError("Choose text message or phone call.")

    phone = normalize_bangladesh_phone(phone_value)
    _check_resend_limit(session.get(PHONE_SESSION_KEY))
    state = {
        "phone": phone,
        "channel": channel,
        "sent_at": _now_timestamp(),
        "expires_at": _now_timestamp() + settings.VERIFICATION_CODE_TTL_SECONDS,
        "attempts": 0,
    }
    debug_code = ""

    if settings.PHONE_VERIFY_BACKEND == "twilio":
        result = _twilio_request("Verifications", {"To": phone, "Channel": channel})
        if result.get("status") != "pending":
            raise VerificationError("Verification code could not be sent.")
    else:
        debug_code = _new_code()
        state["code_hash"] = make_password(debug_code)

    session[PHONE_SESSION_KEY] = state
    session.modified = True
    return phone, debug_code


def verify_phone_code(session, phone_value, code):
    phone = normalize_bangladesh_phone(phone_value)
    state = session.get(PHONE_SESSION_KEY) or {}
    if state.get("phone") != phone:
        raise VerificationError("Request a new code for this phone number.")
    if state.get("expires_at", 0) < _now_timestamp():
        raise VerificationError("The verification code expired. Request a new one.")
    if state.get("attempts", 0) >= 5:
        raise VerificationError("Too many attempts. Request a new code.")

    state["attempts"] = state.get("attempts", 0) + 1
    session[PHONE_SESSION_KEY] = state
    approved = False
    if settings.PHONE_VERIFY_BACKEND == "twilio":
        result = _twilio_request("VerificationCheck", {"To": phone, "Code": (code or "").strip()})
        approved = result.get("status") == "approved"
    else:
        approved = check_password((code or "").strip(), state.get("code_hash", ""))

    if not approved:
        session.modified = True
        raise VerificationError("The verification code is incorrect.")

    session[VERIFIED_PHONE_SESSION_KEY] = {
        "phone": phone,
        "expires_at": _now_timestamp() + 30 * 60,
    }
    session.pop(PHONE_SESSION_KEY, None)
    session.modified = True
    return phone


def signup_phone_is_verified(session, phone):
    state = session.get(VERIFIED_PHONE_SESSION_KEY) or {}
    return state.get("phone") == phone and state.get("expires_at", 0) >= _now_timestamp()


def consume_signup_phone_verification(session):
    session.pop(VERIFIED_PHONE_SESSION_KEY, None)
    session.modified = True


def _send_email(subject, message, recipients):
    try:
        return send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False) == 1
    except Exception:
        logger.exception("Email delivery failed for subject %s", subject)
        return False


def send_email_verification_code(session, user):
    state = session.get(EMAIL_SESSION_KEY)
    _check_resend_limit(state)
    code = _new_code()
    state = {
        "email": user.email,
        "code_hash": make_password(code),
        "sent_at": _now_timestamp(),
        "expires_at": _now_timestamp() + settings.VERIFICATION_CODE_TTL_SECONDS,
        "attempts": 0,
    }
    if not _send_email(
        "Verify your Trendy Stylishness email",
        f"Your email verification code is {code}. It expires in 10 minutes.",
        [user.email],
    ):
        raise VerificationError("Verification email could not be sent.")

    session[EMAIL_SESSION_KEY] = state
    session.modified = True
    return code if settings.DEBUG else ""


def verify_email_code(session, user, code):
    state = session.get(EMAIL_SESSION_KEY) or {}
    if state.get("email") != user.email:
        raise VerificationError("Request a new code for this email address.")
    if state.get("expires_at", 0) < _now_timestamp():
        raise VerificationError("The verification code expired. Request a new one.")
    if state.get("attempts", 0) >= 5:
        raise VerificationError("Too many attempts. Request a new code.")

    state["attempts"] = state.get("attempts", 0) + 1
    session[EMAIL_SESSION_KEY] = state
    if not check_password((code or "").strip(), state.get("code_hash", "")):
        session.modified = True
        raise VerificationError("The verification code is incorrect.")

    profile = user.customer_profile
    profile.email_verified_at = timezone.now()
    profile.save(update_fields=["email_verified_at"])
    session.pop(EMAIL_SESSION_KEY, None)
    session.modified = True
    return profile


def order_email_address(order):
    return order.email or (order.user.email if order.user_id else "")


def send_order_confirmation(order):
    email = order_email_address(order)
    if not email:
        return False
    item_lines = "\n".join(f"- {item.quantity} x {item.product_name}: Tk {item.line_total}" for item in order.items.all())
    message = (
        f"Thanks, {order.customer_name}.\n\n"
        f"Order #{order.pk} is Pending and waiting for shop confirmation.\n\n"
        f"{item_lines}\n\n"
        f"Delivery: Tk {order.delivery_fee}\nTotal: Tk {order.total}\n\n"
        "We will email you whenever the order status changes."
    )
    return _send_email(f"Order #{order.pk} received - Trendy Stylishness", message, [email])


def send_order_status_update(order):
    email = order_email_address(order)
    if not email:
        return False
    status_messages = {
        order.STATUS_CONFIRMED: "Your order was accepted and is being prepared.",
        order.STATUS_RECEIVED: "Your order has been delivered.",
        order.STATUS_CANCELLED: "Your order was cancelled.",
    }
    message = (
        f"Hello {order.customer_name},\n\n"
        f"Order #{order.pk} is now {order.get_status_display()}.\n"
        f"{status_messages.get(order.status, '')}\n\n"
        f"Total: Tk {order.total}"
    )
    if order.status_note:
        message += f"\nNote: {order.status_note}"
    return _send_email(f"Order #{order.pk}: {order.get_status_display()}", message, [email])
