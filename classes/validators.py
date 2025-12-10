"""
Servicio de validaciones avanzadas para clases.
"""
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from typing import List, Dict, Optional, Any
from .models import Class, UserClassReservation
from rest_framework.exceptions import ValidationError


class ClassValidator:
    """
    Servicio para validar clases antes de crearlas o actualizarlas.
    """
    
    @staticmethod
    def validate_instructor_availability(
        instructor_id: int,
        class_date: timezone.datetime,
        duration: timedelta,
        exclude_class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verifica si el instructor está disponible en el horario especificado.
        
        Args:
            instructor_id: ID del instructor
            class_date: Fecha y hora de inicio de la clase
            duration: Duración de la clase
            exclude_class_id: ID de clase a excluir (para actualizaciones)
            
        Returns:
            dict: Resultado de la validación con 'valid' y 'message'
        """
        if not instructor_id:
            return {
                'valid': False,
                'message': 'El instructor es requerido'
            }
        
        class_end = class_date + duration
        
        # Buscar clases del instructor que se solapen con el horario
        # Incluir un margen de tiempo antes y después para evitar clases muy cercanas
        margin = timedelta(minutes=15)
        overlapping_classes = Class.objects.filter(
            instructor_id=instructor_id,
            is_cancelled=False,
            date__lt=class_end + margin,
        ).exclude(
            Q(date__gte=class_end + margin) | Q(date__lte=class_date - margin)
        )
        
        # Excluir la clase actual si se está actualizando
        if exclude_class_id:
            overlapping_classes = overlapping_classes.exclude(id=exclude_class_id)
        
        # Verificar solapamiento real
        conflicts = []
        for existing_class in overlapping_classes:
            existing_end = existing_class.date + existing_class.duration
            # Verificar si hay solapamiento (con margen)
            if not (class_end + margin <= existing_class.date or class_date - margin >= existing_end):
                conflicts.append({
                    'id': existing_class.id,
                    'name': existing_class.name,
                    'date': existing_class.date,
                    'end': existing_end,
                })
        
        if conflicts:
            conflict_info = ', '.join([f"{c['name']} ({c['date'].strftime('%Y-%m-%d %H:%M')})" for c in conflicts])
            return {
                'valid': False,
                'message': f'El instructor tiene conflictos de horario con: {conflict_info}',
                'conflicts': conflicts
            }
        
        return {
            'valid': True,
            'message': 'Instructor disponible'
        }
    
    @staticmethod
    def validate_location_capacity(
        location: str,
        class_date: timezone.datetime,
        duration: timedelta,
        max_students: int,
        exclude_class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Valida la capacidad de la ubicación comparando con otras clases en el mismo lugar y horario.
        
        Args:
            location: Nombre de la ubicación
            class_date: Fecha y hora de inicio de la clase
            duration: Duración de la clase
            max_students: Máximo de estudiantes para esta clase
            exclude_class_id: ID de clase a excluir (para actualizaciones)
            
        Returns:
            dict: Resultado de la validación
        """
        if not location:
            return {
                'valid': True,
                'message': 'No se especificó ubicación'
            }
        
        class_end = class_date + duration
        
        # Buscar clases en la misma ubicación que se solapen
        # Incluir un margen de tiempo para limpieza/preparación
        margin = timedelta(minutes=15)
        overlapping_classes = Class.objects.filter(
            location=location,
            is_cancelled=False,
            date__lt=class_end + margin,
        ).exclude(
            Q(date__gte=class_end + margin) | Q(date__lte=class_date - margin)
        )
        
        if exclude_class_id:
            overlapping_classes = overlapping_classes.exclude(id=exclude_class_id)
        
        # Verificar solapamiento real y capacidad total
        total_students = max_students
        conflicts = []
        
        for existing_class in overlapping_classes:
            existing_end = existing_class.date + existing_class.duration
            # Verificar si hay solapamiento (con margen)
            if not (class_end + margin <= existing_class.date or class_date - margin >= existing_end):
                total_students += existing_class.max_students
                conflicts.append({
                    'id': existing_class.id,
                    'name': existing_class.name,
                    'max_students': existing_class.max_students,
                    'date': existing_class.date,
                })
        
        # Definir capacidad máxima por ubicación (puede ser configurable)
        # Por defecto, asumimos que cada ubicación puede manejar múltiples clases
        # pero podemos agregar límites si es necesario
        MAX_LOCATION_CAPACITY = 100  # Puede ser configurable por ubicación
        
        if total_students > MAX_LOCATION_CAPACITY:
            conflict_info = ', '.join([f"{c['name']} ({c['max_students']} estudiantes)" for c in conflicts])
            return {
                'valid': False,
                'message': f'La ubicación "{location}" excedería su capacidad máxima ({total_students} > {MAX_LOCATION_CAPACITY}) con las clases: {conflict_info}',
                'total_students': total_students,
                'max_capacity': MAX_LOCATION_CAPACITY,
                'conflicts': conflicts
            }
        
        if conflicts:
            return {
                'valid': True,
                'message': f'Ubicación disponible (total: {total_students} estudiantes en horario solapado)',
                'warning': True,
                'total_students': total_students,
                'conflicts': conflicts
            }
        
        return {
            'valid': True,
            'message': 'Ubicación disponible'
        }
    
    @staticmethod
    def validate_schedule_conflicts(
        class_date: timezone.datetime,
        duration: timedelta,
        exclude_class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verifica conflictos de horarios generales (múltiples validaciones).
        
        Args:
            class_date: Fecha y hora de inicio de la clase
            duration: Duración de la clase
            exclude_class_id: ID de clase a excluir
            
        Returns:
            dict: Resultado de la validación
        """
        class_end = class_date + duration
        now = timezone.now()
        
        # Verificar que la clase sea futura (o muy reciente para actualizaciones)
        if class_date < now - timedelta(hours=1):
            return {
                'valid': False,
                'message': 'No se pueden crear clases en el pasado'
            }
        
        # Verificar que la duración sea razonable (máximo 8 horas)
        if duration > timedelta(hours=8):
            return {
                'valid': False,
                'message': 'La duración de la clase no puede exceder 8 horas'
            }
        
        # Verificar que la duración sea mínima (al menos 15 minutos)
        if duration < timedelta(minutes=15):
            return {
                'valid': False,
                'message': 'La duración de la clase debe ser al menos 15 minutos'
            }
        
        return {
            'valid': True,
            'message': 'Horario válido'
        }
    
    @staticmethod
    def validate_student_prerequisites(
        user_id: int,
        class_difficulty: str,
        class_type: str
    ) -> Dict[str, Any]:
        """
        Valida si un estudiante cumple con los prerequisitos para una clase.
        
        Nota: Esta validación requiere información adicional del perfil del estudiante.
        Por ahora, validamos básicamente el nivel de dificultad.
        
        Args:
            user_id: ID del estudiante
            class_difficulty: Nivel de dificultad de la clase
            class_type: Tipo de clase
            
        Returns:
            dict: Resultado de la validación
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {
                'valid': False,
                'message': 'Usuario no encontrado'
            }
        
        # Si la clase es para todos los niveles, no hay restricciones
        if class_difficulty == 'all':
            return {
                'valid': True,
                'message': 'Clase disponible para todos los niveles'
            }
        
        # Aquí se pueden agregar validaciones más complejas basadas en:
        # - Nivel del estudiante (kyu_a, kyu_b, dan)
        # - Clases completadas anteriormente
        # - Certificaciones o logros
        # - Tipo de clase (examen requiere ciertos prerequisitos)
        
        # Por ahora, solo validamos que el usuario esté activo
        if not user.is_active:
            return {
                'valid': False,
                'message': 'El usuario no está activo'
            }
        
        return {
            'valid': True,
            'message': 'Estudiante cumple con los prerequisitos'
        }
    
    @staticmethod
    def validate_equipment_availability(
        equipment_needed: str,
        class_date: timezone.datetime,
        duration: timedelta,
        exclude_class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verifica si el equipamiento necesario está disponible.
        
        Nota: Esta validación requiere un sistema de gestión de equipamiento.
        Por ahora, solo validamos que no haya demasiadas clases que requieran
        el mismo equipamiento en el mismo horario.
        
        Args:
            equipment_needed: Lista de equipamiento necesario (texto)
            class_date: Fecha y hora de inicio de la clase
            duration: Duración de la clase
            exclude_class_id: ID de clase a excluir
            
        Returns:
            dict: Resultado de la validación
        """
        if not equipment_needed or not equipment_needed.strip():
            return {
                'valid': True,
                'message': 'No se requiere equipamiento especial'
            }
        
        class_end = class_date + duration
        
        # Buscar clases que requieran equipamiento similar en el mismo horario
        # Por ahora, solo verificamos si hay muchas clases con equipamiento en el mismo horario
        margin = timedelta(minutes=15)
        overlapping_classes = Class.objects.filter(
            equipment_needed__isnull=False,
            equipment_needed__gt='',
            is_cancelled=False,
            date__lt=class_end + margin,
        ).exclude(
            Q(date__gte=class_end + margin) | Q(date__lte=class_date - margin)
        )
        
        if exclude_class_id:
            overlapping_classes = overlapping_classes.exclude(id=exclude_class_id)
        
        # Verificar solapamiento real
        conflicts = []
        equipment_list = [eq.strip().lower() for eq in equipment_needed.split(',') if eq.strip()]
        
        for existing_class in overlapping_classes:
            existing_end = existing_class.date + existing_class.duration
            # Verificar si hay solapamiento (con margen)
            if not (class_end + margin <= existing_class.date or class_date - margin >= existing_end):
                existing_equipment = [eq.strip().lower() for eq in existing_class.equipment_needed.split(',') if eq.strip()]
                # Verificar si hay equipamiento común
                common_equipment = set(equipment_list) & set(existing_equipment)
                if common_equipment:
                    conflicts.append({
                        'id': existing_class.id,
                        'name': existing_class.name,
                        'equipment': list(common_equipment),
                        'date': existing_class.date,
                    })
        
        if conflicts:
            # Si hay más de 3 clases con el mismo equipamiento, advertir
            if len(conflicts) >= 3:
                conflict_info = ', '.join([f"{c['name']} (requiere: {', '.join(c['equipment'])})" for c in conflicts[:3]])
                return {
                    'valid': False,
                    'message': f'Muchas clases requieren el mismo equipamiento en este horario: {conflict_info}',
                    'conflicts': conflicts
                }
            else:
                conflict_info = ', '.join([f"{c['name']}" for c in conflicts])
                return {
                    'valid': True,
                    'message': f'Equipamiento disponible (advertencia: otras clases también lo requieren: {conflict_info})',
                    'warning': True,
                    'conflicts': conflicts
                }
        
        return {
            'valid': True,
            'message': 'Equipamiento disponible'
        }
    
    @classmethod
    def validate_class(cls, class_data: Dict, exclude_class_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Valida una clase completa con todas las validaciones avanzadas.
        
        Args:
            class_data: Diccionario con los datos de la clase
            exclude_class_id: ID de clase a excluir (para actualizaciones)
            
        Returns:
            dict: Resultado de todas las validaciones
        """
        errors = []
        warnings = []
        
        instructor_id = class_data.get('instructor')
        class_date = class_data.get('date')
        duration = class_data.get('duration', timedelta(hours=1))
        location = class_data.get('location', '')
        max_students = class_data.get('max_students', 0)
        equipment_needed = class_data.get('equipment_needed', '')
        
        # Validar disponibilidad del instructor
        if instructor_id and class_date:
            result = cls.validate_instructor_availability(
                instructor_id, class_date, duration, exclude_class_id
            )
            if not result['valid']:
                errors.append(result['message'])
            elif result.get('warning'):
                warnings.append(result['message'])
        
        # Validar capacidad de ubicación
        if location and class_date:
            result = cls.validate_location_capacity(
                location, class_date, duration, max_students, exclude_class_id
            )
            if not result['valid']:
                errors.append(result['message'])
            elif result.get('warning'):
                warnings.append(result['message'])
        
        # Validar conflictos de horarios
        if class_date:
            result = cls.validate_schedule_conflicts(class_date, duration, exclude_class_id)
            if not result['valid']:
                errors.append(result['message'])
        
        # Validar equipamiento
        if equipment_needed and class_date:
            result = cls.validate_equipment_availability(
                equipment_needed, class_date, duration, exclude_class_id
            )
            if not result['valid']:
                errors.append(result['message'])
            elif result.get('warning'):
                warnings.append(result['message'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }

