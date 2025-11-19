"""
Comando de Django para poblar la base de datos con datos de prueba.
Uso: python manage.py populate_test_data [--users N] [--classes N] [--blog N] [--resources N] [--gallery N]
"""
import random
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from users.models import UserProfile
from classes.models import Class, UserClassReservation, ClassAttendance, ClassTemplate
from payments.models import Payment, QuotaConfig, PaymentTransaction
from blog.models import BlogPost, Category, Tag, Comment, Rating
from resources.models import Resource, ResourceTag, ResourceType, ResourceCategory, ResourceLevel
from gallery.models import Gallery, GalleryItem
from performance.models import (
    Discipline, EvaluationParameter, ExamSession, ExamResult, 
    ExamResultParameterScore, Event, EventCategory, EventParticipation
)

User = get_user_model()

# Datos de prueba
FIRST_NAMES = [
    'Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Pedro', 'Carmen',
    'Miguel', 'Isabel', 'José', 'Patricia', 'Francisco', 'Lucía', 'Antonio',
    'Sofía', 'Manuel', 'Elena', 'Javier', 'Marta', 'Diego', 'Cristina',
    'Alejandro', 'Paula', 'Roberto', 'Andrea', 'Fernando', 'Natalia',
    'Ricardo', 'Monica', 'Sergio', 'Diana', 'Andrés', 'Valeria', 'Raúl',
    'Gabriela', 'Óscar', 'Mariana', 'Eduardo', 'Daniela'
]

LAST_NAMES = [
    'García', 'Rodríguez', 'González', 'Fernández', 'López', 'Martínez',
    'Sánchez', 'Pérez', 'Gómez', 'Martín', 'Jiménez', 'Ruiz', 'Hernández',
    'Díaz', 'Moreno', 'Muñoz', 'Álvarez', 'Romero', 'Alonso', 'Gutiérrez',
    'Navarro', 'Torres', 'Domínguez', 'Vázquez', 'Ramos', 'Gil', 'Ramírez',
    'Serrano', 'Blanco', 'Suárez', 'Molina', 'Morales', 'Ortega', 'Delgado',
    'Castro', 'Ortiz', 'Rubio', 'Marín', 'Sanz', 'Iglesias'
]

DOJOS = [
    'Dojo Central', 'Dojo Norte', 'Dojo Sur', 'Dojo Este', 'Dojo Oeste',
    'Dojo Principal', 'Dojo Secundario', 'Dojo Elite', 'Dojo Tradicional'
]

BELT_RANKS = [
    'Blanco', 'Amarillo', 'Naranja', 'Verde', 'Azul', 'Marrón', 'Negro 1er Dan',
    'Negro 2do Dan', 'Negro 3er Dan', 'Negro 4to Dan'
]

CLASS_NAMES = [
    'Karate Básico', 'Karate Avanzado', 'Kata Tradicional', 'Kumite Competitivo',
    'Defensa Personal', 'Entrenamiento Funcional', 'Flexibilidad y Estiramiento',
    'Técnicas de Combate', 'Preparación para Examen', 'Clase Especial',
    'Seminario de Técnicas', 'Entrenamiento Intensivo', 'Clase Privada',
    'Taller de Kata', 'Entrenamiento de Resistencia'
]

BLOG_CATEGORIES = [
    'Técnicas', 'Historia', 'Filosofía', 'Noticias', 'Eventos', 'Entrenamiento',
    'Nutrición', 'Psicología', 'Competencia', 'Cultura'
]

BLOG_TAGS = [
    'karate', 'kata', 'kumite', 'tradicional', 'moderno', 'competencia',
    'entrenamiento', 'filosofía', 'historia', 'técnica', 'defensa', 'ataque',
    'disciplina', 'respeto', 'honor', 'meditación', 'concentración'
]

RESOURCE_TAGS = [
    'básico', 'avanzado', 'kata', 'kumite', 'defensa', 'ataque', 'técnica',
    'teoría', 'historia', 'filosofía', 'entrenamiento', 'competencia'
]

DISCIPLINES = [
    'Karate Shotokan', 'Karate Kyokushin', 'Karate Goju-Ryu', 'Karate Wado-Ryu',
    'Karate Shito-Ryu', 'Kickboxing', 'Muay Thai', 'Taekwondo'
]

