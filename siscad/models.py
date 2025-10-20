from django.db import models
from django.contrib.auth.models import User


# /// DOMINIO USUARIO ///


class Usuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    dni = models.CharField(max_length=8)

    def __str__(self):
        return f"{self.nombre} ({self.email})"

    class Meta:
        abstract = True  # Corregido


class Profesor(Usuario):
    cantidad_reservas = models.IntegerField(default=2)
    pass


class Secretaria(Usuario):
    pass


class Alumno(Usuario):
    cui = models.CharField(max_length=8)  # Cambiado


class Administrador(Usuario):
    pass


# /// DOMINIO CURSO ///


class Curso(models.Model):
    nombre = models.CharField(max_length=100)
    semestre = models.PositiveIntegerField()
    peso_parcial_1 = models.PositiveIntegerField()
    peso_parcial_2 = models.PositiveIntegerField()
    peso_parcial_3 = models.PositiveIntegerField()
    peso_continua_1 = models.PositiveIntegerField()
    peso_continua_2 = models.PositiveIntegerField()
    peso_continua_3 = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre} - Semestre {self.semestre}"


class GrupoTeoria(models.Model):
    TURNOS = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
    ]

    curso = models.ForeignKey(
        Curso, on_delete=models.CASCADE, related_name="grupos_teoria"
    )
    profesor = models.ForeignKey(
        Profesor, on_delete=models.SET_NULL, null=True, related_name="grupos_teoria"
    )
    turno = models.CharField(max_length=1, choices=TURNOS)

    def __str__(self):
        return f"{self.curso.nombre} - Teoría {self.turno}"


class GrupoPractica(models.Model):
    TURNOS = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
    ]

    grupo_teoria = models.ForeignKey(
        GrupoTeoria, on_delete=models.CASCADE, related_name="grupos_practica"
    )
    profesor = models.ForeignKey(
        Profesor, on_delete=models.SET_NULL, null=True, related_name="grupos_practica"
    )
    turno = models.CharField(max_length=1, choices=TURNOS)

    def __str__(self):
        return f"{self.grupo_teoria.curso.nombre} - Práctica {self.turno}"


class GrupoLaboratorio(models.Model):
    grupo = models.CharField(max_length=1)  # A B o C
    grupo_teoria = models.ForeignKey(
        GrupoTeoria, on_delete=models.CASCADE, related_name="grupos_laboratorio"
    )
    cupos = models.IntegerField()
    profesor = models.ForeignKey(
        Profesor,
        on_delete=models.SET_NULL,
        null=True,
        related_name="grupos_laboratorio",
    )

    def __str__(self):
        return f"{self.grupo_teoria.curso.nombre} - Lab"


class MatriculaCurso(models.Model):
    TURNOS = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
    ]
    alumno = models.ForeignKey(
        Alumno, on_delete=models.CASCADE, related_name="matriculas_curso"
    )
    curso = models.ForeignKey(
        Curso, on_delete=models.CASCADE, related_name="matriculas_curso"
    )  # Corregido

    turno = models.CharField(max_length=1, choices=TURNOS)

    def __str__(self):
        return f"{self.alumno.nombre} inscrito en {self.curso.nombre}"


class MatriculaLaboratorio(models.Model):
    alumno = models.ForeignKey(
        Alumno, on_delete=models.CASCADE, related_name="matriculas_laboratorio"
    )
    grupo_laboratorio = models.ForeignKey(
        GrupoLaboratorio,
        on_delete=models.CASCADE,
        related_name="matriculas_laboratorio",
    )

    def __str__(self):
        return f"{self.alumno.nombre} - {self.grupo_laboratorio}"


# /// DOMINIO ACADEMICO ///


class Nota(models.Model):
    TIPOS = [
        ("P", "Parcial"),
        ("C", "Continua"),
    ]
    tipo = models.CharField(max_length=1, choices=TIPOS)
    periodo = models.PositiveIntegerField()
    peso = models.PositiveIntegerField()
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="notas")
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="notas")
    valor = models.FloatField(default=0)

    def __str__(self):
        return f"{self.alumno.nombre} - {self.get_tipo_display()} ({self.periodo})"


