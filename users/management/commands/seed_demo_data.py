from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from blog.models import BlogPost, Category, Comment, Rating, Tag
from classes.models import Class, ClassAttendance, ClassTemplate, ClassWaitlist, UserClassReservation
from contact.models import Academy, ContactMessage
from gallery.models import Gallery
from notifications.models import Notification, UserNotificationPreference
from payments.models import Payment, PaymentStats, PaymentTransaction, QuotaConfig
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

DEMO_MARKER = "[demo-seed-py]"
DEMO_EMAIL_DOMAIN = "demo.martial.local"
DEFAULT_DEMO_PASSWORD = "DemoSeed2026!"

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
    ("Blanco", 1, "Kyu A"),
    ("Amarillo", 2, "Kyu A"),
    ("Naranja", 3, "Kyu A"),
    ("Verde", 4, "Kyu A"),
    ("Azul", 5, "Kyu B"),
    ("Marron", 6, "Kyu B"),
    ("Rojo", 7, "Kyu B"),
    ("Negro 1 Dan", 8, "Dan"),
]

DISCIPLINES = [
    "Taekwondo ITF",
    "Taekwondo WT",
    "Defensa Personal",
]

EVALUATION_PARAMETERS = [
    ("Technique", "Form", "Execution quality and posture"),
    ("Power", "Physical", "Impact control and body mechanics"),
    ("Discipline", "Attitude", "Respect, focus and protocol"),
    ("Sparring", "Combat", "Distance, timing and control"),
]

BLOG_CATEGORIES = [
    ("Training", "Weekly progress and practice highlights", "#2563EB"),
    ("Community", "Academy activities in Ypane and Villeta", "#059669"),
    ("Events", "Exams, exhibitions and regional tournaments", "#D97706"),
]

BLOG_TAGS = [
    ("ypane", "#2563EB"),
    ("villeta", "#059669"),
    ("taekwondo", "#7C3AED"),
    ("belt-exam", "#DC2626"),
    ("community", "#6B7280"),
]

RESOURCE_TAGS = ["poomsae", "sparring", "warmup", "discipline", "parents", "competition"]

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
            "bio": "Founder supervising both demo branches for thesis presentation.",
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
            "bio": "Coordinates attendance, quotas and public events.",
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
            "bio": "Leads youth fundamentals and women's self-defense groups.",
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
            "bio": "Focuses on sparring and competition preparation.",
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
            "bio": "Supports beginner groups and school-age assessments.",
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