EVENT_CATEGORIES = [
    'Torneo Local', 'Torneo Regional', 'Torneo Nacional', 'Torneo Internacional',
    'Exhibición', 'Seminario', 'Clínica', 'Examen de Grado'
]

EVALUATION_PARAMETERS = [
    'Técnica', 'Velocidad', 'Fuerza', 'Precisión', 'Resistencia',
    'Flexibilidad', 'Concentración', 'Actitud', 'Disciplina', 'Respeto'
]


class Command(BaseCommand):
    help = 'Pobla la base de datos con datos de prueba realistas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Número de usuarios a crear (default: 50)'
        )
        parser.add_argument(
            '--instructors',
            type=int,
            default=5,
            help='Número de instructores a crear (default: 5)'
        )
        parser.add_argument(
            '--classes',
            type=int,
            default=100,
            help='Número de clases a crear (default: 100)'
        )
        parser.add_argument(
            '--blog',
            type=int,
            default=30,
            help='Número de posts de blog a crear (default: 30)'
        )
        parser.add_argument(
            '--resources',
            type=int,
            default=40,
            help='Número de recursos a crear (default: 40)'
        )
        parser.add_argument(
            '--gallery',
            type=int,
            default=10,
            help='Número de galerías a crear (default: 10)'
        )
        parser.add_argument(
            '--events',
            type=int,
            default=15,
            help='Número de eventos a crear (default: 15)'
        )
        parser.add_argument(
            '--exams',
            type=int,
            default=10,
            help='Número de sesiones de examen a crear (default: 10)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Eliminar todos los datos existentes antes de poblar'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Eliminando datos existentes...'))
            self.clear_data()
        
        self.stdout.write(self.style.SUCCESS('Iniciando población de datos de prueba...'))
        
        # Configurar cuota
        quota_config = self.create_quota_config()
        
        # Crear usuarios
        users_data = self.create_users(
            options['users'],
            options['instructors']
        )
        
        # Crear clases
        self.create_classes(
            options['classes'],
            users_data['instructors'],
            users_data['students']
        )
        
        # Crear blog
        self.create_blog_posts(
            options['blog'],
            users_data['instructors'] + users_data['admins']
        )
        
        # Crear recursos
        self.create_resources(
            options['resources'],
            users_data['instructors'] + users_data['admins']
        )
        
        # Crear galerías
        self.create_galleries(options['gallery'])
        
        # Crear eventos y participaciones
        self.create_events_and_participations(
            options['events'],
            users_data['students'],
            users_data['instructors']
        )
        
        # Crear exámenes
        self.create_exams(
            options['exams'],
            users_data['students'],
            users_data['instructors']
        )
        
        self.stdout.write(self.style.SUCCESS('\n¡Datos de prueba creados exitosamente!'))
        self.print_summary(users_data)

    def clear_data(self):
        """Elimina todos los datos de prueba"""
        PaymentTransaction.objects.all().delete()
        Payment.objects.all().delete()
        ClassAttendance.objects.all().delete()
        UserClassReservation.objects.all().delete()
        Class.objects.all().delete()
        Comment.objects.all().delete()
        Rating.objects.all().delete()
        BlogPost.objects.all().delete()
        Resource.objects.all().delete()
        GalleryItem.objects.all().delete()
        Gallery.objects.all().delete()
        EventParticipation.objects.all().delete()
        Event.objects.all().delete()
        ExamResultParameterScore.objects.all().delete()
        ExamResult.objects.all().delete()
        ExamSession.objects.all().delete()
        UserProfile.objects.exclude(role='admin').delete()
        User.objects.exclude(is_superuser=True).delete()

    def create_quota_config(self):
        """Crea la configuración de cuota"""
        quota, created = QuotaConfig.objects.get_or_create(
            is_active=True,
            defaults={
                'amount': Decimal('50.00'),
                'due_day': 10
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Configuración de cuota creada: ${quota.amount}'))
        return quota

    def create_users(self, num_students, num_instructors):
        """Crea usuarios de prueba"""
        admins = []
        instructors = []
        students = []
        
        # Crear admin si no existe
        admin, created = User.objects.get_or_create(
            email='admin@test.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'Principal',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            profile, _ = UserProfile.objects.get_or_create(
                user=admin,
                defaults={
                    'role': 'admin',
                    'belt_rank': 'Negro 5to Dan',
                    'dojo': DOJOS[0]
                }
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Admin creado: {admin.email}'))
        else:
            # Asegurar que el admin tenga perfil
            UserProfile.objects.get_or_create(
                user=admin,
                defaults={
                    'role': 'admin',
                    'belt_rank': 'Negro 5to Dan',
                    'dojo': DOJOS[0]
                }
            )
        admins.append(admin)  # Siempre agregar admin a la lista
        
        # Crear instructores
        instructors_created = 0
        for i in range(num_instructors):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            email = f'instructor{i+1}@test.com'
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name
                }
            )
            if created:
                user.set_password('test123')
                user.save()
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'role': 'instructor',
                        'belt_rank': random.choice(['Negro 1er Dan', 'Negro 2do Dan', 'Negro 3er Dan']),
                        'dojo': random.choice(DOJOS),
                        'bio': f'Instructor con {random.randint(5, 20)} años de experiencia',
                        'age': random.randint(25, 50),
                        'phone_number': f'+34{random.randint(600000000, 699999999)}'
                    }
                )
                instructors_created += 1
            else:
                # Asegurar que el usuario existente tenga perfil de instructor
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'role': 'instructor',
                        'belt_rank': random.choice(['Negro 1er Dan', 'Negro 2do Dan', 'Negro 3er Dan']),
                        'dojo': random.choice(DOJOS)
                    }
                )
                # Actualizar rol si es necesario
                if profile.role != 'instructor':
                    profile.role = 'instructor'
                    profile.save()
            instructors.append(user)  # Siempre agregar a la lista
        
        self.stdout.write(self.style.SUCCESS(f'✓ {len(instructors)} instructores disponibles ({instructors_created} nuevos)'))
        
        # Crear estudiantes
        students_created = 0
        for i in range(num_students):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            email = f'student{i+1}@test.com'
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name
                }
            )
            if created:
                user.set_password('test123')
                user.save()
                enrollment_date = date.today() - timedelta(days=random.randint(30, 1000))
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'role': 'student',
                        'belt_rank': random.choice(BELT_RANKS),
                        'dojo': random.choice(DOJOS),
                        'enrollment_date': enrollment_date,
                        'age': random.randint(8, 60),
                        'phone_number': f'+34{random.randint(600000000, 699999999)}',
                        'address': f'Calle {random.choice(["Mayor", "Principal", "Real", "Nueva"])} {random.randint(1, 100)}',
                        'city': random.choice(['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao'])
                    }
                )
                students_created += 1
            else:
                # Asegurar que el usuario existente tenga perfil de estudiante
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'role': 'student',
                        'belt_rank': random.choice(BELT_RANKS),
                        'dojo': random.choice(DOJOS)
                    }
                )
                # Actualizar rol si es necesario
                if profile.role != 'student':
                    profile.role = 'student'
                    profile.save()
            students.append(user)  # Siempre agregar a la lista
        
        self.stdout.write(self.style.SUCCESS(f'✓ {len(students)} estudiantes disponibles ({students_created} nuevos)'))
        
        return {
            'admins': admins,
            'instructors': instructors,
            'students': students
        }

    def create_classes(self, num_classes, instructors, students):
        """Crea clases de prueba"""
        # Si no hay instructores, usar admin
        if not instructors:
            admin = User.objects.filter(is_superuser=True).first()
            if admin:
                instructors = [admin]
        
        class_types = ['regular', 'intensive', 'private', 'seminar', 'exam']
        difficulty_levels = ['kyu_a', 'kyu_b', 'dan', 'all']
        
        for i in range(num_classes):
            instructor = random.choice(instructors) if instructors else None
            class_date = timezone.now() + timedelta(
                days=random.randint(-30, 60),
                hours=random.randint(9, 20)
            )
            
            class_obj = Class.objects.create(
                name=random.choice(CLASS_NAMES),
                description=f'Descripción de la clase {i+1}. Entrenamiento enfocado en técnicas básicas y avanzadas.',
                instructor=instructor,
                date=class_date,
                max_students=random.randint(10, 30),
                duration=timedelta(hours=random.choice([1, 1.5, 2])),
                class_type=random.choice(class_types),
                difficulty_level=random.choice(difficulty_levels),
                location=random.choice(['Sala Principal', 'Sala Secundaria', 'Dojo Central', 'Gimnasio']),
                equipment_needed=random.choice(['Ninguno', 'Guantes', 'Protecciones', 'Espada de madera', 'Escudo']),
                is_cancelled=random.random() < 0.05  # 5% canceladas
            )
            
            # Crear reservas
            num_reservations = random.randint(0, min(class_obj.max_students, len(students)))
            selected_students = random.sample(students, num_reservations) if students else []
            
            for student in selected_students:
                UserClassReservation.objects.get_or_create(
                    user=student,
                    class_reserved=class_obj
                )
                
                # Crear asistencia (algunas pasadas)
                if class_date < timezone.now():
                    ClassAttendance.objects.get_or_create(
                        class_reserved=class_obj,
                        user=student,
                        defaults={
                            'attended': random.random() > 0.15,  # 85% asistencia
                            'check_in_time': class_date if random.random() > 0.15 else None
                        }
                    )
            
            class_obj.reservation_count = num_reservations
            class_obj.save()
        
        self.stdout.write(self.style.SUCCESS(f'✓ {num_classes} clases creadas'))

    def create_blog_posts(self, num_posts, authors):
        """Crea posts de blog de prueba"""
        # Asegurar que haya al menos un autor disponible
        if not authors:
            # Si no hay autores, usar el admin o crear uno
            admin = User.objects.filter(is_superuser=True).first()
            if admin:
                authors = [admin]
            else:
                self.stdout.write(self.style.WARNING('⚠️  No hay autores disponibles para crear posts de blog'))
                return
        
        # Crear categorías
        categories = []
        for cat_name in BLOG_CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'Categoría sobre {cat_name.lower()}'}
            )
            categories.append(cat)
        
        # Crear tags
        tags = []
        for tag_name in BLOG_TAGS:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)
        
        # Crear posts
        for i in range(num_posts):
            author = random.choice(authors)  # Ya verificamos que authors no está vacío
            post = BlogPost.objects.create(
                title=f'Artículo sobre {random.choice(["Karate", "Técnicas", "Historia", "Entrenamiento"])} - {i+1}',
                content=f'''
                <p>Este es el contenido del artículo número {i+1}.</p>
                <p>En este artículo exploramos diferentes aspectos de las artes marciales,
                incluyendo técnicas, filosofía y práctica.</p>
                <h2>Sección Principal</h2>
                <p>Aquí encontrarás información detallada sobre el tema principal del artículo.</p>
                <h3>Conclusión</h3>
                <p>Esperamos que este artículo haya sido útil para tu práctica de artes marciales.</p>
                ''',
                author=author,
                category=random.choice(categories) if categories else None,
                is_featured=random.random() < 0.2  # 20% destacados
            )
            
            # Asignar tags aleatorios
            num_tags = random.randint(2, 5)
            post.tags.set(random.sample(tags, min(num_tags, len(tags))))
            
            # Crear comentarios
            if authors:
                num_comments = random.randint(0, 10)
                for _ in range(num_comments):
                    Comment.objects.create(
                        blog_post=post,
                        user=random.choice(authors),
                        content=f'Excelente artículo sobre {post.title}. Muy informativo y útil.'
                    )
                
                # Crear ratings
                num_ratings = random.randint(0, 15)
                rated_users = random.sample(authors, min(num_ratings, len(authors)))
                for user in rated_users:
                    Rating.objects.get_or_create(
                        blog_post=post,
                        user=user,
                        defaults={'score': random.randint(3, 5)}
                    )
        
        self.stdout.write(self.style.SUCCESS(f'✓ {num_posts} posts de blog creados'))

    def create_resources(self, num_resources, authors):
        """Crea recursos de prueba"""
        # Asegurar que haya al menos un autor disponible
        if not authors:
            admin = User.objects.filter(is_superuser=True).first()
            if admin:
                authors = [admin]
            else:
                self.stdout.write(self.style.WARNING('⚠️  No hay autores disponibles para crear recursos'))
                return
        
        # Crear tags
        resource_tags = []
        for tag_name in RESOURCE_TAGS:
            tag, _ = ResourceTag.objects.get_or_create(name=tag_name)
            resource_tags.append(tag)
        
        resource_types = [ResourceType.VIDEO, ResourceType.DOCUMENT, ResourceType.LINK, ResourceType.IMAGE]
        resource_categories = [cat[0] for cat in ResourceCategory.choices]
        resource_levels = [level[0] for level in ResourceLevel.choices]
        
        for i in range(num_resources):
            resource_type = random.choice(resource_types)
            url = None
            if resource_type == ResourceType.LINK:
                url = f'https://example.com/resource-{i+1}'
            elif resource_type == ResourceType.VIDEO:
                url = f'https://youtube.com/watch?v=video{i+1}'
            
            resource = Resource.objects.create(
                title=f'Recurso {i+1}: {random.choice(["Técnica", "Teoría", "Historia", "Entrenamiento"])}',
                description=f'Descripción detallada del recurso número {i+1}. Este recurso contiene información valiosa sobre artes marciales.',
                type=resource_type,
                category=random.choice(resource_categories),
                level=random.choice(resource_levels),
                url=url,
                author=random.choice(authors),  # Ya verificamos que authors no está vacío
                views_count=random.randint(0, 1000),
                downloads_count=random.randint(0, 500),
                is_featured=random.random() < 0.15,  # 15% destacados
                is_premium=random.random() < 0.2  # 20% premium
            )
            
            # Asignar tags
            num_tags = random.randint(1, 4)
            resource.tags.set(random.sample(resource_tags, min(num_tags, len(resource_tags))))
        
        self.stdout.write(self.style.SUCCESS(f'✓ {num_resources} recursos creados'))

    def create_galleries(self, num_galleries):
        """Crea galerías de prueba"""
        for i in range(num_galleries):
            gallery = Gallery.objects.create(
                title=f'Galería {i+1}: {random.choice(["Evento", "Clase", "Examen", "Torneo"])}',
                description=f'Descripción de la galería número {i+1}. Contiene imágenes y videos del evento.'
            )
            
            # Crear items de galería
            num_items = random.randint(5, 20)
            for j in range(num_items):
                media_type = random.choice(['image', 'video'])
                GalleryItem.objects.create(
                    gallery=gallery,
                    media_type=media_type,
                    description=f'Elemento {j+1} de la galería {i+1}'
                )
        
        self.stdout.write(self.style.SUCCESS(f'✓ {num_galleries} galerías creadas'))

    def create_events_and_participations(self, num_events, students, instructors):
        """Crea eventos y participaciones"""
        # Asegurar que haya al menos un organizador
        if not instructors:
            admin = User.objects.filter(is_superuser=True).first()
            if admin:
                instructors = [admin]
            else:
                self.stdout.write(self.style.WARNING('⚠️  No hay instructores disponibles para crear eventos'))
                return
        
        # Crear disciplinas
        disciplines = []
        for disc_name in DISCIPLINES:
            disc, _ = Discipline.objects.get_or_create(name=disc_name)
            disciplines.append(disc)
        
        # Crear categorías de eventos
        event_categories = []
        for cat_name in EVENT_CATEGORIES:
            cat, _ = EventCategory.objects.get_or_create(name=cat_name)
            event_categories.append(cat)
        
        result_choices = ['1st', '2nd', '3rd', '4th', '5th', 'participation', 'exhibition']
        
        for i in range(num_events):
            event_date = date.today() + timedelta(days=random.randint(-365, 365))
            organizer = random.choice(instructors)  # Ya verificamos que instructors no está vacío
            
            event = Event.objects.create(
                name=f'{random.choice(["Torneo", "Seminario", "Exhibición", "Clínica"])} {i+1}',
                description=f'Descripción del evento número {i+1}. Un evento importante en el calendario de artes marciales.',
                event_date=event_date,
                location=random.choice(['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao']),
                organizer=f'Organizador {i+1}',
                created_by=organizer,
                is_verified=random.random() > 0.3  # 70% verificados
            )
            
            # Asignar disciplinas
            num_disciplines = random.randint(1, 3)
            event.disciplines.set(random.sample(disciplines, min(num_disciplines, len(disciplines))))
            
            # Asignar categorías
            num_categories = random.randint(1, 2)
            event.categories.set(random.sample(event_categories, min(num_categories, len(event_categories))))
            
            # Crear participaciones
            if students:
                num_participations = random.randint(5, 30)
                selected_students = random.sample(students, min(num_participations, len(students)))
                
                for student in selected_students:
                    category = random.choice(event_categories)
                    EventParticipation.objects.get_or_create(
                        event=event,
                        user=student,
                        event_category=category,
                        defaults={
                            'result': random.choice(result_choices),
                            'is_verified': random.random() > 0.2  # 80% verificados
                        }
                    )
        
        self.stdout.write(self.style.SUCCESS(f'✓ {num_events} eventos creados'))

    def create_exams(self, num_exams, students, instructors):
        """Crea sesiones de examen"""
        # Asegurar que haya al menos un instructor
        if not instructors:
            admin = User.objects.filter(is_superuser=True).first()
            if admin:
                instructors = [admin]
            else:
                self.stdout.write(self.style.WARNING('⚠️  No hay instructores disponibles para crear exámenes'))
                return
        
        # Crear parámetros de evaluación
        eval_params = []
        for param_name in EVALUATION_PARAMETERS:
            param, _ = EvaluationParameter.objects.get_or_create(
                name=param_name,
                defaults={'description': f'Parámetro de evaluación: {param_name}'}
            )
            eval_params.append(param)
        
        belt_levels = ['Blanco', 'Amarillo', 'Naranja', 'Verde', 'Azul', 'Marrón', 'Negro 1er Dan']
        
        for i in range(num_exams):
            exam_date = date.today() + timedelta(days=random.randint(-180, 180))
            created_by = random.choice(instructors)  # Ya verificamos que instructors no está vacío
            
            exam_session = ExamSession.objects.create(
                belt_level=random.choice(belt_levels),
                exam_date=exam_date,
                created_by=created_by
            )
            
            # Asignar parámetros
            num_params = random.randint(5, len(eval_params))
            exam_session.evaluation_parameters.set(random.sample(eval_params, num_params))
            
            # Crear participantes y resultados
            if students:
                num_participants = random.randint(3, 15)
                selected_students = random.sample(students, min(num_participants, len(students)))
                exam_session.participants.set(selected_students)
                
                # Crear resultados con calificaciones
                for student in selected_students:
                    exam_result, _ = ExamResult.objects.get_or_create(
                        exam_session=exam_session,
                        participant=student,
                        defaults={'graded': random.random() > 0.3}  # 70% calificados
                    )
                    
                    # Crear puntuaciones de parámetros
                    if exam_result.graded:
                        for param in exam_session.evaluation_parameters.all():
                            ExamResultParameterScore.objects.get_or_create(
                                exam_result=exam_result,
                                parameter=param,
                                defaults={'score': random.randint(6, 10)}
                            )
        
        self.stdout.write(self.style.SUCCESS(f'✓ {num_exams} sesiones de examen creadas'))

    def print_summary(self, users_data):
        """Imprime un resumen de los datos creados"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('RESUMEN DE DATOS CREADOS'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'Usuarios Admin: {len(users_data["admins"])}')
        self.stdout.write(f'Instructores: {len(users_data["instructors"])}')
        self.stdout.write(f'Estudiantes: {len(users_data["students"])}')
        self.stdout.write(f'Clases: {Class.objects.count()}')
        self.stdout.write(f'Reservas: {UserClassReservation.objects.count()}')
        self.stdout.write(f'Asistencias: {ClassAttendance.objects.count()}')
        self.stdout.write(f'Posts de Blog: {BlogPost.objects.count()}')
        self.stdout.write(f'Recursos: {Resource.objects.count()}')
        self.stdout.write(f'Galerías: {Gallery.objects.count()}')
        self.stdout.write(f'Eventos: {Event.objects.count()}')
        self.stdout.write(f'Sesiones de Examen: {ExamSession.objects.count()}')
        self.stdout.write(f'Pagos: {Payment.objects.count()}')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('\nCredenciales de prueba:'))
        self.stdout.write('  Admin: admin@test.com / admin123')
        self.stdout.write('  Instructor: instructor1@test.com / test123')
        self.stdout.write('  Estudiante: student1@test.com / test123')

