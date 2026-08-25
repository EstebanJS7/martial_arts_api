from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.signals import post_save
from django.test.utils import override_settings
from django.utils import timezone

from blog.models import BlogPost, Category, Comment, Rating, Tag
from classes.models import Class, ClassAttendance, ClassTemplate, ClassWaitlist, UserClassReservation
from classes.signals import (
    attendance_marked,
    class_reservation_count_changed,
    reservation_created_or_updated,
)
from contact.models import Academy, ContactMessage
from gallery.models import Gallery
from notifications.models import Notification, UserNotificationPreference
from payments.models import Payment, PaymentStats, PaymentTransaction, QuotaConfig
from payments.signals import payment_created_or_updated, payment_transaction_created
from performance.models import (
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
from resources.models import Resource, ResourceCategory, ResourceLevel, ResourceTag, ResourceType
User = get_user_model()

# ---------------------------------------------------------------------------
# IDENTIFICACIÓN DE DATOS DEMO (sin marcadores visibles)
#
# Antes existía un marcador textual "[demo-seed-py]" incrustado en títulos,
# descripciones y notas. Eso permitía podar con icontains, pero el público
# podía detectar que los datos eran scripted. Ahora la identificación es:
#
#   1. REGISTROS DETERMINISTAS EN MEMORIA (este módulo): tuplas con los
#      nombres/títulos EXACTOS que crea el comando. La poda usa filtros de
#      igualdad (name__in, title__in, email__in...) sobre esos registros y la
#      idempotencia usa update_or_create sobre las mismas claves.
#   2. ANCLAS ESTRUCTURALES cuando no hay campo de texto único:
#      - Payment.period ('YYYY-MM'): clave natural por usuario/período.
#      - PaymentStats.date: primer día de cada mes cubierto.
#      - ExamSession: no tiene slug ni texto único estable -> se antepone un
#        ESPACIO DE ANCHO CERO (INVISIBLE_TAG) a belt_level. Es invisible en
#        cualquier renderizado y permite filtrar belt_level__startswith.
#      - Notification / reservas / asistencias / transacciones: cuelgan de
#        usuarios demo (email @demo.martial.local) o de filas demo padre, así
#        que la poda por usuario/clase los cubre.
#
# El dominio @demo.martial.local se mantiene intacto: es el mecanismo de
# aislado que garantiza que nunca se toquen datos reales.
# ---------------------------------------------------------------------------
INVISIBLE_TAG = "\u200b"  # espacio de ancho cero: identificador invisible
DEMO_EMAIL_DOMAIN = "demo.martial.local"
DEFAULT_DEMO_PASSWORD = "DemoSeed2026!"

# Base de numeración de recibos demo. Arranca en 900001 para dejar margen
# frente a recibos reales (que arrancan en 1); formato RC-YYYY-NNNNNN.
DEMO_RECEIPT_BASE = 900000

ACADEMY_DATA = [
    {
        "name": "Academia Teko Katu Ypane",
        "address": "Av. Bernardino Caballero c/ Sgto. Maidana, Ypane, Central",
        "phone": "+595981450120",
        "email": f"ypane@{DEMO_EMAIL_DOMAIN}",
        "schedule": "Lun-Vie 17:00-21:00, Sab 08:00-11:30",
        "latitude": Decimal("-25.452500"),
        "longitude": Decimal("-57.533400"),
    },
    {
        "name": "Academia Teko Katu Villeta",
        "address": "Av. Defensores del Chaco c/ Mcal. Estigarribia, Villeta, Central",
        "phone": "+595981450121",
        "email": f"villeta@{DEMO_EMAIL_DOMAIN}",
        "schedule": "Lun-Vie 17:30-21:30, Sab 08:00-12:00",
        "latitude": Decimal("-25.508700"),
        "longitude": Decimal("-57.566000"),
    },
]

BELT_RANKS = [
    # (nombre, orden, categoría, clases requeridas por rango)
    # Valores explícitos y realistas para academia pequeña: hacen que el flujo
    # de "apto para examen" sea alcanzable dentro de la ventana de semanas.
    ("Blanco", 1, "Kyu A", 10),
    ("Amarillo", 2, "Kyu A", 12),
    ("Naranja", 3, "Kyu A", 12),
    ("Verde", 4, "Kyu B", 14),
    ("Azul", 5, "Kyu B", 14),
    ("Marron", 6, "Kyu B", 16),
    ("Rojo", 7, "Kyu B", 16),
    ("Negro 1 Dan", 8, "Dan", 20),
]

DISCIPLINES = [
    "Taekwondo ITF",
    "Taekwondo WT",
    "Defensa Personal",
]

EVALUATION_PARAMETERS = [
    ("Técnica", "Forma", "Calidad de ejecución y postura"),
    ("Potencia", "Física", "Control del impacto y mecánica corporal"),
    ("Disciplina", "Actitud", "Respeto, concentración y protocolo"),
    ("Sparring", "Combate", "Distancia, timing y control"),
]

MONTH_NAMES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# --- Catálogos de blog -------------------------------------------------------
BLOG_CATEGORIES = [
    ("Entrenamiento", "Progreso semanal y destacados de la práctica", "#2563EB"),
    ("Comunidad", "Actividades de la academia en Ypané y Villeta", "#059669"),
    ("Eventos", "Exámenes, exhibiciones y torneos regionales", "#D97706"),
]

BLOG_TAGS = [
    ("ypane", "#2563EB"),
    ("villeta", "#059669"),
    ("taekwondo", "#7C3AED"),
    ("examen", "#DC2626"),
    ("torneo", "#EA580C"),
    ("comunidad", "#6B7280"),
    ("entrenamiento", "#0891B2"),
    ("familias", "#BE185D"),
]

RESOURCE_TAGS = ["poomsae", "sparring", "calentamiento", "disciplina", "familias", "competencia"]

# --- Registro: plantillas de clase -------------------------------------------
DEMO_TEMPLATE_NAMES = (
    "Formativo Infantil Ypané",
    "Sparring Avanzado Villeta",
    "Entrenamiento Familiar Ypané",
)

# --- Registro: clases semanales (6 franjas, 3 por sede) ----------------------
# gaps entre franjas de una misma sede <= 3 días: garantiza que la cohorte en
# riesgo tenga su última asistencia dentro de 35-60 días.
CLASS_SLOT_SPECS = [
    {
        "slot": 0, "academy": "Y", "day_offset": 0, "time": time(18, 0),
        "name": "Taekwondo Formativo Ypané",
        "description": "Fundamentos para jóvenes: flexibilidad, técnicas básicas y disciplina.",
        # Capacidad menor que el padrón disponible de la sede (padrón 16, con
        # la cohorte en riesgo apartada quedan ~14): habilita el escenario de
        # clase COMPLETA con lista de espera real.
        "duration": timedelta(minutes=75), "max_students": 12,
        "class_type": "regular", "difficulty": "kyu_a",
        "equipment": "Dobok, cinturón y botella de agua",
        "notes": "Grupo inicial mixto de la sede Ypané.",
    },
    {
        "slot": 1, "academy": "Y", "day_offset": 3, "time": time(19, 0),
        "name": "Preparación de Examen Ypané",
        "description": "Repaso técnico para las próximas mesas de evaluación de cinturones.",
        "duration": timedelta(minutes=90), "max_students": 12,
        "class_type": "exam", "difficulty": "kyu_b",
        "equipment": "Dobok, cuaderno y lista de puntos del examen",
        "notes": "Ciclo de preparación previa a cada mesa de examen.",
    },
    {
        "slot": 2, "academy": "Y", "day_offset": 5, "time": time(9, 30),
        "name": "Clase Familiar Ypané",
        "description": "Práctica sabatina para todos los niveles: hermanos, padres e hijos.",
        "duration": timedelta(minutes=70), "max_students": 18,
        "class_type": "regular", "difficulty": "all",
        "equipment": "Dobok opcional para quienes visitan la clase por primera vez",
        "notes": "Bloque sabatino pensado para familias.",
    },
    {
        "slot": 3, "academy": "V", "day_offset": 1, "time": time(19, 0),
        "name": "Sparring Técnico Villeta",
        "description": "Asaltos controlados y desplazamiento táctico para competencia.",
        # Igual que la franja 0: capacidad 10 con padrón disponible ~12 habilita
        # la segunda clase completa con lista de espera.
        "duration": timedelta(minutes=80), "max_students": 10,
        "class_type": "intensive", "difficulty": "dan",
        "equipment": "Careta, guantes, protector bucal y espinilleras",
        "notes": "Grupo adulto orientado a la competencia.",
    },
    {
        "slot": 4, "academy": "V", "day_offset": 4, "time": time(18, 30),
        "name": "Defensa Personal Femenina Villeta",
        "description": "Escapes, distancia y recursos prácticos de autodefensa.",
        "duration": timedelta(minutes=75), "max_students": 14,
        "class_type": "regular", "difficulty": "kyu_a",
        "equipment": "Ropa deportiva y botella de agua",
        "notes": "Grupo de autodefensa con convocatoria creciente.",
    },
    {
        "slot": 5, "academy": "V", "day_offset": 5, "time": time(11, 0),
        "name": "Acondicionamiento Físico Villeta",
        "description": "Fuerza, movilidad y resistencia aplicadas al arte marcial.",
        "duration": timedelta(minutes=60), "max_students": 12,
        "class_type": "intensive", "difficulty": "kyu_b",
        "equipment": "Toalla, botella de agua y ropa deportiva",
        "notes": "Complemento físico para todos los grupos de la sede.",
    },
]
DEMO_CLASS_NAMES = tuple(spec["name"] for spec in CLASS_SLOT_SPECS)

# Cohorte en riesgo: últimos estudiantes seleccionados cuyo índice mapea a
# días transcurridos desde su última asistencia objetivo (35-60).
AT_RISK_CUTOFF_DAYS = {3: 36, 9: 43, 18: 50, 24: 56}

# --- Registro: eventos --------------------------------------------------------
DEMO_EVENT_NAMES = (
    "Copa Regional de Taekwondo - Ypané",
    "Torneo Apertura de Formas - Villeta",
    "Exhibición Comunitaria de Artes Marciales - Ypané",
    "Jornada de Ascensos de Cinturones - Sede Central",
)

EVENT_CATEGORY_DATA = [
    ("Torneo Regional", "Competencias intercities de formas y combate"),
    ("Exhibición Comunitaria", "Demostraciones abiertas en espacios públicos"),
    ("Ascenso de Cinturones", "Mesas de evaluación internas con presencia de familias"),
]

# --- Registro: sesiones de examen --------------------------------------------
# Se identifican por el prefijo invisible en belt_level (ver INVISIBLE_TAG).
EXAM_SESSION_PLAN = [
    # (clave de cinturón, días desde hoy, calificado)
    ("Amarillo", -40, True),
    ("Verde", -22, True),
    ("Azul", 21, False),
    ("Naranja", 33, False),
]
# Participantes por sesión (índices 0-based dentro de STUDENT_BASE) elegidos
# para que el cinturón de la sesión sea exactamente el siguiente del alumno.
EXAM_PARTICIPANT_PLAN = {
    "Amarillo": [0, 5, 10, 15, 20],   # cinturones Blanco -> aprueban 4, falla 1
    "Verde": [2, 7, 12, 17, 22],      # cinturones Naranja -> aprueban 4, falla 1
    "Azul": [8, 13, 23, 28],          # cinturones Verde -> anunciados
    "Naranja": [1, 6, 11, 16, 21],    # cinturones Amarillo -> anunciados
}

# --- Registro: blog -----------------------------------------------------------
DEMO_POST_TITLES = (
    "Inauguramos la nueva sede de Villeta",
    "Examen de cinturones: fechas, requisitos y recomendaciones",
    "Crónica de la Copa Regional de Taekwondo en Ypané",
    "Cinco consejos para aprovechar al máximo cada entrenamiento",
    "Primer aniversario de Teko Katu: gracias por acompañarnos",
    "Reunión de familias: cuotas, horarios y preguntas frecuentes",
)

# --- Registro: recursos --------------------------------------------------------
DEMO_RESOURCE_TITLES = (
    "Calentamiento completo para la clase de niños",
    "Poomsae Taegeuk Il Jang paso a paso",
    "Técnicas básicas de patada ITF",
    "Rutina de flexibilidad para hacer en casa",
    "Momentos destacados del torneo regional",
    "Defensa personal: escapes de muñeca y de cuello",
    "Reglamento de competición explicado en simples términos",
    "Guía para el cuidado del dobok",
    "Historia del taekwondo en Paraguay",
)

# --- Registro: galería ----------------------------------------------------------
DEMO_GALLERY_TITLES = (
    "Examen de cinturones - cierre de ciclo",
    "Torneo Regional Ypané",
    "Inauguración de la sede Villeta",
)

# --- Registro: mensajes de contacto ---------------------------------------------
DEMO_CONTACT_EMAILS = (
    "maria.rojas.familia@gmail.com",
    "julio.acosta.villeta@gmail.com",
    "direccion.colegiosanmartin@gmail.com",
    "gabriela.ruiz.consulta@gmail.com",
    "diego.peralta.consulta@gmail.com",
)

BASE_USERS = {
    "superadmin": [
        {
            "email": f"superadmin@{DEMO_EMAIL_DOMAIN}",
            "first_name": "Cesar",
            "last_name": "Benitez",
            "role": "admin",
            "city": "Ypane",
            "neighborhood": "Centro",
            "phone": "+595981700100",
            "academy": "Academia Teko Katu Ypane",
            "belt": "Negro 1 Dan",
            "gender": "M",
            "age": 41,
            "address": "Ruta PY01 km 24, Ypane",
            "bio": "Fundador de la academia. Supervisa las sedes de Ypané y Villeta.",
            "is_superuser": True,
            "is_staff": True,
            "is_exempt": True,
        }
    ],
    "admins": [
        {
            "email": f"admin.operations@{DEMO_EMAIL_DOMAIN}",
            "first_name": "Patricia",
            "last_name": "Gonzalez",
            "role": "admin",
            "city": "Villeta",
            "neighborhood": "San Jose",
            "phone": "+595981700101",
            "academy": "Academia Teko Katu Villeta",
            "belt": "Negro 1 Dan",
            "gender": "F",
            "age": 36,
            "address": "Av. Laudo Hayes 410, Villeta",
            "bio": "Coordina asistencia, cuotas y eventos abiertos de ambas sedes.",
            "is_superuser": False,
            "is_staff": True,
            "is_exempt": True,
        }
    ],
    "instructors": [
        {
            "email": f"lorena.vera@{DEMO_EMAIL_DOMAIN}",
            "first_name": "Lorena",
            "last_name": "Vera",
            "role": "instructor",
            "city": "Ypane",
            "neighborhood": "Thompson",
            "phone": "+595981700201",
            "academy": "Academia Teko Katu Ypane",
            "belt": "Negro 1 Dan",
            "gender": "F",
            "age": 29,
            "address": "Calle Thompson y Curupayty, Ypane",
            "bio": "Conduce los grupos formativos y las prácticas de defensa personal.",
            "is_staff": False,
            "is_exempt": True,
        },
        {
            "email": f"miguel.ortega@{DEMO_EMAIL_DOMAIN}",
            "first_name": "Miguel",
            "last_name": "Ortega",
            "role": "instructor",
            "city": "Villeta",
            "neighborhood": "Tacuruty",
            "phone": "+595981700202",
            "academy": "Academia Teko Katu Villeta",
            "belt": "Negro 1 Dan",
            "gender": "M",
            "age": 33,
            "address": "Barrio Tacuruty, Villeta",
            "bio": "Especialista en sparring y preparación de competidores.",
            "is_staff": False,
            "is_exempt": True,
        },
        {
            "email": f"noelia.ramirez@{DEMO_EMAIL_DOMAIN}",
            "first_name": "Noelia",
            "last_name": "Ramirez",
            "role": "instructor",
            "city": "Ypane",
            "neighborhood": "Paso de Oro",
            "phone": "+595981700203",
            "academy": "Academia Teko Katu Ypane",
            "belt": "Azul",
            "gender": "F",
            "age": 27,
            "address": "Paso de Oro, Ypane",
            "bio": "Apoya los grupos iniciales y las evaluaciones de menores.",
            "is_staff": False,
            "is_exempt": True,
        },
    ],
}

STUDENT_BASE = [
    ("Aldo", "Ayala", "Ypane", "Centro", "+595981800001", "Blanco", 14, "M"),
    ("Brisa", "Caballero", "Ypane", "Thompson", "+595981800002", "Amarillo", 13, "F"),
    ("Camila", "Duarte", "Ypane", "Paso de Oro", "+595981800003", "Naranja", 17, "F"),
    ("Diego", "Escobar", "Ypane", "Centro", "+595981800004", "Verde", 19, "M"),
    ("Elena", "Fernandez", "Ypane", "Costa Fleitas", "+595981800005", "Azul", 22, "F"),
    ("Fabian", "Gaona", "Ypane", "Thompson", "+595981800006", "Blanco", 15, "M"),
    ("Graciela", "Insfran", "Ypane", "Centro", "+595981800007", "Amarillo", 24, "F"),
    ("Hector", "Jara", "Ypane", "Paso de Oro", "+595981800008", "Naranja", 18, "M"),
    ("Ines", "Leguizamon", "Ypane", "Thompson", "+595981800009", "Verde", 16, "F"),
    ("Joel", "Maidana", "Ypane", "Costa Fleitas", "+595981800010", "Azul", 20, "M"),
    ("Karen", "Nunez", "Ypane", "Centro", "+595981800011", "Blanco", 12, "F"),
    ("Lucas", "Ortiz", "Ypane", "Paso de Oro", "+595981800012", "Amarillo", 21, "M"),
    ("Micaela", "Peralta", "Ypane", "Thompson", "+595981800013", "Naranja", 15, "F"),
    ("Nestor", "Quintana", "Ypane", "Centro", "+595981800014", "Verde", 27, "M"),
    ("Olga", "Rojas", "Ypane", "Costa Fleitas", "+595981800015", "Azul", 31, "F"),
    ("Pablo", "Sosa", "Ypane", "Paso de Oro", "+595981800016", "Blanco", 16, "M"),
    ("Rocio", "Acosta", "Villeta", "San Jose", "+595981810001", "Amarillo", 14, "F"),
    ("Santiago", "Barrios", "Villeta", "Tacuruty", "+595981810002", "Naranja", 18, "M"),
    ("Tamara", "Cantero", "Villeta", "Centro", "+595981810003", "Verde", 23, "F"),
    ("Ulises", "Delgado", "Villeta", "Ype Kae", "+595981810004", "Azul", 25, "M"),
    ("Valeria", "Estigarribia", "Villeta", "San Jose", "+595981810005", "Blanco", 13, "F"),
    ("Walter", "Franco", "Villeta", "Centro", "+595981810006", "Amarillo", 29, "M"),
    ("Ximena", "Gimenez", "Villeta", "Tacuruty", "+595981810007", "Naranja", 11, "F"),
    ("Yamil", "Herrera", "Villeta", "Ype Kae", "+595981810008", "Verde", 17, "M"),
    ("Zulma", "Ibarra", "Villeta", "Centro", "+595981810009", "Azul", 34, "F"),
    ("Adrian", "Jimenez", "Villeta", "San Jose", "+595981810010", "Blanco", 16, "M"),
    ("Belen", "Kuhn", "Villeta", "Tacuruty", "+595981810011", "Amarillo", 19, "F"),
    ("Cristian", "Lopez", "Villeta", "Centro", "+595981810012", "Naranja", 26, "M"),
    ("Daniela", "Martinez", "Villeta", "Ype Kae", "+595981810013", "Verde", 15, "F"),
    ("Ernesto", "Narvaez", "Villeta", "San Jose", "+595981810014", "Azul", 28, "M"),
]


def _stable_hash(*parts) -> int:
    """Hash entero determinista (FNV-1a) independiente del proceso.

    Se usa en lugar de hash() porque Python salta str.hash por proceso
    (PYTHONHASHSEED) y eso rompería la reproducibilidad del seed.
    """
    value = 2166136261
    for part in parts:
        value = ((value ^ (int(part) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return value


def _chance(*parts, percent: int) -> bool:
    return _stable_hash(*parts) % 100 < percent


def _propensity_percent(student_index: int) -> int:
    """Propensión personal de asistencia (50%..90%) por índice de estudiante."""
    return 50 + (student_index * 37) % 41


def _month_shift(month_start: date, shift: int) -> date:
    """Devuelve el primer día del mes con `shift` meses de diferencia."""
    total = month_start.year * 12 + (month_start.month - 1) + shift
    return date(total // 12, total % 12 + 1, 1)


def _covered_month_starts(today: date, past_months: int = 3) -> list[date]:
    """Meses cubiertos por el historial de cuotas demo (pasado + corriente).

    Funciona como registro de anclas para PaymentStats (no tiene campo de
    texto utilizable) y como clave de poda de pagos vía Payment.period.
    """
    current = today.replace(day=1)
    return [_month_shift(current, -offset) for offset in range(past_months, -1, -1)]


class Command(BaseCommand):
    help = "Crea o actualiza datos demo deterministas para la defensa de tesis, sin tocar datos reales."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=30, help="Cantidad de estudiantes demo (default: 30)")
        parser.add_argument("--instructors", type=int, default=3, help="Cantidad de instructores demo (default: 3)")
        parser.add_argument("--weeks", type=int, default=12, help="Semanas de calendario cubiertas, recomendado 10-16 (default: 12)")
        parser.add_argument("--reset-demo", action="store_true", help="Elimina solo los datos demo deterministas antes de volver a sembrar")
        parser.add_argument("--allow-production", action="store_true", help="Requerido junto con ALLOW_DEMO_SEED=true cuando DEBUG=False")

    def handle(self, *args, **options):
        self.validate_options(options)
        self.assert_safe_environment(options)

        # Crear reservas dispara señales en tiempo real (group_send); forzar un
        # channel layer en memoria para que un Redis ausente o inalcanzable no
        # pueda tumbar el comando durante el seed. Se restaura el valor original
        # al salir del bloque.
        #
        # Además se desconectan las señales que generan notificaciones y
        # contadores (reservas, asistencias, pagos): su comportamiento difiere
        # entre altas y actualizaciones y rompería la idempotencia del seed.
        # El comando cubre esos efectos de forma determinista (contadores por
        # clase, notificaciones sintéticas) y las señales SIEMPRE se
        # reconectan al salir, incluso ante errores.
        seed_signals = [
            (payment_created_or_updated, Payment),
            (payment_transaction_created, PaymentTransaction),
            (reservation_created_or_updated, UserClassReservation),
            (attendance_marked, ClassAttendance),
            (class_reservation_count_changed, Class),
        ]
        for receiver, sender in seed_signals:
            post_save.disconnect(receiver, sender=sender)
        try:
            with override_settings(
                CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
            ):
                with transaction.atomic():
                    if options["reset_demo"]:
                        self.reset_demo_data()

                    academies = self.seed_academies()
                    belts = self.seed_belt_ranks()
                    disciplines = self.seed_disciplines()
                    evaluation_parameters = self.seed_evaluation_parameters()
                    quota = self.ensure_quota_config()
                    users = self.seed_users(academies, belts, options["students"], options["instructors"])
                    # Limpia notificaciones de corridas o despliegues previos;
                    # las definitivas se generan sintéticas más abajo.
                    self.rebuild_notifications(users)
                    self.seed_notification_preferences(users["all"])
                    templates = self.seed_class_templates(users["instructors"], academies)
                    classes = self.seed_classes(users["instructors"], academies, options["weeks"])
                    self.seed_reservations_attendance_waitlist(classes, users["students"], users["instructors"])
                    self.seed_payments(users["students"], quota, users["admins"][0])
                    events = self.seed_events(users, disciplines)
                    self.seed_exam_sessions(users, belts, evaluation_parameters)
                    self.seed_blog(users)
                    self.seed_resources(users)
                    self.seed_gallery()
                    self.seed_contact_messages()
                    self.seed_notifications_mix(users)
                    self.refresh_performance_stats(users["students"])

            self.print_summary(users, classes, templates, events)
        finally:
            for receiver, sender in seed_signals:
                post_save.connect(receiver, sender=sender)

    def validate_options(self, options):
        if options["students"] < 24 or options["students"] > len(STUDENT_BASE):
            raise CommandError(f"--students debe estar entre 24 y {len(STUDENT_BASE)} para datos demo deterministas.")
        if options["instructors"] < 1 or options["instructors"] > len(BASE_USERS["instructors"]):
            raise CommandError(f"--instructors debe estar entre 1 y {len(BASE_USERS['instructors'])}.")
        if options["weeks"] < 8 or options["weeks"] > 16:
            raise CommandError("--weeks debe estar entre 8 y 16.")

    def assert_safe_environment(self, options):
        if settings.DEBUG:
            return
        if not options["allow_production"] or os.getenv("ALLOW_DEMO_SEED", "").lower() != "true":
            raise CommandError(
                "Seed de producción bloqueado. Con DEBUG=False debés pasar --allow-production "
                "y definir ALLOW_DEMO_SEED=true."
            )

    # ------------------------------------------------------------------
    # PODA / RESET
    # ------------------------------------------------------------------
    def reset_demo_data(self):
        """Elimina únicamente datos demo usando registros deterministas.

        Nunca borra catálogos compartidos (cinturones, disciplinas, categorías,
        etiquetas) ni usuarios con email fuera del dominio demo.
        """
        demo_users = list(User.objects.filter(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}"))
        demo_user_ids = [user.id for user in demo_users]

        Notification.objects.filter(recipient_id__in=demo_user_ids).delete()
        ExamResultParameterScore.objects.filter(exam_result__participant_id__in=demo_user_ids).delete()
        ExamResult.objects.filter(participant_id__in=demo_user_ids).delete()
        EventParticipation.objects.filter(user_id__in=demo_user_ids).delete()
        UserClassReservation.objects.filter(user_id__in=demo_user_ids).delete()
        ClassAttendance.objects.filter(user_id__in=demo_user_ids).delete()
        ClassWaitlist.objects.filter(user_id__in=demo_user_ids).delete()

        PaymentTransaction.objects.filter(payment__user_id__in=demo_user_ids).delete()
        Payment.objects.filter(user_id__in=demo_user_ids).delete()
        PerformanceStatistics.objects.filter(user_id__in=demo_user_ids).delete()
        UserNotificationPreference.objects.filter(user_id__in=demo_user_ids).delete()

        BlogPost.objects.filter(title__in=DEMO_POST_TITLES).delete()
        Resource.objects.filter(title__in=DEMO_RESOURCE_TITLES).delete()
        Event.objects.filter(name__in=DEMO_EVENT_NAMES).delete()
        # ExamSession no tiene campo único apto para registro: el prefijo de
        # ancho cero actúa como identificador invisible (ver INVISIBLE_TAG).
        ExamSession.objects.filter(belt_level__startswith=INVISIBLE_TAG).delete()
        ContactMessage.objects.filter(email__in=DEMO_CONTACT_EMAILS).delete()
        Gallery.objects.filter(title__in=DEMO_GALLERY_TITLES).delete()
        ClassTemplate.objects.filter(name__in=DEMO_TEMPLATE_NAMES).delete()
        Class.objects.filter(name__in=DEMO_CLASS_NAMES).delete()

        # Snapshots de estadísticas de pagos: anclas por inicio de mes cubierto.
        # Se incluye además la heurística legada (hoy y hoy-30) para limpiar
        # snapshots creados por versiones anteriores del comando.
        stats_dates = set(_covered_month_starts(timezone.localdate()))
        today = timezone.localdate()
        stats_dates.update({today - timedelta(days=30), today})
        PaymentStats.objects.filter(date__in=stats_dates).delete()

        User.objects.filter(id__in=demo_user_ids).delete()
        Academy.objects.filter(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}").delete()

        self.stdout.write(self.style.WARNING("Datos demo eliminados. Los catálogos compartidos se conservaron."))

    # ------------------------------------------------------------------
    # CATÁLOGOS BASE
    # ------------------------------------------------------------------
    def seed_academies(self):
        academies = {}
        for item in ACADEMY_DATA:
            academy, _ = Academy.objects.update_or_create(
                email=item["email"],
                defaults={
                    "name": item["name"],
                    "address": item["address"],
                    "phone": item["phone"],
                    "schedule": item["schedule"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "is_active": True,
                },
            )
            academies[academy.name] = academy
        return academies

    def seed_belt_ranks(self):
        belts = {}
        catalog_orders = {name: order_number for name, order_number, _category, _required in BELT_RANKS}
        conflicts = []
        for belt in BeltRank.objects.all():
            if belt.name in catalog_orders:
                if catalog_orders[belt.name] != belt.order_number:
                    conflicts.append(
                        f"'{belt.name}' existe con order_number={belt.order_number}, "
                        f"el catálogo demo espera {catalog_orders[belt.name]}"
                    )
            elif belt.order_number in set(catalog_orders.values()):
                conflicts.append(
                    f"order_number={belt.order_number} está tomado por '{belt.name}', "
                    "que no forma parte del catálogo demo"
                )
        if conflicts:
            raise CommandError(
                "Conflictos de BeltRank detectados (name y order_number son únicos). "
                "Conciliar manualmente antes de sembrar: " + "; ".join(conflicts)
            )
        for name, order_number, category, required_classes in BELT_RANKS:
            belt, _ = BeltRank.objects.update_or_create(
                name=name,
                defaults={
                    "order_number": order_number,
                    "category": category,
                    "required_classes": required_classes,
                    "is_active": True,
                },
            )
            belts[name] = belt
        return belts

    def seed_disciplines(self):
        items = []
        for name in DISCIPLINES:
            discipline, _ = Discipline.objects.get_or_create(name=name)
            items.append(discipline)
        return items

    def seed_evaluation_parameters(self):
        items = []
        for name, category, description in EVALUATION_PARAMETERS:
            parameter, _ = EvaluationParameter.objects.update_or_create(
                name=name,
                defaults={"category": category, "description": description},
            )
            items.append(parameter)
        return items

    def ensure_quota_config(self):
        active = QuotaConfig.get_active_config()
        if active:
            return active
        return QuotaConfig.objects.create(amount=Decimal("180000.00"), due_day=10, is_active=True)

    # ------------------------------------------------------------------
    # USUARIOS
    # ------------------------------------------------------------------
    def seed_users(self, academies, belts, student_count, instructor_count):
        users = {"all": [], "admins": [], "instructors": [], "students": []}
        desired_demo_emails = set()

        for item in BASE_USERS["superadmin"] + BASE_USERS["admins"]:
            user = self.upsert_user(item, academies, belts)
            users["all"].append(user)
            users["admins"].append(user)
            desired_demo_emails.add(user.email)

        for item in BASE_USERS["instructors"][:instructor_count]:
            user = self.upsert_user(item, academies, belts)
            users["all"].append(user)
            users["instructors"].append(user)
            desired_demo_emails.add(user.email)

        for index, row in enumerate(STUDENT_BASE[:student_count], start=1):
            first_name, last_name, city, neighborhood, phone, belt_name, age, gender = row
            academy_name = "Academia Teko Katu Ypane" if city == "Ypane" else "Academia Teko Katu Villeta"
            email = f"student{index:02d}.{first_name.lower()}.{last_name.lower()}@{DEMO_EMAIL_DOMAIN}"
            user = self.upsert_user(
                {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": "student",
                    "city": city,
                    "neighborhood": neighborhood,
                    "phone": phone,
                    "academy": academy_name,
                    "belt": belt_name,
                    "gender": gender,
                    "age": age,
                    "address": f"{neighborhood}, {city}",
                    "bio": "Alumno regular de la academia. Le gusta entrenar en grupo y participar de los torneos locales.",
                    "is_staff": False,
                    "is_exempt": index % 11 == 0,
                },
                academies,
                belts,
            )
            users["all"].append(user)
            users["students"].append(user)
            desired_demo_emails.add(user.email)

        User.objects.filter(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}").exclude(email__in=desired_demo_emails).delete()

        # Los exentos no abonan cuota: cualquier pago autogenerado por la señal
        # de alta de perfil queda fuera del escenario demo.
        exempt_ids = [user.id for idx, user in enumerate(users["students"], start=1) if idx % 11 == 0]
        PaymentTransaction.objects.filter(payment__user_id__in=exempt_ids).delete()
        Payment.objects.filter(user_id__in=exempt_ids).delete()
        return users

    def upsert_user(self, item, academies, belts):
        user, created = User.objects.update_or_create(
            email=item["email"],
            defaults={
                "first_name": item["first_name"],
                "last_name": item["last_name"],
                # En seeds tipo producción (DEBUG=False) el superusuario demo
                # se desactiva a propósito; el resto de los usuarios demo queda
                # activo.
                "is_active": settings.DEBUG or not item.get("is_superuser", False),
                "is_staff": item.get("is_staff", False),
                "is_superuser": item.get("is_superuser", False),
            },
        )
        user.set_password(DEFAULT_DEMO_PASSWORD)
        user.save(update_fields=["password"])

        profile = user.userprofile
        birth_year = timezone.localdate().year - item.get("age", 18)
        profile.role = item["role"]
        profile.belt_rank = belts.get(item.get("belt"))
        profile.dojo = academies[item["academy"]]
        profile.is_exempt = item.get("is_exempt", False)
        profile.address = item.get("address")
        profile.bio = item.get("bio")
        profile.age = item.get("age")
        profile.date_of_birth = date(birth_year, 6, 15)
        profile.gender = item.get("gender")
        profile.city = item.get("city")
        profile.state = "Central"
        profile.country = "Paraguay"
        profile.neighborhood = item.get("neighborhood")
        profile.phone_number = item.get("phone")
        profile.emergency_contact = "+595981999999"
        profile.social_media_links = {"instagram": "@academiatekokatu"}
        profile.save()

        if created and item["role"] != "student":
            Payment.objects.filter(user=user).delete()
        return user

    def seed_notification_preferences(self, users):
        for index, user in enumerate(users):
            UserNotificationPreference.objects.update_or_create(
                user=user,
                defaults={
                    "enabled": True,
                    "receive_realtime": index % 5 != 0,
                },
            )

    def rebuild_notifications(self, users):
        """Borra notificaciones de usuarios demo antes de sembrar actividad.

        Las señales de reservas, asistencias y pagos generan notificaciones en
        cada corrida; partir de cero garantiza conteos idempotentes.
        """
        demo_ids = [user.id for user in users["all"]]
        Notification.objects.filter(recipient_id__in=demo_ids).delete()

    # ------------------------------------------------------------------
    # PLANTILLAS Y CLASES
    # ------------------------------------------------------------------
    def seed_class_templates(self, instructors, academies):
        template_specs = [
            (DEMO_TEMPLATE_NAMES[0], instructors[0], "regular", "beginner", academies["Academia Teko Katu Ypane"].name, 18),
            (DEMO_TEMPLATE_NAMES[1], instructors[min(1, len(instructors) - 1)], "intensive", "advanced", academies["Academia Teko Katu Villeta"].name, 14),
            (DEMO_TEMPLATE_NAMES[2], instructors[-1], "regular", "all_levels", academies["Academia Teko Katu Ypane"].name, 22),
        ]
        templates = []
        for name, instructor, class_type, level, location, max_students in template_specs:
            template, _ = ClassTemplate.objects.update_or_create(
                name=name,
                instructor=instructor,
                defaults={
                    "description": "Plantilla reutilizable para armar la clase semanal correspondiente sin cargar todo manualmente.",
                    "class_type": class_type,
                    "difficulty_level": level,
                    "duration": timedelta(minutes=75),
                    "max_students": max_students,
                    "location": location,
                    "equipment_needed": "Dobok, botella de agua y espinilleras para los asaltos.",
                    "prerequisites": "Asistencia constante y puntualidad.",
                    "is_active": True,
                },
            )
            templates.append(template)
        ClassTemplate.objects.filter(name__in=DEMO_TEMPLATE_NAMES).exclude(
            pk__in=[item.pk for item in templates]
        ).delete()
        return templates

    def seed_classes(self, instructors, academies, weeks):
        now = timezone.localtime()
        monday = (now - timedelta(days=now.weekday())).date() - timedelta(weeks=max(weeks - 2, 1))

        ypane_instructor = instructors[0]
        villeta_instructor = instructors[min(1, len(instructors) - 1)]
        support_instructor = instructors[-1]

        classes = []
        for week in range(weeks):
            for spec in CLASS_SLOT_SPECS:
                class_date = timezone.make_aware(
                    datetime.combine(monday + timedelta(weeks=week, days=spec["day_offset"]), spec["time"])
                )
                # Una clase pasada cancelada para mostrar el flujo completo.
                is_cancelled_slot = (week == 1 and spec["slot"] == 1)
                cancelled_at = class_date - timedelta(days=2) if is_cancelled_slot else None
                if spec["academy"] == "Y":
                    instructor = support_instructor if spec["slot"] == 2 else ypane_instructor
                else:
                    instructor = villeta_instructor
                defaults = {
                    "description": spec["description"],
                    "instructor": instructor,
                    "max_students": spec["max_students"],
                    "duration": spec["duration"],
                    "class_type": spec["class_type"],
                    "difficulty_level": spec["difficulty"],
                    "location": academies["Academia Teko Katu Ypane"].name if spec["academy"] == "Y" else academies["Academia Teko Katu Villeta"].name,
                    "equipment_needed": spec["equipment"],
                    "notes": spec["notes"],
                    "is_cancelled": is_cancelled_slot,
                    "cancellation_reason": "Superposición con evento municipal" if is_cancelled_slot else "",
                    "cancelled_by": instructor if is_cancelled_slot else None,
                    "cancelled_at": cancelled_at,
                }
                class_obj, _ = Class.objects.update_or_create(
                    name=spec["name"], date=class_date, defaults=defaults
                )
                if is_cancelled_slot and cancelled_at:
                    # La señal pre_save de Class sella cancelled_at con now();
                    # se vuelve a fijar el valor determinista por encima.
                    Class.objects.filter(pk=class_obj.pk).update(cancelled_at=cancelled_at)
                classes.append(class_obj)
        Class.objects.filter(name__in=DEMO_CLASS_NAMES).exclude(pk__in=[item.pk for item in classes]).delete()
        return classes

    # ------------------------------------------------------------------
    # RESERVAS, ASISTENCIA Y LISTAS DE ESPERA
    # ------------------------------------------------------------------
    def _is_blocked_by_risk(self, student_index, class_obj, now):
        cutoff_days = AT_RISK_CUTOFF_DAYS.get(student_index)
        if cutoff_days is None:
            return False
        return class_obj.date > now - timedelta(days=cutoff_days)

    def seed_reservations_attendance_waitlist(self, classes, students, instructors):
        now = timezone.now()
        pools = {
            "Y": [s for s in students if s.userprofile.city == "Ypane"],
            "V": [s for s in students if s.userprofile.city != "Ypane"],
        }

        # Se reconstruyen reservas/asistencias/listas desde cero en cada
        # corrida: las señales de creación disparan las notificaciones y así
        # los conteos quedan idempotentes entre ejecuciones.
        ClassAttendance.objects.filter(class_reserved__in=classes).delete()
        ClassWaitlist.objects.filter(class_reserved__in=classes).delete()
        UserClassReservation.objects.filter(class_reserved__in=classes).delete()

        # Escenario garantizado de clases completas con lista de espera:
        # primera ocurrencia futura de la franja 0 (Ypané) y de la 3 (Villeta).
        full_scenario_slots = {
            CLASS_SLOT_SPECS[0]["name"]: CLASS_SLOT_SPECS[0]["slot"],
            CLASS_SLOT_SPECS[3]["name"]: CLASS_SLOT_SPECS[3]["slot"],
        }
        upcoming_full_slots = {}
        for class_obj in sorted(classes, key=lambda item: item.date):
            slot = full_scenario_slots.get(class_obj.name)
            if slot is None or class_obj.date <= now or class_obj.is_cancelled:
                continue
            if slot not in upcoming_full_slots:
                upcoming_full_slots[slot] = class_obj.pk
        full_class_ids = set(upcoming_full_slots.values())

        for class_index, class_obj in enumerate(classes):
            pool = pools["Y" if class_obj.location == "Academia Teko Katu Ypane" else "V"]
            candidates = [
                (idx, student) for idx, student in enumerate(students)
                if student in pool and not self._is_blocked_by_risk(idx, class_obj, now)
            ]
            pool_size = len(candidates)
            if pool_size == 0:
                Class.objects.filter(pk=class_obj.pk).update(reservation_count=0)
                continue

            is_full_scenario = class_obj.pk in full_class_ids and class_obj.date > now
            if is_full_scenario:
                # Clase completa: se cubre TODO el aforo y el resto del padrón
                # disponible pasa a la lista de espera.
                reserve_n = min(class_obj.max_students, pool_size)
            else:
                shortfall = _stable_hash(class_obj.pk, 11) % 4  # 0..3 vacantes sin cubrir
                reserve_n = min(class_obj.max_students, max(pool_size - shortfall, 1))

            start = _stable_hash(class_obj.pk, pool_size) % pool_size
            selected = [candidates[(start + k) % pool_size] for k in range(reserve_n)]

            for _idx, student in selected:
                UserClassReservation.objects.create(
                    user=student,
                    class_reserved=class_obj,
                )

            active_count = UserClassReservation.objects.filter(
                class_reserved=class_obj, is_cancelled=False
            ).count()
            Class.objects.filter(pk=class_obj.pk).update(reservation_count=active_count)
            class_obj.refresh_from_db(fields=["reservation_count"])

            # Toda clase PRÓXIMA que queda llena con gente afuera recibe lista
            # de espera contigua 1..N (escenario designado u orgánico).
            leftover = pool_size - len(selected)
            if (
                class_obj.date > now
                and not class_obj.is_cancelled
                and len(selected) >= class_obj.max_students
                and leftover > 0
            ):
                self._seed_waitlist(class_obj, candidates, len(selected), min(leftover, 2))

            if class_obj.date >= now or class_obj.is_cancelled:
                continue

            # Asistencia orgánica: propensión personal + variación por clase.
            for sel_pos, (student_index, student) in enumerate(selected):
                rate = _propensity_percent(student_index)
                attended = _chance(class_obj.pk, student.pk, 7, percent=rate)
                class_start = class_obj.date
                attendance_defaults = {
                    "attended": attended,
                    "notes": (
                        ("Presente" if _chance(class_obj.pk, student.pk, 21, percent=50) else "Asistió a toda la clase")
                        if attended
                        else ("Ausente justificada" if _chance(class_obj.pk, student.pk, 23, percent=50) else "Inasistencia")
                    ),
                    "marked_by": instructors[class_index % len(instructors)],
                    "check_in_time": class_start - timedelta(minutes=10) if attended else None,
                    "check_out_time": class_start + class_obj.duration if attended else None,
                }
                ClassAttendance.objects.create(
                    class_reserved=class_obj,
                    user=student,
                    **attendance_defaults,
                )

            # Contadores que la señal desconectada mantenía: se recalculan una
            # vez por clase al finalizar sus registros de asistencia.
            Class.objects.filter(pk=class_obj.pk).update(
                attendance_count=ClassAttendance.objects.filter(class_reserved=class_obj, attended=True).count(),
                no_show_count=ClassAttendance.objects.filter(class_reserved=class_obj, attended=False).count(),
            )

    def _seed_waitlist(self, class_obj, candidates, reserve_n, waitlist_target):
        """Lista de espera 1..N con estados mixtos sobre una clase llena."""
        ClassWaitlist.objects.filter(class_reserved=class_obj).delete()
        waitlist_candidates = candidates[reserve_n:reserve_n + waitlist_target]
        notified_time = timezone.make_aware(
            datetime.combine(class_obj.date.date() - timedelta(days=1), time(12, 0))
        )
        for position, (_idx, student) in enumerate(waitlist_candidates, start=1):
            # save() asigna la posición secuencial (max+1 entre activas);
            # creando en orden quedan 1..N contiguas.
            ClassWaitlist.objects.create(
                user=student,
                class_reserved=class_obj,
                status="notified" if position == 2 else "waiting",
                notes="",
            )
        ClassWaitlist.objects.filter(
            class_reserved=class_obj, status="notified"
        ).update(notified_at=notified_time)

    # ------------------------------------------------------------------
    # PAGOS
    # ------------------------------------------------------------------
    def seed_payments(self, students, quota, admin_user):
        today = timezone.localdate()
        month_starts = _covered_month_starts(today, past_months=3)
        due_day = min(quota.due_day, 28)

        # Limpiar transacciones demo previas: permite recalcular la numeración
        # secuencial de recibos sin colisiones con corridas anteriores.
        PaymentTransaction.objects.filter(payment__user__email__iendswith=f"@{DEMO_EMAIL_DOMAIN}").delete()

        # Contador local (no global): cada corrida recomienza en la base fija,
        # así los recibos quedan deterministas entre ejecuciones.
        self._receipt_seq = DEMO_RECEIPT_BASE

        for student_index, student in enumerate(students):
            if (student_index + 1) % 11 == 0:
                continue  # exentos: sin cuotas (coherente con su perfil)

            desired_periods = []
            for month_start in month_starts:
                due_date = date(month_start.year, month_start.month, due_day)
                period = f"{due_date.year}-{due_date.month:02d}"
                desired_periods.append(period)
                is_current = month_start == month_starts[-1]

                description = (
                    f"Cuota mensual correspondiente a {MONTH_NAMES_ES[due_date.month - 1]} {due_date.year}"
                )
                payment, _ = Payment.objects.update_or_create(
                    user=student,
                    period=period,
                    defaults={
                        "amount": quota.amount,
                        "description": description,
                        "amount_paid": Decimal("0.00"),
                        "is_paid": False,
                        "is_fully_paid": False,
                        "due_date": due_date,
                    },
                )

                if is_current:
                    # Mes en curso: mezcla realista de cobros tempranos,
                    # pagos parciales y cuotas aún pendientes.
                    pattern = student_index % 5
                    if pattern in (0, 1):
                        self._pay_full(payment, student_index, due_date, admin_user)
                    elif pattern == 2:
                        self._pay_partial(payment, due_date, admin_user)
                    # patrones 3 y 4: quedan pendientes de mes en curso
                else:
                    pattern = (student_index + due_date.month * 3) % 10
                    if pattern < 7:
                        self._pay_full(payment, student_index, due_date, admin_user)
                    elif pattern == 7:
                        self._pay_partial(payment, due_date, admin_user)
                    # patrones 8 y 9: vencidas e impagas

                # Ancla determinista de generación de la cuota (inicio del mes).
                Payment.objects.filter(pk=payment.pk).update(
                    date_payment=timezone.make_aware(datetime.combine(due_date.replace(day=1), time(9, 0)))
                )

            # Fuera del escenario demo: meses futuros autogenerados por la señal
            # de alta del perfil u otras corridas con distinto alcance.
            Payment.objects.filter(user=student).exclude(period__in=desired_periods).delete()

            # Bandera de mora coherente con la fecha del día.
            Payment.objects.filter(user=student, is_fully_paid=False, due_date__lt=today).update(is_overdue=True)
            Payment.objects.filter(user=student, due_date__gte=today).update(is_overdue=False)

        self.seed_payment_stats()

    def _pay_full(self, payment, student_index, due_date, admin_user):
        payment.amount_paid = payment.amount
        payment.is_paid = True
        payment.is_fully_paid = True
        payment.save(update_fields=["amount_paid", "is_paid", "is_fully_paid"])

        use_transfer = student_index % 2 == 0
        if _chance(student_index, due_date.month, 31, percent=33):
            # Pago dividido: seña en efectivo + saldo por transferencia.
            first = (payment.amount * Decimal("0.60")).quantize(Decimal("0.01"))
            second = payment.amount - first
            self._create_transaction(
                payment, first, "cash", due_date - timedelta(days=5),
                "Seña de cuota en efectivo", admin_user,
            )
            self._create_transaction(
                payment, second, "transfer", due_date - timedelta(days=1),
                "Saldo de cuota por transferencia", admin_user,
                reference=f"TRF-{due_date:%Y%m}-{student_index:03d}",
            )
        elif use_transfer:
            self._create_transaction(
                payment, payment.amount, "transfer", due_date - timedelta(days=2),
                "Cuota abonada por transferencia", admin_user,
                reference=f"TRF-{due_date:%Y%m}-{student_index:03d}",
            )
        else:
            self._create_transaction(
                payment, payment.amount, "cash", due_date - timedelta(days=2),
                "Cuota abonada en recepción", admin_user,
            )

    def _pay_partial(self, payment, due_date, admin_user):
        partial = (payment.amount * Decimal("0.50")).quantize(Decimal("0.01"))
        payment.amount_paid = partial
        payment.is_paid = True
        payment.is_fully_paid = False
        payment.save(update_fields=["amount_paid", "is_paid", "is_fully_paid"])
        self._create_transaction(
            payment, partial, "cash", due_date - timedelta(days=1),
            "Pago parcial en recepción", admin_user,
        )

    def _create_transaction(self, payment, amount, method, recorded_date, description, admin_user, reference=None):
        self._receipt_seq += 1
        receipt = f"RC-{recorded_date.year}-{self._receipt_seq:06d}"
        transaction = PaymentTransaction.objects.create(
            payment=payment,
            amount=amount,
            description=description,
            payment_method=method,  # solo 'cash' | 'transfer' (choices válidas)
            registered_by=admin_user,
            reference_number=reference,
            # Identificador interno neutro (visible solo en auditoría).
            external_transaction_id=f"OP-{payment.period}-{self._receipt_seq:06d}",
            receipt_number=receipt,
        )
        recorded_at = timezone.make_aware(datetime.combine(recorded_date, time(10, 30)))
        PaymentTransaction.objects.filter(pk=transaction.pk).update(transaction_date=recorded_at)
        Payment.objects.filter(pk=payment.pk).update(date_payment=recorded_at)
        return transaction

    def get_demo_stats_dates(self):
        """Fechas snapshot de PaymentStats que posee el seed (anclas mensuales)."""
        return _covered_month_starts(timezone.localdate(), past_months=3)

    def seed_payment_stats(self):
        today = timezone.localdate()
        stats_dates = self.get_demo_stats_dates()
        for stats_date in stats_dates:
            month_payments = Payment.objects.filter(
                due_date__year=stats_date.year, due_date__month=stats_date.month
            )
            total_collected = sum((payment.amount_paid for payment in month_payments), Decimal("0.00"))
            pending_amount = sum(
                (payment.amount - payment.amount_paid for payment in month_payments if payment.due_date >= today),
                Decimal("0.00"),
            )
            overdue_amount = sum(
                (payment.amount - payment.amount_paid for payment in month_payments if payment.due_date < today),
                Decimal("0.00"),
            )
            expected = sum((payment.amount for payment in month_payments), Decimal("0.00"))
            rate = Decimal("0.00") if expected == 0 else (total_collected / expected * Decimal("100.00")).quantize(Decimal("0.01"))

            PaymentStats.objects.update_or_create(
                date=stats_date,
                defaults={
                    "total_collected": total_collected,
                    "pending_amount": pending_amount,
                    "overdue_amount": overdue_amount,
                    "payment_count": month_payments.count(),
                    "collection_rate": rate,
                },
            )

    # ------------------------------------------------------------------
    # EVENTOS
    # ------------------------------------------------------------------
    def seed_events(self, users, disciplines):
        # Primero se podan los eventos demo previos: las fechas se corren con
        # el día actual, así que update_or_create solo acumularía filas viejas.
        Event.objects.filter(name__in=DEMO_EVENT_NAMES).delete()
        categories = {}
        for name, description in EVENT_CATEGORY_DATA:
            category, _ = EventCategory.objects.update_or_create(
                name=name,
                defaults={"description": description, "is_active": True},
            )
            categories[name] = category

        today = timezone.localdate()
        event_specs = [
            (DEMO_EVENT_NAMES[0], today - timedelta(days=52), "Polideportivo de Villeta", categories["Torneo Regional"], True),
            (DEMO_EVENT_NAMES[1], today - timedelta(days=24), "Club Social de Villeta", categories["Torneo Regional"], True),
            (DEMO_EVENT_NAMES[2], today + timedelta(days=13), "Plaza Mariscal López, Ypané", categories["Exhibición Comunitaria"], False),
            (DEMO_EVENT_NAMES[3], today + timedelta(days=30), "Academia Teko Katu Ypane", categories["Ascenso de Cinturones"], False),
        ]
        created_events = []
        for index, (name, event_date, location, category, is_past) in enumerate(event_specs):
            event, _ = Event.objects.update_or_create(
                name=name,
                event_date=event_date,
                defaults={
                    "description": (
                        "Jornada de artes marciales con participación de alumnos de las sedes Ypané y Villeta. "
                        "Entrada libre y gratuita para las familias."
                    ),
                    "location": location,
                    "organizer": "Federación Central de Taekwondo",
                    "is_verified": True,
                    "created_by": users["admins"][0],
                    "verified_by": users["admins"][0],
                    "verified_at": timezone.now(),
                },
            )
            event.disciplines.set(disciplines)
            event.categories.set([category])
            created_events.append(event)

            if is_past:
                participants = users["students"][index * 4 : index * 4 + 8]
                result_cycle = ["1st", "2nd", "3rd", "participation", "participation", "exhibition", "participation", "participation"]
                for participation_index, student in enumerate(participants):
                    EventParticipation.objects.update_or_create(
                        event=event,
                        user=student,
                        event_category=category,
                        defaults={
                            "result": result_cycle[participation_index],
                            "is_verified": True,
                            "verified_by": users["admins"][0],
                            "verified_at": timezone.now(),
                        },
                    )
            else:
                # Inscripciones anticipadas sin verificar todavía.
                participants = users["students"][index * 3 : index * 3 + 5]
                for student in participants:
                    EventParticipation.objects.update_or_create(
                        event=event,
                        user=student,
                        event_category=category,
                        defaults={
                            "result": "participation",
                            "is_verified": False,
                        },
                    )
        return created_events

    # ------------------------------------------------------------------
    # SESIONES DE EXAMEN
    # ------------------------------------------------------------------
    def seed_exam_sessions(self, users, belts, evaluation_parameters):
        # Se podan las sesiones demo previas (prefijo invisible en belt_level):
        # las fechas se mueven con el día actual. Resultados y puntajes cascadan
        # por FK; los vínculos M2M se limpian solos.
        ExamSession.objects.filter(belt_level__startswith=INVISIBLE_TAG).delete()
        today = timezone.localdate()
        for belt_key, day_offset, graded in EXAM_SESSION_PLAN:
            belt = belts[belt_key]
            exam_date = today + timedelta(days=day_offset)
            exam_session, _ = ExamSession.objects.update_or_create(
                belt_rank=belt,
                exam_date=exam_date,
                defaults={
                    # Prefijo invisible: identifica la fila como demo sin mostrar
                    # nada legible en pantallas ni reportes.
                    "belt_level": f"{INVISIBLE_TAG}{belt.name}",
                    "created_by": users["admins"][0],
                },
            )
            exam_session.evaluation_parameters.set(evaluation_parameters)

            participants = [users["students"][position] for position in EXAM_PARTICIPANT_PLAN[belt_key]]
            exam_session.participants.set(participants)
            for participant_index, participant in enumerate(participants):
                # Bypass de ExamResult.save(): al aprobar promueve el cinturón
                # del perfil y rompería los perfiles deterministas. Queryset
                # update()/bulk_create() omiten save() por completo.
                existing_results = ExamResult.objects.filter(exam_session=exam_session, participant=participant)
                if graded:
                    # Mesa ya calificada: mayoría aprobada, una falla por mesa.
                    passed = participant_index < len(participants) - 1
                else:
                    passed = False
                if existing_results.exists():
                    existing_results.update(graded=graded, passed=passed)
                    result = existing_results.first()
                else:
                    result = ExamResult.objects.bulk_create(
                        [
                            ExamResult(
                                exam_session=exam_session,
                                participant=participant,
                                graded=graded,
                                passed=passed,
                            )
                        ]
                    )[0]
                if graded:
                    for score_index, parameter in enumerate(evaluation_parameters, start=1):
                        ExamResultParameterScore.objects.update_or_create(
                            exam_result=result,
                            parameter=parameter,
                            defaults={"score": 65 + ((participant_index * 7 + score_index * 5) % 30)},
                        )

    # ------------------------------------------------------------------
    # BLOG
    # ------------------------------------------------------------------
    def seed_blog(self, users):
        second_instructor = users["instructors"][min(1, len(users["instructors"]) - 1)]
        categories = {}
        for name, description, color in BLOG_CATEGORIES:
            category, _ = Category.objects.update_or_create(
                name=name,
                defaults={"description": description, "color": color},
            )
            categories[name] = category

        tags = {}
        for name, color in BLOG_TAGS:
            tag, _ = Tag.objects.update_or_create(name=name, defaults={"color": color})
            tags[name] = tag

        t = tags
        posts = [
            {
                "title": DEMO_POST_TITLES[0],
                "author": users["instructors"][0],
                "category": categories["Comunidad"],
                "content": (
                    "Abrimos las puertas de nuestra nueva sede de Villeta con una jornada de puertas abiertas. "
                    "Familias, vecinos y alumnos recorrieron el salón principal y participaron de una clase muestra.\n\n"
                    "Agradecemos a la Municipalidad por el acompañamiento y a cada familia que acercó su apoyo. "
                    "Los horarios de la nueva sede ya están disponibles en la cartelera y en esta web."
                ),
                "is_featured": True,
                "tags": [t["villeta"], t["taekwondo"], t["comunidad"]],
            },
            {
                "title": DEMO_POST_TITLES[1],
                "author": users["admins"][0],
                "category": categories["Eventos"],
                "content": (
                    "Ya están abiertas las inscripciones para la próxima mesa de evaluación. Recordá presentar el "
                    "carnet al día, el dobok completo y la libreta de técnicas firmada por tu instructor.\n\n"
                    "Los requisitos de clases asistidas por rango se consultan desde la sección de progreso. "
                    "Ante cualquier duda, conversalo en clase o escribinos por la página de contacto."
                ),
                "is_featured": True,
                "tags": [t["examen"], t["ypane"], t["villeta"]],
            },
            {
                "title": DEMO_POST_TITLES[2],
                "author": second_instructor,
                "category": categories["Eventos"],
                "content": (
                    "El equipo regresó de la Copa Regional con medallas y muchas enseñanzas. Destacamos la actuación "
                    "de los debutantes, que subieron al tapete con serenidad y buen espíritu.\n\n"
                    "Gracias a los jueces voluntarios y a las familias que viajaron para alentar. Las fotos del "
                    "torneo ya están cargadas en la galería de la academia."
                ),
                "is_featured": False,
                "tags": [t["torneo"], t["ypane"], t["taekwondo"]],
            },
            {
                "title": DEMO_POST_TITLES[3],
                "author": users["instructors"][0],
                "category": categories["Entrenamiento"],
                "content": (
                    "Llegar cinco minutos antes permite empezar la movilidad con calma y aprovechar mejor la parte técnica. "
                    "Es el consejo número uno de este resumen.\n\n"
                    "Además: hidratarse antes de entrar al tatami, registrar las series en la libreta, preguntar las dudas "
                    "en el momento y repetir la forma diez veces despacio antes de llevarla a velocidad. La constancia hace el resto."
                ),
                "is_featured": False,
                "tags": [t["entrenamiento"], t["taekwondo"]],
            },
            {
                "title": DEMO_POST_TITLES[4],
                "author": users["admins"][0],
                "category": categories["Comunidad"],
                "content": (
                    "Cumplimos nuestro primer año con dos sedes activas, tres instructores titulados y una comunidad que "
                    "crece clase a clase. Lo celebramos con una clase abierta y merienda compartida.\n\n"
                    "Seguimos trabajando para que cada alumno encuentre en la escuela un lugar de aprendizaje y respeto. "
                    "Gracias por ser parte de este primer año."
                ),
                "is_featured": True,
                "tags": [t["comunidad"], t["familias"], t["ypane"]],
            },
            {
                "title": DEMO_POST_TITLES[5],
                "author": users["admins"][0],
                "category": categories["Comunidad"],
                "content": (
                    "Repasamos los temas más consultados de la reunión de familias: vencimientos de cuota, justificación de "
                    "inasistencias y uso del sistema de reservas de clase.\n\n"
                    "La cuota vence el día 10 de cada mes y puede abonarse en recepción o por transferencia. Si tu hijo/a va a "
                    "faltar más de dos semanas, avisá al instructor para planificar su retorno."
                ),
                "is_featured": False,
                "tags": [t["familias"], t["comunidad"]],
            },
        ]

        Comment.objects.filter(blog_post__title__in=DEMO_POST_TITLES).delete()
        Rating.objects.filter(blog_post__title__in=DEMO_POST_TITLES).delete()

        comment_bank = [
            "¡Qué buena noticia! Nos alegra mucho leer esto.",
            "Gracias por la información, muy clara y completa.",
            "Nos vemos en la próxima clase, vamos con todo.",
            "Excelente crónica, felicitaciones a todo el equipo.",
            "Se agradece el recordatorio de los requisitos.",
        ]

        for post_index, post_data in enumerate(posts):
            post, _ = BlogPost.objects.update_or_create(
                title=post_data["title"],
                author=post_data["author"],
                defaults={
                    "content": post_data["content"],
                    "category": post_data["category"],
                    "is_featured": post_data["is_featured"],
                },
            )
            post.tags.set(post_data["tags"])

            comment_authors = [
                users["students"][post_index % len(users["students"])],
                users["students"][(post_index + 5) % len(users["students"])],
            ]
            for comment_index, author in enumerate(comment_authors):
                Comment.objects.create(
                    blog_post=post,
                    user=author,
                    content=comment_bank[(post_index + comment_index) % len(comment_bank)],
                )
            raters = [
                (4 + (post_index % 2), users["students"][(post_index + 2) % len(users["students"])]),
                (5, users["students"][(post_index + 7) % len(users["students"])]),
            ]
            for score, rater in raters:
                Rating.objects.update_or_create(
                    blog_post=post, user=rater, defaults={"score": score}
                )

    # ------------------------------------------------------------------
    # RECURSOS
    # ------------------------------------------------------------------
    def seed_resources(self, users):
        second_instructor = users["instructors"][min(1, len(users["instructors"]) - 1)]
        tag_map = {}
        for name in RESOURCE_TAGS:
            tag, _ = ResourceTag.objects.get_or_create(name=name)
            tag_map[name] = tag

        # Solo VIDEO y LINK con URL: evita DOCUMENT sin archivo, cuya descarga
        # fallaría en la demo.
        resources = [
            (DEMO_RESOURCE_TITLES[0], ResourceType.VIDEO, ResourceCategory.TRAINING, ResourceLevel.KYU_A,
             "https://www.youtube.com/watch?v=calentam001", users["instructors"][0],
             [tag_map["calentamiento"], tag_map["familias"]],
             "Secuencia completa de calentamiento articular y movilidad para la clase infantil."),
            (DEMO_RESOURCE_TITLES[1], ResourceType.VIDEO, ResourceCategory.TECHNIQUE, ResourceLevel.KYU_A,
             "https://www.youtube.com/watch?v=poomsae101a", users["instructors"][0],
             [tag_map["poomsae"]],
             "Explicación paso a paso de la primera forma con vista frontal y lateral."),
            (DEMO_RESOURCE_TITLES[2], ResourceType.VIDEO, ResourceCategory.TECHNIQUE, ResourceLevel.KYU_B,
             "https://www.youtube.com/watch?v=pateoitf01b", second_instructor,
             [tag_map["sparring"], tag_map["disciplina"]],
             "Fundamentos de ap chagi y dollyo chagi con errores comunes y correcciones."),
            (DEMO_RESOURCE_TITLES[3], ResourceType.VIDEO, ResourceCategory.TRAINING, ResourceLevel.ALL,
             "https://www.youtube.com/watch?v=flexicasa02", users["instructors"][0],
             [tag_map["calentamiento"]],
             "Rutina de quince minutos para mejorar la flexibilidad desde casa, ideal para días sin clase."),
            (DEMO_RESOURCE_TITLES[4], ResourceType.VIDEO, ResourceCategory.COMPETITION, ResourceLevel.ALL,
             "https://www.youtube.com/watch?v=regional03c", users["admins"][0],
             [tag_map["competencia"], tag_map["sparring"]],
             "Selección de momentos destacados de nuestra participación en el torneo regional."),
            (DEMO_RESOURCE_TITLES[5], ResourceType.VIDEO, ResourceCategory.TECHNIQUE, ResourceLevel.ALL,
             "https://www.youtube.com/watch?v=escapes04dd", second_instructor,
             [tag_map["disciplina"]],
             "Práctica guiada de escapes de muñeca y de cuello con compañero de trabajo."),
            (DEMO_RESOURCE_TITLES[6], ResourceType.LINK, ResourceCategory.COMPETITION, ResourceLevel.KYU_B,
             "https://es.wikipedia.org/wiki/Taekwondo", users["admins"][0],
             [tag_map["competencia"]],
             "Referencia rápida del reglamento vigente: puntaje, penalizaciones y categorías de peso."),
            (DEMO_RESOURCE_TITLES[7], ResourceType.LINK, ResourceCategory.THEORY, ResourceLevel.ALL,
             "https://es.wikipedia.org/wiki/Dobok", users["instructors"][0],
             [tag_map["disciplina"], tag_map["familias"]],
             "Cómo lavar, doblar y conservar el uniforme para que dure todo el año."),
            (DEMO_RESOURCE_TITLES[8], ResourceType.LINK, ResourceCategory.HISTORY, ResourceLevel.ALL,
             "https://es.wikipedia.org/wiki/Historia_del_taekwondo", users["admins"][0],
             [],
             "Panorama histórico del arte marcial y su llegada y crecimiento en Paraguay."),
        ]

        for title, resource_type, category, level, url, author, resource_tags, description in resources:
            resource, _ = Resource.objects.update_or_create(
                title=title,
                defaults={
                    "description": description,
                    "type": resource_type,
                    "category": category,
                    "level": level,
                    "url": url,
                    "file": None,
                    "author": author,
                    "views_count": 15 + (_stable_hash(len(title)) % 120),
                    "downloads_count": 2 + (_stable_hash(len(title), 9) % 18),
                    "is_featured": True,
                    "is_premium": False,
                },
            )
            resource.tags.set(resource_tags)

    # ------------------------------------------------------------------
    # GALERÍA
    # ------------------------------------------------------------------
    def seed_gallery(self):
        albums = [
            (DEMO_GALLERY_TITLES[0], "Imágenes del cierre de ciclo y entrega de certificados a los evaluados."),
            (DEMO_GALLERY_TITLES[1], "Delegación, combates y premiación en la copa regional de este año."),
            (DEMO_GALLERY_TITLES[2], "Apertura oficial de la segunda sede con clase muestra y actividades para familias."),
        ]
        for title, description in albums:
            Gallery.objects.update_or_create(
                title=title,
                defaults={"description": description},
            )

    # ------------------------------------------------------------------
    # CONTACTO
    # ------------------------------------------------------------------
    def seed_contact_messages(self):
        messages = [
            (DEMO_CONTACT_EMAILS[0], "María Rojas", "+595981660100",
             "Buenas tardes, quisiera saber los horarios de iniciación para niños en la sede Ypané y si hay clase de prueba gratuita.", True),
            (DEMO_CONTACT_EMAILS[1], "Julio Acosta", "+595981660101",
             "Les escribo desde la comisión de fiestas de Villeta. Queremos invitarlos a dar una exhibición de artes marciales en el festival estudiantil.", True),
            (DEMO_CONTACT_EMAILS[2], "Dirección Colegio San Martín", "+59521555010",
             "Estamos evaluando un convenio de clases extracurriculares para nuestros alumnos de primaria. Solicitan enviar propuesta de horarios y aranceles.", True),
            (DEMO_CONTACT_EMAILS[3], "Gabriela Ruiz", "+595983660102",
             "Hola, vi el anuncio de defensa personal femenina. Quisiera saber si puedo empezar sin experiencia previa y qué ropa necesito.", False),
            (DEMO_CONTACT_EMAILS[4], "Diego Peralta", "+595984660103",
             "Consulta sobre el valor de la cuota familiar: tenemos tres hijos interesados en entrenar, ¿existe algún descuento?", False),
        ]
        for email, name, phone, body, is_read in messages:
            ContactMessage.objects.update_or_create(
                email=email,
                defaults={
                    "name": name,
                    "phone": phone,
                    "message": body,
                    "is_read": is_read,
                },
            )

    # ------------------------------------------------------------------
    # NOTIFICACIONES
    # ------------------------------------------------------------------
    def seed_notifications_mix(self, users):
        """Historial sintético por alumno + mezcla leído/no leído verosímil.

        Con las señales desconectadas, estas notificaciones son la fuente
        única y determinista: mismas cantidades en cada corrida.
        """
        history_themes = [
            ("class", "Reserva confirmada", "Tu reserva de la clase quedó registrada. ¡Nos vemos en el tatami!"),
            ("class", "Asistencia registrada", "El instructor cargó la asistencia de la última clase."),
            ("payment", "Pago recibido", "Tu pago fue acreditado. Gracias por mantener tu cuota al día."),
            ("info", "Recordatorio de clase", "Mañana tenés clase: prepará el dobok y llegá unos minutos antes."),
        ]
        for index, student in enumerate(users["students"]):
            # Dos avisos históricos (pasan a leídas) + uno vigente por tema.
            for offset in range(2):
                ntype, title, message = history_themes[(index + offset) % len(history_themes)]
                Notification.objects.create(
                    recipient=student, title=title, message=message, type=ntype, data={}
                )
            themes = [
                ("payment", "Recordatorio de cuota",
                 "Tu cuota del mes vence el día 10. Podés abonarla en recepción o por transferencia bancaria."),
                ("class", "Nueva clase disponible",
                 "Se habilitaron nuevos cupos para la semana. Reservá tu lugar desde el panel de clases."),
                ("info", "Convocatoria a examen de cinturones",
                 "Revisá tus clases asistidas en la sección de progreso y confirmá tu inscripción con el instructor."),
                ("success", "Inscripción al torneo regional",
                 "Tu inscripción quedó registrada. Cerca de la fecha enviaremos el cronograma de pesaje y categorías."),
            ]
            ntype, title, message = themes[index % len(themes)]
            Notification.objects.create(
                recipient=student,
                title=title,
                message=message,
                type=ntype,
                data={},
            )
        for instructor in users["instructors"]:
            Notification.objects.create(
                recipient=instructor,
                title="Resumen semanal de asistencias",
                message="El reporte de asistencia de tus clases de la semana ya está disponible en el panel.",
                type="info",
                data={},
            )
            Notification.objects.create(
                recipient=instructor,
                title="Nueva reserva en tu clase",
                message="Un alumno reservó su lugar para la próxima sesión.",
                type="class",
                data={},
            )
        for admin in users["admins"]:
            Notification.objects.create(
                recipient=admin,
                title="Reporte mensual de pagos listo",
                message="El consolidado de cuotas del mes anterior está disponible en la sección de reportes.",
                type="payment",
                data={},
            )

        # Mezcla leído/no leído: las dos más recientes de cada destinatario
        # quedan sin leer; el historial anterior pasa a leído.
        demo_ids = [user.id for user in users["all"]]
        for recipient_id in demo_ids:
            recent_ids = list(
                Notification.objects.filter(recipient_id=recipient_id)
                .order_by("-created_at", "-id")
                .values_list("id", flat=True)[:2]
            )
            Notification.objects.filter(recipient_id=recipient_id).exclude(id__in=recent_ids).update(is_read=True)

    # ------------------------------------------------------------------
    # ESTADÍSTICAS Y RESUMEN
    # ------------------------------------------------------------------
    def refresh_performance_stats(self, students):
        for student in students:
            stats, _ = PerformanceStatistics.objects.get_or_create(user=student)
            stats.update_statistics()

    def print_summary(self, users, classes, templates, events):
        now = timezone.now()
        past_classes = sum(1 for item in classes if item.date < now)
        attendance_total = ClassAttendance.objects.count()
        attendance_true = ClassAttendance.objects.filter(attended=True).count()
        reservation_total = UserClassReservation.objects.count()
        waitlist_total = ClassWaitlist.objects.filter(status__in=["waiting", "notified"]).count()
        payment_total = Payment.objects.count()
        transaction_total = PaymentTransaction.objects.count()
        stats_total = PaymentStats.objects.count()
        graded_sessions = ExamResult.objects.filter(graded=True).count()
        post_total = BlogPost.objects.count()
        comment_total = Comment.objects.count()
        rating_total = Rating.objects.count()
        resource_total = Resource.objects.count()
        album_total = Gallery.objects.count()
        contact_total = ContactMessage.objects.count()
        notification_total = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()

        self.stdout.write(self.style.SUCCESS("Seed demo completado correctamente."))
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    "DEBUG=False: la cuenta superusuario demo quedó desactivada (is_active=False) por diseño."
                )
            )
        self.stdout.write(f"Academias: {len(ACADEMY_DATA)}")
        self.stdout.write(
            f"Usuarios: {len(users['all'])} ({len(users['admins'])} administración, "
            f"{len(users['instructors'])} instructores, {len(users['students'])} estudiantes)"
        )
        self.stdout.write(f"Plantillas de clase: {len(templates)}")
        self.stdout.write(f"Clases: {len(classes)} ({past_classes} pasadas, {len(classes) - past_classes} próximas)")
        self.stdout.write(f"Reservas: {reservation_total}")
        self.stdout.write(
            f"Asistencias: {attendance_total} registros "
            f"({round(100 * attendance_true / attendance_total) if attendance_total else 0}% presentes)"
        )
        self.stdout.write(f"Listas de espera activas: {waitlist_total} entradas")
        self.stdout.write(f"Pagos: {payment_total} cuotas, {transaction_total} transacciones, {stats_total} snapshots mensuales")
        self.stdout.write(f"Eventos: {len(events)} (con participaciones y podios en los pasados)")
        self.stdout.write(f"Sesiones de examen: resultados calificados {graded_sessions}, próximas anunciadas")
        self.stdout.write(f"Blog: {post_total} entradas, {comment_total} comentarios, {rating_total} calificaciones")
        self.stdout.write(f"Recursos: {resource_total} | Galería: {album_total} álbumes (metadatos, sin archivos)")
        self.stdout.write(f"Mensajes de contacto: {contact_total}")
        self.stdout.write(f"Notificaciones: {notification_total} ({unread_notifications} sin leer)")
        self.stdout.write(f"Cuentas demo: *@{DEMO_EMAIL_DOMAIN}")