class Command(BaseCommand):
    help = "Create or refresh deterministic thesis demo data without wiping real data."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=30, help="Number of demo students to seed (default: 30)")
        parser.add_argument("--instructors", type=int, default=3, help="Number of demo instructors to seed (default: 3)")
        parser.add_argument("--weeks", type=int, default=10, help="Calendar span in weeks, recommended 8-12 (default: 10)")
        parser.add_argument("--reset-demo", action="store_true", help="Delete only deterministic demo data created by this command before reseeding")
        parser.add_argument("--allow-production", action="store_true", help="Required together with ALLOW_DEMO_SEED=true when DEBUG=False")

    def handle(self, *args, **options):
        self.validate_options(options)
        self.assert_safe_environment(options)

        # Crear reservas dispara señales en tiempo real (group_send); forzar un
        # channel layer en memoria para que un Redis ausente o inalcanzable no
        # pueda tumbar el comando durante el seed. Se restaura el valor original
        # al salir del bloque.
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
                self.seed_notification_preferences(users["all"])
                templates = self.seed_class_templates(users["instructors"], academies)
                classes = self.seed_classes(users["instructors"], academies, options["weeks"])
                self.seed_reservations_attendance_waitlist(classes, users["students"], users["instructors"])
                self.seed_payments(users["students"], quota)
                events = self.seed_events(users, disciplines)
                self.seed_exam_sessions(users, belts, evaluation_parameters)
                self.seed_blog(users)
                self.seed_resources(users)
                self.seed_gallery()
                self.seed_contact_messages()
                self.refresh_performance_stats(users["students"])

        self.print_summary(users, classes, templates, events)

    def validate_options(self, options):
        if options["students"] < 24 or options["students"] > len(STUDENT_BASE):
            raise CommandError(f"--students must be between 24 and {len(STUDENT_BASE)} for deterministic demo data.")
        if options["instructors"] < 1 or options["instructors"] > len(BASE_USERS["instructors"]):
            raise CommandError(f"--instructors must be between 1 and {len(BASE_USERS['instructors'])}.")
        if options["weeks"] < 8 or options["weeks"] > 12:
            raise CommandError("--weeks must be between 8 and 12.")

    def assert_safe_environment(self, options):
        if settings.DEBUG:
            return
        if not options["allow_production"] or os.getenv("ALLOW_DEMO_SEED", "").lower() != "true":
            raise CommandError(
                "Production seed blocked. When DEBUG=False you must pass --allow-production and set ALLOW_DEMO_SEED=true."
            )

    def reset_demo_data(self):
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
        # Stats snapshots are derived aggregates created by seed_payment_stats;
        # remove the ones it owns (same deterministic dates used at creation).
        PaymentStats.objects.filter(date__in=self.get_demo_stats_dates()).delete()
        PerformanceStatistics.objects.filter(user_id__in=demo_user_ids).delete()
        UserNotificationPreference.objects.filter(user_id__in=demo_user_ids).delete()

        BlogPost.objects.filter(content__icontains=DEMO_MARKER).delete()
        Resource.objects.filter(description__icontains=DEMO_MARKER).delete()
        Event.objects.filter(description__icontains=DEMO_MARKER).delete()
        ExamSession.objects.filter(belt_level__icontains=DEMO_MARKER).delete()
        ContactMessage.objects.filter(message__icontains=DEMO_MARKER).delete()
        Gallery.objects.filter(description__icontains=DEMO_MARKER).delete()
        ClassTemplate.objects.filter(description__icontains=DEMO_MARKER).delete()
        Class.objects.filter(notes__icontains=DEMO_MARKER).delete()

        User.objects.filter(id__in=demo_user_ids).delete()
        Academy.objects.filter(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}").delete()

        self.stdout.write(self.style.WARNING("Demo data removed. Shared reference catalogs were preserved."))

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
        catalog_orders = {name: order_number for name, order_number, _category in BELT_RANKS}
        conflicts = []
        for belt in BeltRank.objects.all():
            if belt.name in catalog_orders:
                if catalog_orders[belt.name] != belt.order_number:
                    conflicts.append(
                        f"'{belt.name}' exists with order_number={belt.order_number}, "
                        f"demo catalog expects {catalog_orders[belt.name]}"
                    )
            elif belt.order_number in set(catalog_orders.values()):
                conflicts.append(
                    f"order_number={belt.order_number} is taken by existing '{belt.name}', "
                    "which is not part of the demo catalog"
                )
        if conflicts:
            raise CommandError(
                "BeltRank conflicts detected (name and order_number are unique). "
                "Reconcile manually before seeding: " + "; ".join(conflicts)
            )
        for name, order_number, category in BELT_RANKS:
            belt, _ = BeltRank.objects.update_or_create(
                name=name,
                defaults={
                    "order_number": order_number,
                    "category": category,
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
                    "bio": f"{DEMO_MARKER} Demo student profile for thesis walkthrough.",
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

        Payment.objects.filter(user__email__iendswith=f"@{DEMO_EMAIL_DOMAIN}").exclude(
            user__userprofile__role="student"
        ).delete()
        return users

    def upsert_user(self, item, academies, belts):
        user, created = User.objects.update_or_create(
            email=item["email"],
            defaults={
                "first_name": item["first_name"],
                "last_name": item["last_name"],
                # In production-like seeds (DEBUG=False) the demo superuser is
                # deactivated on purpose; regular demo users stay active.
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
        profile.social_media_links = {"instagram": "@tekokatu_demo"}
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

    def seed_class_templates(self, instructors, academies):
        template_specs = [
            ("Ypane Kids Fundamentals", instructors[0], "regular", "beginner", academies["Academia Teko Katu Ypane"].name, 18),
            ("Villeta Sparring Lab", instructors[min(1, len(instructors) - 1)], "intensive", "advanced", academies["Academia Teko Katu Villeta"].name, 14),
            ("Ypane Family Training", instructors[-1], "regular", "all_levels", academies["Academia Teko Katu Ypane"].name, 22),
        ]
        templates = []
        for name, instructor, class_type, level, location, max_students in template_specs:
            template, _ = ClassTemplate.objects.update_or_create(
                name=name,
                instructor=instructor,
                defaults={
                    "description": f"{DEMO_MARKER} Reusable class template for thesis dashboard demos.",
                    "class_type": class_type,
                    "difficulty_level": level,
                    "duration": timedelta(minutes=75),
                    "max_students": max_students,
                    "location": location,
                    "equipment_needed": "Dobok, water bottle, shin guards for sparring sessions.",
                    "prerequisites": "Basic attendance discipline and punctuality.",
                    "is_active": True,
                },
            )
            templates.append(template)
        ClassTemplate.objects.filter(description__icontains=DEMO_MARKER).exclude(pk__in=[item.pk for item in templates]).delete()
        return templates

    def seed_classes(self, instructors, academies, weeks):
        now = timezone.localtime()
        monday = (now - timedelta(days=now.weekday())).date() - timedelta(weeks=4)
        schedule = [
            {
                "day_offset": 0,
                "name": "Taekwondo Formativo Ypane",
                "description": "Youth fundamentals, flexibility and discipline drills.",
                "time": time(18, 0),
                "duration": timedelta(minutes=75),
                "max_students": 16,
                "class_type": "regular",
                "difficulty": "kyu_a",
                "location": academies["Academia Teko Katu Ypane"].name,
                "equipment": "Dobok, belt, water bottle",
                "notes": f"{DEMO_MARKER} Mixed beginner group from Ypane.",
                "instructor": instructors[0],
            },
            {
                "day_offset": 1,
                "name": "Preparacion de Examen Villeta",
                "description": "Technique review for upcoming belt evaluations.",
                "time": time(19, 0),
                "duration": timedelta(minutes=90),
                "max_students": 14,
                "class_type": "exam",
                "difficulty": "kyu_b",
                "location": academies["Academia Teko Katu Villeta"].name,
                "equipment": "Dobok, notebook, belt checklist",
                "notes": f"{DEMO_MARKER} Exam preparation cycle for Villeta branch.",
                "instructor": instructors[min(1, len(instructors) - 1)],
            },
            {
                "day_offset": 3,
                "name": "Sparring Tecnico Villeta",
                "description": "Controlled sparring rounds and tactical movement.",
                "time": time(18, 30),
                "duration": timedelta(minutes=80),
                "max_students": 12,
                "class_type": "intensive",
                "difficulty": "dan",
                "location": academies["Academia Teko Katu Villeta"].name,
                "equipment": "Shin guards, gloves, mouth guard",
                "notes": f"{DEMO_MARKER} Competition-oriented adult group.",
                "instructor": instructors[min(1, len(instructors) - 1)],
            },
            {
                "day_offset": 5,
                "name": "Clase Familiar Ypane",
                "description": "Weekend all-level practice for siblings and parents.",
                "time": time(9, 0),
                "duration": timedelta(minutes=70),
                "max_students": 20,
                "class_type": "regular",
                "difficulty": "all",
                "location": academies["Academia Teko Katu Ypane"].name,
                "equipment": "Dobok optional for first-time visitors",
                "notes": f"{DEMO_MARKER} Saturday family attendance block.",
                "instructor": instructors[-1],
            },
        ]

        classes = []
        for week in range(weeks):
            for slot_index, spec in enumerate(schedule):
                class_date = timezone.make_aware(datetime.combine(monday + timedelta(weeks=week, days=spec["day_offset"]), spec["time"]))
                is_cancelled_slot = week == 2 and slot_index == 1
                cancelled_at = class_date - timedelta(days=2) if is_cancelled_slot else None
                defaults = {
                    "description": spec["description"],
                    "instructor": spec["instructor"],
                    "max_students": spec["max_students"],
                    "duration": spec["duration"],
                    "class_type": spec["class_type"],
                    "difficulty_level": spec["difficulty"],
                    "location": spec["location"],
                    "equipment_needed": spec["equipment"],
                    "notes": spec["notes"],
                    "is_cancelled": is_cancelled_slot,
                    "cancellation_reason": "Municipal event overlap" if is_cancelled_slot else "",
                    "cancelled_by": spec["instructor"] if is_cancelled_slot else None,
                    "cancelled_at": cancelled_at,
                }
                class_obj, _ = Class.objects.update_or_create(name=spec["name"], date=class_date, defaults=defaults)
                if is_cancelled_slot and cancelled_at:
                    # The Class pre_save signal stamps cancelled_at with now();
                    # pin the deterministic value back over whatever it wrote.
                    Class.objects.filter(pk=class_obj.pk).update(cancelled_at=cancelled_at)
                classes.append(class_obj)
        Class.objects.filter(notes__icontains=DEMO_MARKER).exclude(pk__in=[item.pk for item in classes]).delete()
        return classes

    def seed_reservations_attendance_waitlist(self, classes, students, instructors):
        ClassAttendance.objects.filter(class_reserved__in=classes).delete()
        ClassWaitlist.objects.filter(class_reserved__in=classes).delete()
        UserClassReservation.objects.filter(class_reserved__in=classes).delete()

        for class_index, class_obj in enumerate(classes):
            offset = class_index % len(students)
            reserved_students = [students[(offset + i) % len(students)] for i in range(min(class_obj.max_students, 8))]

            for student in reserved_students:
                UserClassReservation.objects.update_or_create(
                    user=student,
                    class_reserved=class_obj,
                    defaults={"is_cancelled": False},
                )

            active_count = UserClassReservation.objects.filter(class_reserved=class_obj, is_cancelled=False).count()
            if class_index % 6 == 0:
                active_count = class_obj.max_students
                reserved_students = [students[(offset + i) % len(students)] for i in range(class_obj.max_students)]
                for student in reserved_students:
                    UserClassReservation.objects.update_or_create(
                        user=student,
                        class_reserved=class_obj,
                        defaults={"is_cancelled": False},
                    )
                for wait_index in range(2):
                    wait_student = students[(offset + class_obj.max_students + wait_index) % len(students)]
                    ClassWaitlist.objects.update_or_create(
                        user=wait_student,
                        class_reserved=class_obj,
                        defaults={
                            "position": wait_index + 1,
                            "status": "waiting" if wait_index == 0 else "notified",
                            "notes": f"{DEMO_MARKER} Waitlist generated for full class scenario.",
                        },
                    )

            Class.objects.filter(pk=class_obj.pk).update(reservation_count=active_count)
            class_obj.refresh_from_db(fields=["reservation_count"])

            if class_obj.date < timezone.now() and not class_obj.is_cancelled:
                for attendance_index, student in enumerate(reserved_students[: min(6, len(reserved_students))]):
                    attended = attendance_index % 5 != 0
                    attendance, created = ClassAttendance.objects.update_or_create(
                        class_reserved=class_obj,
                        user=student,
                        defaults={
                            "attended": attended,
                            "notes": "Present and active" if attended else "No-show due to school exam",
                            "marked_by": instructors[class_index % len(instructors)],
                        },
                    )
                    if created or attendance.check_in_time is None:
                        class_start = class_obj.date
                        attendance.check_in_time = class_start - timedelta(minutes=10) if attended else None
                        attendance.check_out_time = class_start + class_obj.duration if attended else None
                        attendance.save(update_fields=["check_in_time", "check_out_time"])

    def seed_payments(self, students, quota):
        today = timezone.localdate()
        month_start = today.replace(day=1)

        for index, student in enumerate(students):
            desired_due_dates = set()
            for month_offset in (-1, 0, 1):
                target_month = month_start.month + month_offset
                target_year = month_start.year
                if target_month < 1:
                    target_month += 12
                    target_year -= 1
                elif target_month > 12:
                    target_month -= 12
                    target_year += 1

                due_date = date(target_year, target_month, min(quota.due_day, 28))
                desired_due_dates.add(due_date)
                payment, _ = Payment.objects.update_or_create(
                    user=student,
                    due_date=due_date,
                    defaults={
                        "amount": quota.amount,
                        "description": f"{DEMO_MARKER} Monthly membership {due_date.strftime('%Y-%m')}",
                        "amount_paid": Decimal("0.00"),
                        "is_paid": False,
                        "is_fully_paid": False,
                    },
                )

                PaymentTransaction.objects.filter(payment=payment).delete()

                pattern = (index + month_offset) % 4
                if pattern == 0:
                    payment.amount_paid = payment.amount
                    payment.is_paid = True
                    payment.is_fully_paid = True
                    payment.save(update_fields=["amount_paid", "is_paid", "is_fully_paid"])
                    self.create_payment_transaction(payment, payment.amount, "Transfer", due_date, "Full payment received")
                elif pattern == 1:
                    partial = (payment.amount * Decimal("0.50")).quantize(Decimal("0.01"))
                    payment.amount_paid = partial
                    payment.is_paid = True
                    payment.is_fully_paid = False
                    payment.save(update_fields=["amount_paid", "is_paid", "is_fully_paid"])
                    self.create_payment_transaction(payment, partial, "Cash", due_date, "Partial payment at academy desk")
                elif pattern == 2:
                    payment.amount_paid = Decimal("0.00")
                    payment.is_paid = False
                    payment.is_fully_paid = False
                    payment.save(update_fields=["amount_paid", "is_paid", "is_fully_paid"])
                else:
                    payment.amount_paid = payment.amount
                    payment.is_paid = True
                    payment.is_fully_paid = True
                    payment.save(update_fields=["amount_paid", "is_paid", "is_fully_paid"])
                    split = (payment.amount / 2).quantize(Decimal("0.01"))
                    remainder = payment.amount - split
                    self.create_payment_transaction(payment, split, "Bank transfer", due_date - timedelta(days=2), "First installment")
                    self.create_payment_transaction(payment, remainder, "Bank transfer", due_date, "Balance payment")

            Payment.objects.filter(user=student).exclude(due_date__in=desired_due_dates).delete()

        self.seed_payment_stats()

    def create_payment_transaction(self, payment, amount, payment_method, recorded_date, description):
        transaction = PaymentTransaction.objects.create(
            payment=payment,
            amount=amount,
            description=f"{DEMO_MARKER} {description}",
            payment_method=payment_method,
            external_transaction_id=f"demo-{payment.user_id}-{payment.due_date:%Y%m%d}-{amount}",
        )
        recorded_at = timezone.make_aware(datetime.combine(recorded_date, time(10, 0)))
        PaymentTransaction.objects.filter(pk=transaction.pk).update(transaction_date=recorded_at)
        Payment.objects.filter(pk=payment.pk).update(date_payment=recorded_at)
        return transaction

    def get_demo_stats_dates(self):
        # Single source of truth for the snapshot dates owned by the demo seed.
        # PaymentStats has no text field, so these deterministic dates act as
        # the marker for both creation and cleanup.
        today = timezone.localdate()
        return [today - timedelta(days=30), today]

    def seed_payment_stats(self):
        today = timezone.localdate()
        stats_dates = self.get_demo_stats_dates()
        for stats_date in stats_dates:
            month_payments = Payment.objects.filter(due_date__year=stats_date.year, due_date__month=stats_date.month)
            total_collected = sum((payment.amount_paid for payment in month_payments), Decimal("0.00"))
            pending_amount = sum((payment.amount - payment.amount_paid for payment in month_payments if payment.due_date >= today), Decimal("0.00"))
            overdue_amount = sum((payment.amount - payment.amount_paid for payment in month_payments if payment.due_date < today), Decimal("0.00"))
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

    def seed_events(self, users, disciplines):
        # Drop previously seeded demo events first: event_date shifts with the
        # current date, so update_or_create alone would stack stale rows.
        # EventParticipation rows cascade via FK on Event deletion.
        Event.objects.filter(description__icontains=DEMO_MARKER).delete()
        categories = []
        for name, description in [
            ("Regional Tournament", "Inter-city sparring and forms event"),
            ("Community Exhibition", "Public demonstration at local square"),
            ("Belt Promotion", "Internal evaluation and family attendance"),
        ]:
            category, _ = EventCategory.objects.update_or_create(
                name=name,
                defaults={"description": description, "is_active": True},
            )
            categories.append(category)

        event_specs = [
            ("Copa Central Formas 2026", timezone.localdate() - timedelta(days=35), "Polideportivo de Villeta", categories[0]),
            ("Exhibicion Comunitaria Ypane", timezone.localdate() + timedelta(days=12), "Plaza Mariscal Lopez de Ypane", categories[1]),
            ("Jornada de Ascensos Central", timezone.localdate() + timedelta(days=28), "Academia Teko Katu Ypane", categories[2]),
        ]
        created_events = []
        for index, (name, event_date, location, category) in enumerate(event_specs):
            event, _ = Event.objects.update_or_create(
                name=name,
                event_date=event_date,
                defaults={
                    "description": f"{DEMO_MARKER} Thesis demo event covering Ypane and Villeta academy activity.",
                    "location": location,
                    "organizer": "Federacion Demo Central",
                    "is_verified": True,
                    "created_by": users["admins"][0],
                    "verified_by": users["admins"][0],
                    "verified_at": timezone.now(),
                },
            )
            event.disciplines.set(disciplines)
            event.categories.set([category])
            created_events.append(event)

            participants = users["students"][index * 4 : index * 4 + 6]
            result_cycle = ["1st", "2nd", "3rd", "participation", "exhibition", "participation"]
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
        return created_events

    def seed_exam_sessions(self, users, belts, evaluation_parameters):
        # Drop previously seeded demo sessions first: exam_date shifts with the
        # current date, so update_or_create alone would stack stale rows.
        # ExamResult / scores cascade via FK; M2M links are cleaned automatically.
        ExamSession.objects.filter(belt_level__icontains=DEMO_MARKER).delete()
        belt_targets = [belts["Amarillo"], belts["Verde"], belts["Azul"]]
        for index, belt in enumerate(belt_targets):
            exam_date = timezone.localdate() - timedelta(days=20) if index == 0 else timezone.localdate() + timedelta(days=18 + index * 7)
            exam_session, _ = ExamSession.objects.update_or_create(
                belt_rank=belt,
                exam_date=exam_date,
                defaults={
                    "belt_level": f"{belt.name} {DEMO_MARKER}",
                    "created_by": users["admins"][0],
                },
            )
            exam_session.evaluation_parameters.set(evaluation_parameters)

            participants = users["students"][index * 5 : index * 5 + 5]
            exam_session.participants.set(participants)
            for participant_index, participant in enumerate(participants):
                graded = exam_date <= timezone.localdate()
                passed = (index == 0 or participant_index % 4 != 0) if graded else False
                # Bypass ExamResult.save(): it promotes the participant's
                # belt_rank on a new pass, which would break deterministic demo
                # profiles. Queryset update()/bulk_create() skip save() entirely.
                existing_results = ExamResult.objects.filter(exam_session=exam_session, participant=participant)
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
                            defaults={"score": 70 + ((participant_index + score_index) % 25)},
                        )

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

        posts = [
            {
                "title": "Attendance growth in Ypane beginner groups",
                "author": users["instructors"][0],
                "category": categories["Training"],
                "content": f"Weekly attendance is improving as families commit to fixed schedules in Ypane. {DEMO_MARKER}",
                "is_featured": True,
                "tags": [tags["ypane"], tags["taekwondo"], tags["community"]],
            },
            {
                "title": "Villeta sparring team prepares for regional tournament",
                "author": second_instructor,
                "category": categories["Events"],
                "content": f"Students from Villeta are focusing on distance management and ring discipline. {DEMO_MARKER}",
                "is_featured": True,
                "tags": [tags["villeta"], tags["taekwondo"], tags["belt-exam"]],
            },
            {
                "title": "Parent meeting covers quotas, exams and transport logistics",
                "author": users["admins"][0],
                "category": categories["Community"],
                "content": f"The admin team presented realistic fee tracking and exam planning for the thesis demo. {DEMO_MARKER}",
                "is_featured": False,
                "tags": [tags["community"], tags["ypane"], tags["villeta"]],
            },
        ]

        for post_data in posts:
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

            comment_authors = users["students"][:2]
            for index, author in enumerate(comment_authors, start=1):
                Comment.objects.update_or_create(
                    blog_post=post,
                    user=author,
                    defaults={"content": f"{DEMO_MARKER} Helpful update for families and students, comment {index}."},
                )
            for score, rater in [(5, users["students"][2]), (4, users["students"][3])]:
                Rating.objects.update_or_create(blog_post=post, user=rater, defaults={"score": score})

    def seed_resources(self, users):
        second_instructor = users["instructors"][min(1, len(users["instructors"]) - 1)]
        tag_map = {}
        for name in RESOURCE_TAGS:
            tag, _ = ResourceTag.objects.get_or_create(name=name)
            tag_map[name] = tag

        resources = [
            {
                "title": "Warm-up routine for school-age beginners",
                "type": ResourceType.VIDEO,
                "category": ResourceCategory.TRAINING,
                "level": ResourceLevel.KYU_A,
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "author": users["instructors"][0],
                "tags": [tag_map["warmup"], tag_map["parents"]],
            },
            {
                "title": "Tournament checklist for Villeta competitors",
                "type": ResourceType.LINK,
                "category": ResourceCategory.COMPETITION,
                "level": ResourceLevel.KYU_B,
                "url": "https://example.com/demo/villeta-tournament-checklist",
                "author": second_instructor,
                "tags": [tag_map["competition"], tag_map["sparring"]],
            },
            {
                "title": "Poomsae home practice reference",
                "type": ResourceType.LINK,
                "category": ResourceCategory.TECHNIQUE,
                "level": ResourceLevel.ALL,
                "url": "https://example.com/demo/poomsae-reference",
                "author": users["admins"][0],
                "tags": [tag_map["poomsae"], tag_map["discipline"]],
            },
        ]

        for item in resources:
            resource, _ = Resource.objects.update_or_create(
                title=item["title"],
                defaults={
                    "description": f"{DEMO_MARKER} Safe link-only thesis resource.",
                    "type": item["type"],
                    "category": item["category"],
                    "level": item["level"],
                    "url": item["url"],
                    "author": item["author"],
                    "views_count": 20,
                    "downloads_count": 3,
                    "is_featured": True,
                    "is_premium": False,
                },
            )
            resource.tags.set(item["tags"])

    def seed_gallery(self):
        Gallery.objects.update_or_create(
            title="Thesis Demo Activity Highlights",
            defaults={
                "description": (
                    f"{DEMO_MARKER} Gallery seeded without media files on purpose. "
                    "This project uses file-based gallery items, so the command avoids fragile uploads in local and Render environments."
                )
            },
        )

    def seed_contact_messages(self):
        messages = [
            ("Marta Fernandez", "marta.family@example.com", "+595981660100", "Consulta por horarios de iniciacion en Ypane."),
            ("Julio Acosta", "julio.community@example.com", "+595981660101", "Solicitud de exhibicion para festival estudiantil en Villeta."),
            ("Colegio San Miguel", "direccion@sanmiguel.edu.py", "+59521555010", "Interes en convenio para clases extracurriculares."),
        ]
        for name, email, phone, body in messages:
            ContactMessage.objects.update_or_create(
                email=email,
                defaults={
                    "name": name,
                    "phone": phone,
                    "message": f"{body} {DEMO_MARKER}",
                    "is_read": False,
                },
            )

    def refresh_performance_stats(self, students):
        for student in students:
            stats, _ = PerformanceStatistics.objects.get_or_create(user=student)
            stats.update_statistics()

    def print_summary(self, users, classes, templates, events):
        self.stdout.write(self.style.SUCCESS("Demo seed completed safely."))
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    "DEBUG=False: the demo superuser account was deactivated (is_active=False) by design."
                )
            )
        self.stdout.write(f"Academies: {len(ACADEMY_DATA)}")
        self.stdout.write(f"Users: {len(users['all'])} total ({len(users['admins'])} admin/superadmin, {len(users['instructors'])} instructors, {len(users['students'])} students)")
        self.stdout.write(f"Class templates: {len(templates)}")
        self.stdout.write(f"Classes: {len(classes)}")
        self.stdout.write(f"Events: {len(events)}")
        self.stdout.write("Gallery: seeded as metadata only, without file uploads")
        self.stdout.write(f"Demo emails use *@{DEMO_EMAIL_DOMAIN}")
