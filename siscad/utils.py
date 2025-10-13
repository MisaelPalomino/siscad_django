from .models import Profesor, Alumno, Secretaria, Administrador

# ============ PROFESOR ==============


def CrearProfesor(nombre, email, dni, cantida_reservas=2):
    profesor = Profesor.objects.create(
        nombre=nombre, email=email, dni=dni, cantida_reservas=cantida_reservas
    )
    return profesor


def ObtenerProfesorId(profesor_id):
    try:
        return Profesor.objects.get(id=profesor_id)
    except Profesor.DoesNotExist:
        return None


def EliminarProfesor(profesor_id):
    profesor = ObtenerProfesorId(profesor_id)
    if profesor:
        profesor.delete()
        return True
    return False


# =========== Alumno ==============


def CrearAlumno(nombre, email, dni, cui):
    alumno = Alumno.objects.create(nombre=nombre, email=email, dni=dni, cui=cui)
    return alumno


def ObtenerAlumnoId(alumno_id):
    try:
        return Alumno.objects.get(id=alumno_id)
    except Alumno.DoesNotExist:
        return None


def EliminarAlumno(alumno_id):
    alumno = ObtenerAlumnoId(alumno_id)
    if alumno:
        alumno.delete()
        return True
    return False


# ========== Secretaria =============


def CrearSecretaria(nombre, email, dni):
    secretaria = Secretaria.objects.create(nombre=nombre, email=email, dni=dni)
    return secretaria


def ObtenerSecretariaId(secretaria_id):
    try:
        return Secretaria.objects.get(id=secretaria_id)
    except Secretaria.DoesNotExist:
        return None


def EliminarSecretaria(secretaria_id):
    secretaria = ObtenerSecretariaId(secretaria_id)
    if secretaria:
        secretaria.delete()
        return True
    return False
