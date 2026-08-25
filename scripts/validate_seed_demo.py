"""Validación en memoria (SQLite :memory:) del comando seed_demo_data.

Ejecuta el seed dos veces y verifica idempotencia + cobertura; luego corre
una tercera vez con --reset-demo comprobando que un usuario manual no demo
se preserva. Imprime una matriz PASS/FAIL honesta y sale con código 1 si
algo falla.

Uso:
    python3 scripts/validate_seed_demo.py
"""
from __future__ import annotations

import os
import re
import sys
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "martial_arts_api.settings")
os.environ.setdefault("DEBUG", "true")  # entorno tipo dev: superusuario activo y SECRET_KEY de fallback

# Se parchea el módulo de settings ANTES de django.setup(): así el handler de
# conexiones y cualquier caché interna leen la base en memoria desde el inicio.
import importlib  # noqa: E402

_settings_mod = importlib.import_module("martial_arts_api.settings")
_settings_mod.DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
_settings_mod.CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.utils import timezone  # noqa: E402

# Esquema completo sobre la base en memoria.
call_command("migrate", verbosity=0, interactive=False)
print("Esquema migrado en SQLite :memory:", flush=True)

from blog.models import BlogPost, Category, Comment, Rating, Tag  # noqa: E402
from classes.models import (  # noqa: E402
    Class,
    ClassAttendance,
    ClassTemplate,
    ClassWaitlist,
    UserClassReservation,
)
from contact.models import Academy, ContactMessage  # noqa: E402
from gallery.models import Gallery  # noqa: E402
from notifications.models import Notification, UserNotificationPreference  # noqa: E402
from payments.models import Payment, PaymentStats, PaymentTransaction, QuotaConfig  # noqa: E402
from performance.models import (  # noqa: E402
    BeltRank,
    Discipline,
    EvaluationParameter,
    Event,
    EventCategory,
    EventParticipation,
    ExamResult,
    ExamResultParameterScore,
    ExamSession,
    PerformanceStatistics,
)
from performance.views import _get_belt_progress  # noqa: E402
from resources.models import Resource, ResourceTag  # noqa: E402
from users.models import UserProfile  # noqa: E402

User = get_user_model()
DEMO_DOMAIN = "demo.martial.local"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))


def snapshot_counts() -> dict[str, int]:
    models = {
        "User": User, "UserProfile": UserProfile, "Academy": Academy,
        "BeltRank": BeltRank, "Discipline": Discipline, "QuotaConfig": QuotaConfig,
        "ClassTemplate": ClassTemplate, "Class": Class,
        "UserClassReservation": UserClassReservation, "ClassAttendance": ClassAttendance,
        "ClassWaitlist": ClassWaitlist, "Payment": Payment,
        "PaymentTransaction": PaymentTransaction, "PaymentStats": PaymentStats,
        "Event": Event, "EventCategory": EventCategory, "EventParticipation": EventParticipation,
        "ExamSession": ExamSession, "ExamResult": ExamResult,
        "ExamResultParameterScore": ExamResultParameterScore,
        "PerformanceStatistics": PerformanceStatistics,
        "BlogPost": BlogPost, "Category": Category, "Tag": Tag,
        "Comment": Comment, "Rating": Rating,
        "Resource": Resource, "ResourceTag": ResourceTag,
        "Gallery": Gallery, "ContactMessage": ContactMessage,
        "Notification": Notification, "UserNotificationPreference": UserNotificationPreference,
    }
    return {label: model.objects.count() for label, model in models.items()}


def run_seed(*args: str) -> None:
    call_command("seed_demo_data", *args, verbosity=0)


# ---------------------------------------------------------------------------
# 1) Ejecutar seed DOS veces y comparar conteos (idempotencia)
# ---------------------------------------------------------------------------
print("== Corrida 1 del seed ==", flush=True)
run_seed()
counts_run1 = snapshot_counts()

print("== Corrida 2 del seed (idempotencia) ==", flush=True)
run_seed()
counts_run2 = snapshot_counts()

mismatched = {k: (counts_run1[k], counts_run2[k]) for k in counts_run1 if counts_run1[k] != counts_run2[k]}
check(
    "Idempotencia: mismas cantidades en corrida 1 y 2",
    not mismatched,
    f"desajustes: {mismatched}" if mismatched else f"{sum(counts_run2.values())} filas en {len(counts_run2)} modelos",
)

demo_users = User.objects.filter(email__iendswith=f"@{DEMO_DOMAIN}")
students = list(demo_users.filter(userprofile__role="student").order_by("id"))
now = timezone.now()
today = timezone.localdate()

# ---------------------------------------------------------------------------
# 2) Pagos
# ---------------------------------------------------------------------------
periods = set(Payment.objects.filter(user__email__iendswith=f"@{DEMO_DOMAIN}").values_list("period", flat=True))
check("Pagos: >=3 períodos distintos cubiertos", len(periods) >= 3, f"períodos={sorted(periods)}")

bad_methods = PaymentTransaction.objects.filter(payment__user__email__iendswith=f"@{DEMO_DOMAIN}").exclude(
    payment_method__in=["cash", "transfer"]
).count()
null_methods = PaymentTransaction.objects.filter(
    payment__user__email__iendswith=f"@{DEMO_DOMAIN}", payment_method__isnull=True
).count()
check("Pagos: payment_method inválido == 0 (solo cash|transfer)", bad_methods + null_methods == 0,
      f"inválidos={bad_methods}, nulos={null_methods}")

receipts = list(
    PaymentTransaction.objects.filter(payment__user__email__iendswith=f"@{DEMO_DOMAIN}")
    .values_list("receipt_number", flat=True)
)
receipt_re = re.compile(r"^RC-\d{4}-\d{6}$")
receipts_ok = all(receipt_re.match(r) for r in receipts if r)
paid_payments = Payment.objects.filter(user__email__iendswith=f"@{DEMO_DOMAIN}", is_fully_paid=True)
payments_with_receipt = all(p.transactions.exclude(receipt_number="").exists() for p in paid_payments)
check("Pagos: transacciones pagadas con recibo RC-YYYY-NNNNNN válido y único",
      receipts_ok and len(set(receipts)) == len(receipts) and payments_with_receipt,
      f"recibos={len(receipts)}, formato_ok={receipts_ok}, únicos={len(set(receipts)) == len(receipts)}")

fully_paid_share = (
    Payment.objects.filter(user__email__iendswith=f"@{DEMO_DOMAIN}", is_fully_paid=True).count()
    / max(Payment.objects.filter(user__email__iendswith=f"@{DEMO_DOMAIN}").count(), 1)
)
overdue_count = Payment.objects.filter(user__email__iendswith=f"@{DEMO_DOMAIN}", is_overdue=True).count()
partial_count = Payment.objects.filter(
    user__email__iendswith=f"@{DEMO_DOMAIN}",
    is_fully_paid=False, amount_paid__gt=0,
).count()
check("Pagos: mezcla realista (~70% completos, parciales y morosos presentes)",
      0.55 <= fully_paid_share <= 0.85 and overdue_count > 0 and partial_count > 0,
      f"completos={fully_paid_share:.0%}, parciales={partial_count}, vencidos={overdue_count}")
check("Pagos: snapshots mensuales de estadísticas >=4",
      PaymentStats.objects.count() >= 4, f"snapshots={PaymentStats.objects.count()}")

# ---------------------------------------------------------------------------
# 3) Asistencia
# ---------------------------------------------------------------------------
attendance_total = ClassAttendance.objects.count()
attendance_false = ClassAttendance.objects.filter(attended=False).count()
false_share = attendance_false / max(attendance_total, 1)
past_classes = Class.objects.filter(date__lt=now).count()
check("Asistencia: >100 registros", attendance_total > 100, f"total={attendance_total}, clases_pasadas={past_classes}")
check("Asistencia: ausentes >10% (mezcla orgánica)", false_share > 0.10, f"ausentes={false_share:.1%}")

