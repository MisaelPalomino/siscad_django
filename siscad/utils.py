from .models import (
    Profesor,
    Alumno,
    Secretaria,
    Administrador,
    Curso,
    GrupoTeoria,
    GrupoPractica,
    GrupoLaboratorio,
    Aula,
    Reserva,
    Silabo,
    Examen,
    MatriculaCurso,
    Nota,
    MatriculaLaboratorio,
    Tema,
    Hora,
    AsistenciaProfesor,
    AsistenciaAlumno,
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


# ================== Grupo Laboratorio ===============


def CrearGrupoLaboratorio(grupo_teoria_id, profesor_id, grupo="A", cupos=20):
    grupo_teoria = None
    profesor = None
    if grupo_teoria_id:
        grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)
    if profesor_id:
        profesor = ObtenerProfesorId(profesor_id)
    if not grupo_teoria:
        return None
    grupo_lab = GrupoLaboratorio.objects.create(
        grupo_teoria=grupo_teoria, profesor=profesor, cupos=cupos, grupo=grupo
    )
    return grupo_lab


def ObtenerGrupoLaboratorioId(grupo_laboratorio_id):
    try:
        return GrupoLaboratorio.objects.get(id=grupo_laboratorio_id)
    except GrupoLaboratorio.DoesNotExist:
        return None


def EliminarGrupoLaboratorio(grupo_laboratorio_id):
    grupo_laboratorio = ObtenerGrupoLaboratorioId(grupo_laboratorio_id)
    if grupo_laboratorio:
        grupo_laboratorio.delete()
        return True
    return False


# ================= Aula =====================


def CrearAula(nombre):
    aula = Aula.objects.create(nombre=nombre)
    return aula


def ObtenerAulaId(aula_id):
    try:
        return Aula.objects.get(id=aula_id)
    except Aula.DoesNotExist:
        return None


def EliminarAula(aula_id):
    aula = ObtenerAulaId(aula_id)
    if aula:
        aula.delete()
        return True
    return False


# ================= Reserva ===================


def CrearReserva(curso_id, profesor_id):
    curso = None
    profesor = None
    if curso_id:
        curso = ObtenerCursoId(curso_id)
    if profesor_id:
        profesor = ObtenerProfesorId(profesor_id)

    if not profesor:
        return None
    if not curso:
        return None

    reserva = Reserva.objects.create(curso=curso, profesor=profesor)
    return reserva


def ObtenerReservaId(reserva_id):
    try:
        return Reserva.objects.get(id=reserva_id)
    except Reserva.DoesNotExist:
        return None


def EliminarReserva(reserva_id):
    reserva = ObtenerReservaId(reserva_id)
    if reserva:
        reserva.delete()
        return True
    return False


# ================ Silabo ==================0


def CrearSilabo(grupo_teoria_id, nombre, archivo):
    grupo_teoria = None
    if grupo_teoria_id:
        grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)

    if not grupo_teoria:
        return None

    silabo = Silabo.objects.create(
        grupo_teoria=grupo_teoria, nombre=nombre, archivo=archivo
    )
    return silabo


def ObtenerSilaboId(silabo_id):
    try:
        return Silabo.objects.get(id=silabo_id)
    except Silabo.DoesNotExist:
        return None


def EliminarSilabo(silabo_id):
    silabo = ObtenerSilaboId(silabo_id)
    if silabo:
        silabo.delete()
        return True
    return False


# ================= Examen =================


def CrearExamen(alumno_id, grupo_teoria_id, archivo, tipo="A"):
    grupo_teoria = None
    alumno = None
    if grupo_teoria_id:
        grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)
    if not grupo_teoria:
        return None
    if alumno_id:
        alumno = ObtenerAlumnoId(alumno_id)
    if not alumno:
        return None
    examen = Examen.objects.create(
        alumno=alumno,
        grupo_teoria=grupo_teoria,
        archivo=archivo,
        tipo=tipo,
    )
    return examen


def ObtenerExamenId(examen_id):
    try:
        return Examen.objects.get(id=examen_id)
    except Examen.DoesNotExist:
        return None


def EliminarExamen(examen_id):
    examen = ObtenerExamenId(examen_id)
    if examen:
        examen.delete()
        return True
    return False


# =========== Matricula Curso ================


def CrearMatriculaCurso(alumno_id, curso_id):
    alumno = None
    curso = None
    if alumno_id:
        alumno = ObtenerAlumnoId(alumno_id)
    if not alumno:
        return None
    if curso_id:
        curso = ObtenerCursoId(curso_id)
    if not curso:
        return None

    matricula = MatriculaCurso.objects.create(
        alumno=alumno,
        curso=curso,
    )
    return matricula


def ObtenerMatriculaCursoId(matricula_curso_id):
    try:
        return MatriculaCurso.objects.get(id=matricula_curso_id)
    except MatriculaCurso.DoesNotExist:
        return None


def EliminarMatriculaCurso(matricula_curso_id):
    matricula = ObtenerMatriculaCursoId(matricula_curso_id)
    if matricula:
        matricula.delete()
        return True
    return False


# =============== Nota ================


def CrearNota(alumno_id, periodo, peso, tipo):
    alumno = None
    if alumno_id:
        alumno = ObtenerAlumnoId(alumno_id)
    if not alumno:
        return None

    nota = Nota.objects.create(
        alumno=alumno,
        periodo=periodo,
        peso=peso,
        tipo=tipo,
    )
    return nota


def ObtenerNotaId(nota_id):
    try:
        return Nota.objects.get(id=nota_id)
    except Nota.DoesNotExist:
        return None


def EliminarNota(nota_id):
    nota = ObtenerNotaId(nota_id)
    if nota:
        nota.delete()
        return True
    return False


# ============= Matricula Laboratorio =============


def CrearMatriculaLaboratorio(alumno_id, grupo_laboratorio_id):
    alumno = None
    grupo_laboratorio = None
    if alumno_id:
        alumno = ObtenerAlumnoId(alumno_id)
    if not alumno:
        return None
    if grupo_laboratorio_id:
        grupo_laboratorio = ObtenerGrupoLaboratorioId(grupo_laboratorio_id)
    if not grupo_laboratorio:
        return None

    matricula = MatriculaLaboratorio.objects.create(
        alumno=alumno,
        grupo_laboratorio=grupo_laboratorio,
    )
    return matricula


def ObtenerMatriculaLaboratorioId(matricula_laboratorio_id):
    try:
        return MatriculaLaboratorio.objects.get(id=matricula_laboratorio_id)
    except MatriculaLaboratorio.DoesNotExist:
        return None


def EliminarMatriculaLaboratorio(matricula_laboratorio_id):
    matricula = ObtenerMatriculaLaboratorioId(matricula_laboratorio_id)
    if matricula:
        matricula.delete()
        return True
    return False


# =================== Tema ============================


def CrearTema(grupo_teoria_id, silabo_id, fecha, nombre, estado="N"):
    grupo_teoria = None
    silabo = None
    if grupo_teoria_id:
        grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)
    if silabo_id:
        silabo = ObtenerSilaboId(silabo_id)

    tema = Tema.objects.create(
        grupo_teoria=grupo_teoria,
        silabo=silabo,
        fecha=fecha,
        nombre=nombre,
        estado=estado,
    )

    return tema


def ObtenerTemaId(tema_id):
    try:
        return Tema.objects.get(id=tema_id)
    except Tema.DoesNotExist:
        return None


def EliminarTema(tema_id):
    tema = ObtenerTemaId(tema_id)
    if tema:
        tema.delete()
        return True
    return False


# ======================= Hora ======================


