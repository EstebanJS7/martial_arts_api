"""
Script alternativo para poblar datos de prueba usando la API REST.
Este script es útil si prefieres usar llamadas HTTP en lugar del comando de Django.

Uso:
    python populate_via_api.py

Requisitos:
    pip install requests

Nota: Este script es más lento que el comando de Django porque hace llamadas HTTP.
Para mejor rendimiento, usa: python manage.py populate_test_data
"""
import requests
import json
import random
from datetime import datetime, timedelta, date
from decimal import Decimal

# Configuración
BASE_URL = "http://localhost:8000/api"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

# Datos de prueba
FIRST_NAMES = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Pedro', 'Carmen']
LAST_NAMES = ['García', 'Rodríguez', 'González', 'Fernández', 'López', 'Martínez']
DOJOS = ['Dojo Central', 'Dojo Norte', 'Dojo Sur', 'Dojo Este']
BELT_RANKS = ['Blanco', 'Amarillo', 'Naranja', 'Verde', 'Azul', 'Marrón', 'Negro 1er Dan']


class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
    
    def login(self, email, password):
        """Inicia sesión y obtiene el token"""
        response = self.session.post(
            f"{self.base_url}/users/login/",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access')
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            print(f"✓ Login exitoso: {email}")
            return True
        else:
            print(f"✗ Error en login: {response.status_code} - {response.text}")
            return False
    
    def register_user(self, email, password, first_name, last_name, role='student'):
        """Registra un nuevo usuario"""
        response = self.session.post(
            f"{self.base_url}/users/register/",
            json={
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name
            }
        )
        if response.status_code in [200, 201]:
            user_id = response.json().get('user', {}).get('id')
            # Actualizar rol si es necesario
            if role != 'student' and user_id:
                self.update_user_role(user_id, role)
            return user_id
        return None
    
    def update_user_role(self, user_id, role):
        """Actualiza el rol de un usuario (requiere admin)"""
        response = self.session.put(
            f"{self.base_url}/users/admin/update-role/{user_id}/",
            json={"role": role}
        )
        return response.status_code == 200
    
    def create_class(self, class_data):
        """Crea una clase"""
        response = self.session.post(
            f"{self.base_url}/classes/",
            json=class_data
        )
        return response.json() if response.status_code in [200, 201] else None
    
    def create_blog_post(self, post_data):
        """Crea un post de blog"""
        response = self.session.post(
            f"{self.base_url}/blog/posts/",
            json=post_data
        )
        return response.json() if response.status_code in [200, 201] else None
    
    def create_resource(self, resource_data):
        """Crea un recurso"""
        response = self.session.post(
            f"{self.base_url}/resources/",
            json=resource_data
        )
        return response.json() if response.status_code in [200, 201] else None


def populate_users(client, num_students=20, num_instructors=3):
    """Crea usuarios de prueba"""
    print("\n📝 Creando usuarios...")
    
    # Crear instructores
    instructors = []
    for i in range(num_instructors):
        email = f"instructor{i+1}@test.com"
        user_id = client.register_user(
            email=email,
            password="test123",
            first_name=random.choice(FIRST_NAMES),
            last_name=random.choice(LAST_NAMES),
            role="instructor"
        )
        if user_id:
            instructors.append(user_id)
    
    print(f"✓ {len(instructors)} instructores creados")
    
    # Crear estudiantes
    students = []
    for i in range(num_students):
        email = f"student{i+1}@test.com"
        user_id = client.register_user(
            email=email,
            password="test123",
            first_name=random.choice(FIRST_NAMES),
            last_name=random.choice(LAST_NAMES),
            role="student"
        )
        if user_id:
            students.append(user_id)
    
    print(f"✓ {len(students)} estudiantes creados")
    
    return instructors, students


def populate_classes(client, instructors, students, num_classes=30):
    """Crea clases de prueba"""
    print(f"\n📚 Creando {num_classes} clases...")
    
    created = 0
    for i in range(num_classes):
        class_date = (datetime.now() + timedelta(days=random.randint(-30, 60))).isoformat()
        instructor_id = random.choice(instructors) if instructors else None
        
        class_data = {
            "name": f"Clase {i+1}",
            "description": f"Descripción de la clase {i+1}",
            "instructor": instructor_id,
            "date": class_date,
            "max_students": random.randint(10, 30),
            "class_type": random.choice(['regular', 'intensive', 'private']),
            "difficulty_level": random.choice(['kyu_a', 'kyu_b', 'dan', 'all']),
            "location": random.choice(['Sala Principal', 'Dojo Central'])
        }
        
        if client.create_class(class_data):
            created += 1
    
    print(f"✓ {created} clases creadas")


def populate_blog(client, authors, num_posts=10):
    """Crea posts de blog"""
    print(f"\n📰 Creando {num_posts} posts de blog...")
    
    created = 0
    for i in range(num_posts):
        post_data = {
            "title": f"Artículo {i+1}",
            "content": f"Contenido del artículo {i+1}",
            "author": random.choice(authors) if authors else None,
            "is_featured": random.random() < 0.2
        }
        
        if client.create_blog_post(post_data):
            created += 1
    
    print(f"✓ {created} posts creados")


def populate_resources(client, authors, num_resources=15):
    """Crea recursos"""
    print(f"\n📦 Creando {num_resources} recursos...")
    
    created = 0
    for i in range(num_resources):
        resource_data = {
            "title": f"Recurso {i+1}",
            "description": f"Descripción del recurso {i+1}",
            "type": random.choice(['VIDEO', 'DOCUMENT', 'LINK']),
            "category": random.choice(['TECHNIQUE', 'THEORY', 'HISTORY']),
            "level": random.choice(['KYU_A', 'KYU_B', 'DAN', 'ALL']),
            "url": f"https://example.com/resource-{i+1}",
            "author": random.choice(authors) if authors else None
        }
        
        if client.create_resource(resource_data):
            created += 1
    
    print(f"✓ {created} recursos creados")


def main():
    """Función principal"""
    print("="*60)
    print("Script de Población de Datos vía API REST")
    print("="*60)
    print("\n⚠️  Nota: Este script es más lento que el comando de Django.")
    print("   Para mejor rendimiento, usa: python manage.py populate_test_data\n")
    
    client = APIClient(BASE_URL)
    
    # Login como admin
    if not client.login(ADMIN_EMAIL, ADMIN_PASSWORD):
        print("\n✗ No se pudo iniciar sesión. Asegúrate de que:")
        print("  1. El servidor esté corriendo en http://localhost:8000")
        print("  2. Exista un usuario admin@test.com con contraseña admin123")
        print("  3. O modifica ADMIN_EMAIL y ADMIN_PASSWORD en el script")
        return
    
    # Crear datos
    instructors, students = populate_users(client, num_students=20, num_instructors=3)
    all_users = instructors + students
    
    populate_classes(client, instructors, students, num_classes=30)
    populate_blog(client, all_users, num_posts=10)
    populate_resources(client, all_users, num_resources=15)
    
    print("\n" + "="*60)
    print("✓ Población de datos completada")
    print("="*60)
    print("\nCredenciales de prueba:")
    print("  Instructor: instructor1@test.com / test123")
    print("  Estudiante: student1@test.com / test123")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso cancelado por el usuario")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

