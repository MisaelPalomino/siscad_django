from django.db import models


# /// DOMINIO USUARIO ///


class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    dni = models.CharField(max_length=8)  # Cambiado: IntegerField no tiene max_digits

    def __str__(self):
        return f"{self.nombre} ({self.email})"

    class Meta:
        abstract = True  # Corregido


class Profesor(Usuario):
    pass


class Secretaria(Usuario):
    pass


class Alumno(Usuario):
    cui = models.CharField(max_length=8)  # Cambiado


class Administrador(Usuario):
    pass


# /// DOMINIO CURSO ///


class Curso(models.Model):  # <-- Corregido
    nombre = models.CharField(max_length=100)
    semestre = models.PositiveIntegerField()  # Cambiado

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
    grupo_teoria = models.ForeignKey(
        GrupoTeoria, on_delete=models.CASCADE, related_name="grupos_laboratorio"
    )

    def __str__(self):
        return f"{self.grupo_teoria.curso.nombre} - Lab"


class MatriculaCurso(models.Model):
    alumno = models.ForeignKey(
        Alumno, on_delete=models.CASCADE, related_name="matriculas_curso"
    )
    curso = models.ForeignKey(
        Curso, on_delete=models.CASCADE, related_name="matriculas_curso"
    )  # Corregido

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

    def __str__(self):
        return f"{self.alumno.nombre} - {self.get_tipo_display()} ({self.periodo})"