# ---------------------------------------------------------------------------
# 4) Cohorte en riesgo (última asistencia hace 35-60 días)
# ---------------------------------------------------------------------------
risk_rows = []
for student in students:
    last_date = (
        ClassAttendance.objects.filter(
            user=student, attended=True,
            class_reserved__is_cancelled=False, class_reserved__date__lt=now,
        ).order_by("-class_reserved__date").values_list("class_reserved__date", flat=True).first()
    )
    if last_date is None:
        continue
    age_days = (now - last_date).days
    if age_days >= 30:
        risk_rows.append((student.email, age_days))
in_window = [row for row in risk_rows if 35 <= row[1] <= 60]
check("Riesgo: >=3 alumnos activos con última asistencia hace 35-60 días", len(in_window) >= 3,
      f"en_ventana={len(in_window)}, detalle={in_window[:6]}")

# ---------------------------------------------------------------------------
# 5) Cohorte apta para examen (criterio real del endpoint)
# ---------------------------------------------------------------------------
eligible = []
for student in students:
    progress = _get_belt_progress(student)
    if progress["eligible_for_exam"]:
        eligible.append((student.email, progress["classes_at_rank"], progress["required_classes"]))
check("Examen: >=3 alumnos elegibles según /exam-eligible (criterio real)", len(eligible) >= 3,
      f"elegibles={len(eligible)}, muestra={eligible[:5]}")

# ---------------------------------------------------------------------------
# 6) Sesiones de examen pasadas calificadas + futuras anunciadas
# ---------------------------------------------------------------------------
graded_sessions = ExamSession.objects.filter(exam_date__lte=today, exam_results__graded=True).distinct()
future_sessions = ExamSession.objects.filter(exam_date__gt=today)
has_fail = ExamResult.objects.filter(graded=True, passed=False).exists()
has_pass = ExamResult.objects.filter(graded=True, passed=True).exists()
scores_exist = ExamResultParameterScore.objects.exists() and graded_sessions.exists()
check("Examen: >=2 mesas pasadas calificadas con aprobados y fallas + puntajes",
      graded_sessions.count() >= 2 and has_pass and has_fail and scores_exist,
      f"calificadas={graded_sessions.count()}, futuras={future_sessions.count()}, scores={ExamResultParameterScore.objects.count()}")
check("Examen: sesión futura anunciada", future_sessions.count() >= 1, f"futuras={future_sessions.count()}")

# ---------------------------------------------------------------------------
# 7) Blog
# ---------------------------------------------------------------------------
posts = BlogPost.objects.all()
weak_posts = [
    post.title for post in posts
    if not (post.comments.exists() or post.ratings.exists())
]
check("Blog: >=5 entradas publicadas", posts.count() >= 5, f"entradas={posts.count()}")
check("Blog: cada entrada con >=1 comentario o calificación", not weak_posts,
      f"débiles={weak_posts}")

# ---------------------------------------------------------------------------
# 8) Recursos
# ---------------------------------------------------------------------------
resources = Resource.objects.all()
empty_documents = resources.filter(type="DOCUMENT", file="").count() + resources.filter(type="DOCUMENT", file__isnull=True).count()
no_url_media = resources.filter(type__in=["VIDEO", "LINK"], url="").count()
check("Recursos: >=8 ítems", resources.count() >= 8, f"recursos={resources.count()}")
check("Recursos: sin DOCUMENT vacío y VIDEO/LINK con URL", empty_documents == 0 and no_url_media == 0,
      f"documents_vacíos={empty_documents}, sin_url={no_url_media}")

# ---------------------------------------------------------------------------
# 9) Eventos
# ---------------------------------------------------------------------------
events_total = Event.objects.count()
past_events = Event.objects.filter(event_date__lt=today)
upcoming_events = Event.objects.filter(event_date__gte=today)
podium_results = set(
    EventParticipation.objects.filter(event__event_date__lt=today).values_list("result", flat=True)
)
check("Eventos: >=4 con pasados y próximos", events_total >= 4 and past_events.exists() and upcoming_events.exists(),
      f"total={events_total}, pasados={past_events.count()}, próximos={upcoming_events.count()}")
check("Eventos: podios 1º/2º/3º en eventos pasados", {"1st", "2nd", "3rd"}.issubset(podium_results),
      f"resultados={sorted(podium_results)}")