class Silabo(models.Model):
    grupo_teoria = models.ForeignKey(
        GrupoTeoria, on_delete=models.SET_NULL, null=True, related_name="silabos"
    )
    nombre = models.CharField(max_length=100)
    archivo = models.FileField(upload_to="archivos/Silabos")


class Examen(models.Model):
    TIPOS = [
        ("A", "Alta"),
        ("P", "Promedio"),
        ("B", "Baja"),
    ]
    alumno = models.ForeignKey(
        Alumno, on_delete=models.CASCADE, related_name="examenes"
    )
    tipo = models.CharField(max_length=1, choices=TIPOS)
    GrupoTeoria = models.ForeignKey(
        GrupoTeoria, on_delete=models.CASCADE, related_name="examenes"
    )
    archivo = models.FileField(upload_to="archivos/Examenes")


class Tema(models.Model):
    ESTADOS = [("H", "Hecho"), ("N", "No hecho")]
    nombre = models.CharField(max_length=100)
    silabo = models.ForeignKey(
        Silabo, on_delete=models.SET_NULL, null=True, related_name="temas"
    )
    estado = models.CharField(max_length=1, choices=ESTADOS)
    fecha = models.DateField()
    grupo_teoria = models.ForeignKey(
        GrupoTeoria, on_delete=models.SET_NULL, null=True, related_name="temas"
    )


class Aula(models.Model):
    nombre = models.CharField(max_length=100)


class Reserva(models.Model):
    profesor = models.ForeignKey(
        Profesor, on_delete=models.CASCADE, related_name="reservas"
    )
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="reservas")


class Hora(models.Model):
    DIAS_SEMANA = [
        ("L", "Lunes"),
        ("M", "Martes"),
        ("X", "Miércoles"),
        ("J", "Jueves"),
        ("V", "Viernes"),
        ("S", "Sábado"),
    ]

    TIPOS_SESION = [
        ("T", "Teoría"),
        ("P", "Práctica"),
        ("L", "Laboratorio"),
        ("R", "Reserva"),
    ]

    dia = models.CharField(max_length=1, choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    tipo = models.CharField(max_length=1, choices=TIPOS_SESION)
    aula = models.ForeignKey(
        Aula, on_delete=models.SET_NULL, null=True, related_name="horas"
    )
    grupo_teoria = models.ForeignKey(
        GrupoTeoria, on_delete=models.SET_NULL, null=True, blank=True
    )
    grupo_practica = models.ForeignKey(
        GrupoPractica, on_delete=models.SET_NULL, null=True, blank=True
    )
    grupo_laboratorio = models.ForeignKey(
        GrupoLaboratorio, on_delete=models.SET_NULL, null=True, blank=True
    )

    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, null=True, blank=True, related_name="horas"
    )

    def __str__(self):
        return f"{self.get_dia_display()} {self.hora_inicio}-{self.hora_fin} ({self.get_tipo_display()})"


class AsistenciaProfesor(models.Model):
    ESTADOS = [("P", "Presente"), ("F", "Falta")]

    profesor = models.ForeignKey(
        Profesor, on_delete=models.CASCADE, related_name="asistencias"
    )
    fecha = models.DateField()
    estado = models.CharField(max_length=1, choices=ESTADOS)
    hora = models.ForeignKey(
        Hora, on_delete=models.CASCADE, related_name="asistencias_profesores"
    )


class AsistenciaAlumno(models.Model):
    ESTADOS = [("P", "Presente"), ("F", "Falta")]

    alumno = models.ForeignKey(
        Alumno, on_delete=models.CASCADE, related_name="asistencias"
    )
    fecha = models.DateField()
    estado = models.CharField(max_length=1, choices=ESTADOS)
    hora = models.ForeignKey(
        Hora, on_delete=models.CASCADE, related_name="asistencias_alumnos"
    )