def CrearHora(
    aula_id=None,
    grupo_teoria_id=None,
    grupo_practica_id=None,
    grupo_laboratorio_id=None,
    reserva_id=None,
    dia=None,
    hora_inicio=None,
    hora_fin=None,
    tipo=None,
):
    aula = None
    grupo_teoria = None
    grupo_practica = None
    grupo_laboratorio = None
    reserva = None

    if aula_id:
        aula = ObtenerAulaId(aula_id)
        if not aula:
            return None

    grupos = [grupo_teoria_id, grupo_practica_id, grupo_laboratorio_id]
    grupos_asignados = sum(1 for g in grupos if g is not None)

    if grupos_asignados > 1:
        print(
            "❌ Error: Solo uno de los grupos (teoría, práctica o laboratorio) puede asignarse."
        )
        return None

    if grupo_teoria_id:
        grupo_teoria = ObtenerGrupoTeoriaId(grupo_teoria_id)
        if not grupo_teoria:
            return None

    elif grupo_practica_id:
        grupo_practica = ObtenerGrupoPracticaId(grupo_practica_id)
        if not grupo_practica:
            return None

    elif grupo_laboratorio_id:
        grupo_laboratorio = ObtenerGrupoLaboratorioId(grupo_laboratorio_id)
        if not grupo_laboratorio:
            return None

    elif reserva_id:
        reserva = ObtenerReservaId(reserva_id)
        if not reserva:
            return None

    hora = Hora.objects.create(
        aula=aula,
        grupo_teoria=grupo_teoria,
        grupo_practica=grupo_practica,
        grupo_laboratorio=grupo_laboratorio,
        reserva=reserva,
        dia=dia,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        tipo=tipo,
    )

    return hora


def ObtenerHoraId(hora_id):
    try:
        return Hora.objects.get(id=hora_id)
    except Hora.DoesNotExist:
        return None


def EliminarHora(hora_id):
    hora = ObtenerHoraId(hora_id)
    if hora:
        hora.delete()
        return True
    return False


# =================== Asistencia Profesor ================


def CrearAsistenciaProfesor(profesor_id, hora_id, fecha, estado="F"):
    profesor = None
    hora = None
    if profesor_id:
        profesor = ObtenerProfesorId(profesor_id)
    if not profesor:
        return None
    if hora_id:
        hora = ObtenerHoraId(hora_id)
    if not hora:
        return None

    asistencia = AsistenciaProfesor.objects.create(
        profesor=profesor,
        hora=hora,
        fecha=fecha,
        estado=estado,
    )
    return asistencia


def ObtenerAsisteciaProfesorId(asistencia_profesor_id):
    try:
        return AsistenciaProfesor.objects.get(id=asistencia_profesor_id)
    except AsistenciaProfesor.DoesNotExist:
        return None


def EliminarAsistenciaProfesor(asistencia_profesor_id):
    asistencia = ObtenerAsisteciaProfesorId(asistencia_profesor_id)
    if asistencia:
        asistencia.delete()
        return True
    return False


# =================== Asistencia ALumno ==================
def CrearAsistenciaAlumno(alumno_id, hora_id, fecha, estado="F"):
    alumno = None
    hora = None
    if alumno_id:
        alumno = ObtenerAlumnoId(alumno_id)
    if not alumno:
        return None
    if hora_id:
        hora = ObtenerHoraId(hora_id)
    if not hora:
        return None

    asistencia = AsistenciaAlumno.objects.create(
        alumno=alumno,
        hora=hora,
        fecha=fecha,
        estado=estado,
    )

    return asistencia


def ObtenerAsistenciaAlumnoId(asistencia_alumno_id):
    try:
        return AsistenciaAlumno.objects.get(id=asistencia_alumno_id)
    except AsistenciaAlumno.DoesNotExist:
        return None


def EliminarAsistenciaAlumno(asistencia_alumno_id):
    asistencia = ObtenerAsistenciaAlumnoId(asistencia_alumno_id)
    if asistencia:
        asistencia.delete()
        return True
    return False

# ================== 