check("Eventos: participaciones cargadas", EventParticipation.objects.count() >= 10,
      f"participaciones={EventParticipation.objects.count()}")

# ---------------------------------------------------------------------------
# 10) Listas de espera sobre clases llenas próximas
# ---------------------------------------------------------------------------
full_upcoming = [c for c in Class.objects.filter(date__gt=now, is_cancelled=False) if c.reservation_count >= c.max_students]
waitlist_ok = True
detail_parts = []
full_with_waitlist = []
for class_obj in full_upcoming:
    entries = list(
        ClassWaitlist.objects.filter(class_reserved=class_obj, status__in=["waiting", "notified"])
        .order_by("position")
    )
    positions = [entry.position for entry in entries]
    statuses = {entry.status for entry in entries}
    if entries:
        # Si hay lista de espera, sus posiciones deben ser contiguas 1..N.
        contiguous = positions == list(range(1, len(positions) + 1))
        if contiguous and "waiting" in statuses:
            full_with_waitlist.append(class_obj.name)
        else:
            waitlist_ok = False
        detail_parts.append(f"{class_obj.name}: pos={positions}, estados={sorted(statuses)}")
    else:
        # Clase llena sin gente afuera (cupos exactamente cubiertos): no tener
        # cola es un resultado válido.
        detail_parts.append(f"{class_obj.name}: completa sin cola")
check("Listas de espera: >=2 clases próximas llenas con posiciones contiguas 1..N",
      len(full_with_waitlist) >= 2 and waitlist_ok,
      f"llenas_con_espera={len(full_with_waitlist)}, detalle={detail_parts}")
designated = {"Taekwondo Formativo Ypané", "Sparring Técnico Villeta"}
check("Listas de espera: las 2 franjas designadas están llenas y con espera",
      designated.issubset(set(full_with_waitlist)),
      f"designadas_presentes={designated & set(full_with_waitlist)}")

# ---------------------------------------------------------------------------
# 11) Notificaciones, contacto, galería
# ---------------------------------------------------------------------------
unread = Notification.objects.filter(is_read=False).count()
read = Notification.objects.filter(is_read=True).count()
students_without_notifications = sum(
    1 for student in students if not Notification.objects.filter(recipient=student).exists()
)
check("Notificaciones: mezcla leído/no leído y todos los alumnos con al menos una",
      unread > 0 and read > 0 and students_without_notifications == 0,
      f"leídas={read}, no_leídas={unread}, alumnos_sin={students_without_notifications}")
check("Contacto: >=5 mensajes variados", ContactMessage.objects.count() >= 5,
      f"mensajes={ContactMessage.objects.count()}, leídos={ContactMessage.objects.filter(is_read=True).count()}")
check("Galería: >=3 álbumes (metadatos)", Gallery.objects.count() >= 3, f"álbumes={Gallery.objects.count()}")

# ---------------------------------------------------------------------------
# 12) Escaneo ORM de campos visibles: cero marcadores ni placeholders
# ---------------------------------------------------------------------------
INVISIBLE_TAG = "\u200b"
SCAN_PLAN = [
    (Academy, ["name", "address", "schedule"]),
    (User, ["first_name", "last_name"]),
    (UserProfile, ["bio", "address", "city", "neighborhood"]),
    (BeltRank, ["name"]),
    (Discipline, ["name"]),
    (ExamSession, ["belt_level"]),
    (EvaluationParameter, ["name", "description"]) ,
    (ClassTemplate, ["name", "description", "location", "equipment_needed", "prerequisites"]),
    (Class, ["name", "description", "notes", "location", "equipment_needed", "cancellation_reason"]),
    (ClassAttendance, ["notes"]),
    (ClassWaitlist, ["notes"]),
    (Payment, ["description"]),
    (PaymentTransaction, ["description", "reference_number", "external_transaction_id"]),
    (Event, ["name", "description", "location", "organizer"]),
    (EventCategory, ["name", "description"]),
    (BlogPost, ["title", "content"]),
    (Category, ["name", "description"]),
    (Tag, ["name"]),
    (Comment, ["content"]),
    (Resource, ["title", "description", "url"]),
    (ResourceTag, ["name"]),
    (Gallery, ["title", "description"]),
    (ContactMessage, ["name", "message"]),
    (Notification, ["title", "message"]),
]
FORBIDDEN_RE = re.compile(r"\b(demo|seed|thesis|placeholder|sample|dummy|lorem|test)\b", re.IGNORECASE)
hits: list[str] = []
for model, fields in SCAN_PLAN:
    for values in model.objects.values("pk", *fields):
        for field in fields:
            raw = values.get(field) or ""
            # El identificador invisible (ancho cero) está permitido: se retira
            # antes de evaluar texto legible.
            text = str(raw).replace(INVISIBLE_TAG, "")
            match = FORBIDDEN_RE.search(text)
            if match:
                hits.append(f"{model.__name__}.{field}(pk={values['pk']}): {text[:60]!r}")
check("Visibilidad: sin '[demo-seed-py]' ni palabras placeholder/demo en campos visibles",
      not hits, f"coincidencias={hits[:8]}")

sessions_with_tag = ExamSession.objects.filter(belt_level__startswith=INVISIBLE_TAG).count()
check("Identificador invisible: sesiones de examen portan el ancla de ancho cero",
      sessions_with_tag == ExamSession.objects.count() and ExamSession.objects.count() > 0,
      f"con_ancla={sessions_with_tag}/{ExamSession.objects.count()}")

# ---------------------------------------------------------------------------
# 13) --reset-demo preserva usuario manual no demo
# ---------------------------------------------------------------------------
manual = User.objects.create_user(
    email="profesor.real@gmail.com",
    password="RealPass2026!",
    first_name="Profesor",
    last_name="Real",
)
# La señal de alta crea el perfil con rol por defecto 'student' y dispara la
# generación automática de cuotas: se limpia ese efecto secundario para que el
# usuario quede como un instructor real ajeno al seed.
Payment.objects.filter(user=manual).delete()
PaymentTransaction.objects.filter(payment__user=manual).delete()
Notification.objects.filter(recipient=manual).delete()
manual.userprofile.role = "instructor"
manual.userprofile.save()
manual_notification = Notification.objects.create(
    recipient=manual, title="Aviso manual", message="Dato ajeno al seed que debe sobrevivir.", type="info"
)

print("== Corrida 3 del seed con --reset-demo ==", flush=True)
run_seed("--reset-demo")
counts_run3 = snapshot_counts()
# El usuario manual (y su perfil/notificación) suma exactamente +1 en esos
# modelos; todo lo demás debe ser idéntico.
allowed_delta = {"User": 1, "UserProfile": 1, "Notification": 1}
reset_mismatch = {
    k: (counts_run2[k], counts_run3[k])
    for k in counts_run2
    if counts_run3[k] - counts_run2[k] != allowed_delta.get(k, 0)
}
check("Reset+reseed: cantidades estables (solo +1 por el usuario manual)", not reset_mismatch,
      f"desajustes={reset_mismatch}" if reset_mismatch else "conteos estables tras reset")
check("Reset: usuario manual no demo preservado (sin datos generados por el seed)",
      User.objects.filter(pk=manual.pk, email="profesor.real@gmail.com").exists()
      and Notification.objects.filter(pk=manual_notification.pk).exists()
      and not Payment.objects.filter(user=manual).exists())
check("Reset: datos demo recreados tras --reset-demo",
      Class.objects.count() > 50 and Payment.objects.count() > 80 and BlogPost.objects.count() >= 5,
      f"clases={Class.objects.count()}, pagos={Payment.objects.count()}, entradas={BlogPost.objects.count()}")

# ---------------------------------------------------------------------------
# Matriz final
# ---------------------------------------------------------------------------
print("\n================ MATRIZ DE VALIDACIÓN ================")
failed = 0
for name, ok, detail in RESULTS:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" | {detail}" if detail else ""))
    if not ok:
        failed += 1
print("======================================================")
print(f"Total: {len(RESULTS)} verificaciones, {len(RESULTS) - failed} PASS, {failed} FAIL")
sys.exit(1 if failed else 0)
