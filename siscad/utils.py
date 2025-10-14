from .models import (
    Profesor,
    Alumno,
    Secretaria,
    Administrador,
    Curso,
    GrupoTeoria,
    GrupoPractica,
    GrupoLaboratorio,
)

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


# ============ Administrador ===================


def CrearAdministrador(nombre, email, dni):
    administrador = Administrador.objects.create(nombre=nombre, email=email, dni=dni)
    return administrador


def ObtenerAdministradorId(administrador_id):
    try:
        return Administrador.objects.get(id=administrador_id)
    except Administrador.DoesNotExist:
        return None


def EliminarAdministrador(administrador_id):
    administrador = ObtenerAdministradorId(administrador_id)
    if administrador:
        administrador.delete()
        return True
    return False


# =================ACADEMICO=======================

# =============  CURSO =======================


def CrearCurso(
    nombre,
    peso_continua_1,
    peso_continua_2,
    peso_continua_3,
    peso_parcial_1,
    peso_parcial_2,
    peso_parcial_3,
    semestre,
):
    curso = Curso.objects.create(
        nombre=nombre,
        peso_continua_1=peso_continua_1,
        peso_continua_2=peso_continua_2,
        peso_continua_3=peso_continua_3,
        peso_parcial_1=peso_parcial_1,
        peso_parcial_2=peso_parcial_2,
        peso_parcial_3=peso_parcial_3,
        semestre=semestre,
    )
    return curso


def ObtenerCursoId(curso_id):
    try:
        return Curso.objects.get(id=curso_id)
    except Curso.DoesNotExist:
        return None


def EliminarCurso(curso_id):
    curso = ObtenerCursoId(curso_id)
    if curso:
        curso.delete()
        return True
    return False


# ================== GRUPO TEORIA ====================


def CrearGrupoTeoria(curso_id, profesor_id=None, turno="A"):
    if curso_id:
        curso = ObtenerCursoId(curso_id)
    profesor = None
    if profesor_id:
        profesor = ObtenerProfesorId(profesor_id)
    if not curso:
        return None
    grupo = GrupoTeoria.objects.create(curso=curso, profesor=profesor, turno=turno)
    return grupo


def ObtenerGrupoTeoriaId(grupo_teoria_id):
    try:
        return GrupoTeoria.objects.get(id=grupo_teoria_id)
    except GrupoTeoria.DoesNotExist:
        return None


def EliminarGrupoTeoria(grupo_teoria_id):
    grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)
    if grupo_teoria:
        grupo_teoria.delete()
        return True
    return False


# ================== Grupo Practica =================


def CrearGrupoPractica(grupo_teoria_id, profesor_id=None, turno="A"):
    grupo_teoria = None
    profesor = None
    if grupo_teoria_id:
        grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)
    if profesor_id:
        profesor = ObtenerProfesorId(profesor_id)
    if not grupo_teoria:
        return None
    grupo = GrupoPractica.objects.create(
        grupo_teoria=grupo_teoria, profesor=profesor, turno=turno
    )
    return grupo


def ObtenerGrupoPracticaId(grupo_practica_id):
    try:
        return GrupoPractica.objects.get(id=grupo_practica_id)
    except GrupoPractica.DoesNotExist:
        return None


def EliminarGrupoPractica(grupo_practica_id):
    grupo_practica = ObtenerGrupoPracticaId(grupo_practica_id)
    if grupo_practica:
        grupo_practica.delete()
        return True
    return False

#================== Grupo Laboratorio ===============

def CrearGrupoLaboratorio(grupo_teoria_id,profesor_id,grupo="A",cupos=20):
    grupo_teoria = None
    profesor = None
    if grupo_teoria_id:
        grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)
    if profesor_id:
        profesor = ObtenerProfesorId(profesor_id)
    if not grupo_teoria:
        return None
    grupo_lab = GrupoLaboratorio.objects.create(
        grupo_teoria=grupo_teoria,profesor=profesor,cupos = cupos, grupo=grupo
    )
    return grupo_lab

def 