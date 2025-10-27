import pandas as pd
from django.db import transaction
from .models import (
    Alumno,
    Curso,
    MatriculaCurso,
    Profesor,
    Aula,
    GrupoTeoria,
    GrupoPractica,
    Nota,
    GrupoLaboratorio,
    Secretaria,
)
from pathlib import Path


def insertar_alumnos_excel(path_excel):
    """
    Inserta alumnos desde un archivo Excel usando el ORM de Django.
    Funciona desde la consola: python manage.py shell
    """
    file = Path(path_excel)

    if not file.exists():
        print(f" El archivo {file} no existe.")
        return

    df = pd.read_excel(file)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required_columns = ["apellidop", "apellidom", "nombres", "correo", "dni", "cui"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        print(f" Faltan columnas obligatorias: {', '.join(missing)}")
        return

    created = 0
    updated = 0
    errores = []

    with transaction.atomic():
        for index, row in df.iterrows():
            apellidop = (
                str(row["apellidop"]).strip() if pd.notna(row["apellidop"]) else ""
            )
            apellidom = (
                str(row["apellidom"]).strip() if pd.notna(row["apellidom"]) else ""
            )
            nombres = str(row["nombres"]).strip() if pd.notna(row["nombres"]) else ""
            email = (
                str(row["correo"]).strip().lower() if pd.notna(row["correo"]) else ""
            )

            dni = str(row["dni"]).strip() if pd.notna(row["dni"]) else ""
            cui = str(row["cui"]).strip() if pd.notna(row["cui"]) else ""

            nombre = f"{apellidop} {apellidom} {nombres}".strip()

            if not email:
                errores.append(f"Fila {index + 2}: email vacío, no se pudo procesar.")
                continue

            alumno, created_flag = Alumno.objects.update_or_create(
                email=email,
                defaults={"nombre": nombre, "dni": dni, "cui": cui},
            )

            if created_flag:
                created += 1
            else:
                updated += 1

    print(f" Importación completada: {created} creados, {updated} actualizados.")
    if errores:
        print(" Errores encontrados:")
        for err in errores[:10]:
            print(f"   - {err}")


def insertar_cursos_excel(path_excel):
    file = Path(path_excel)
    if not file.exists():
        print(f" El archivo {file} no existe.")
        return

    df = pd.read_excel(file)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required_columns = [
        "codigo",
        "nombre",
        "semestre",
        "prerrequisitos_str",
        "peso_parcial_1",
        "peso_parcial_2",
        "peso_parcial_3",
        "peso_continua_1",
        "peso_continua_2",
        "peso_continua_3",
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f" Faltan columnas obligatorias: {', '.join(missing)}")
        return

    created = 0
    updated = 0
    errores = []

    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                codigo = int(row["codigo"]) if pd.notna(row["codigo"]) else None
                nombre = str(row["nombre"]).strip() if pd.notna(row["nombre"]) else None
                semestre = int(row["semestre"]) if pd.notna(row["semestre"]) else 0
                prerequisito_raw = (
                    str(row["prerrequisitos_str"]).strip()
                    if pd.notna(row["prerrequisitos_str"])
                    else ""
                )

                #  Procesar prerequisito
                if prerequisito_raw and "," in prerequisito_raw:
                    prerequisito_codigo = int(prerequisito_raw.split(",")[0].strip())
                elif prerequisito_raw:
                    prerequisito_codigo = int(prerequisito_raw)
                else:
                    prerequisito_codigo = None

                #  Convertir pesos a int
                peso_parcial_1 = (
                    int(row["peso_parcial_1"]) if pd.notna(row["peso_parcial_1"]) else 0
                )
                peso_parcial_2 = (
                    int(row["peso_parcial_2"]) if pd.notna(row["peso_parcial_2"]) else 0
                )
                peso_parcial_3 = (
                    int(row["peso_parcial_3"]) if pd.notna(row["peso_parcial_3"]) else 0
                )
                peso_continua_1 = (
                    int(row["peso_continua_1"])
                    if pd.notna(row["peso_continua_1"])
                    else 0
                )
                peso_continua_2 = (
                    int(row["peso_continua_2"])
                    if pd.notna(row["peso_continua_2"])
                    else 0
                )
                peso_continua_3 = (
                    int(row["peso_continua_3"])
                    if pd.notna(row["peso_continua_3"])
                    else 0
                )

                if not codigo or not nombre:
                    errores.append(f"Fila {index + 2}: Código o nombre vacío.")
                    continue

                curso, created_flag = Curso.objects.update_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "semestre": semestre,
                        "prerequisito_codigo": prerequisito_codigo,
                        "peso_parcial_1": peso_parcial_1,
                        "peso_parcial_2": peso_parcial_2,
                        "peso_parcial_3": peso_parcial_3,
                        "peso_continua_1": peso_continua_1,
                        "peso_continua_2": peso_continua_2,
                        "peso_continua_3": peso_continua_3,
                    },
                )

                if created_flag:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errores.append(f"Fila {index + 2}: Error procesando datos - {str(e)}")

    print(f" Importación completada: {created} creados, {updated} actualizados.")
    if errores:
        print(" Errores encontrados:")
        for err in errores:
            print(f"   - {err}")


def insertar_profesores_excel(path_excel):
    file = Path(path_excel)

    if not file.exists():
        print(f" El archivo {file} no existe.")
        return

    df = pd.read_excel(file)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required_columns = ["nombre", "email", "dni", "cantidad_reservas"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f" Faltan columnas obligatorias: {', '.join(missing)}")
        return

    created = 0
    updated = 0
    errores = []

    with transaction.atomic():
        for index, row in df.iterrows():
            nombre = str(row["nombre"]).strip() if pd.notna(row["nombre"]) else ""
            email = str(row["email"]).strip().lower() if pd.notna(row["email"]) else ""
            dni = str(row["dni"]).strip() if pd.notna(row["dni"]) else ""
            cantidad_reservas = (
                int(row["cantidad_reservas"])
                if pd.notna(row["cantidad_reservas"])
                else 0
            )

            if not email:
                errores.append(f"Fila {index + 2}: email vacío, no se pudo procesar.")
                continue

            profesor, created_flag = Profesor.objects.update_or_create(
                email=email,
                defaults={
                    "nombre": nombre,
                    "dni": dni,
                    "cantidad_reservas": cantidad_reservas,
                },
            )

            if created_flag:
                created += 1
            else:
                updated += 1

    print(f" Importación completada: {created} creados, {updated} actualizados.")
    if errores:
        print(" Errores encontrados:")
        for err in errores[:10]:
            print(f"   - {err}")
        if len(errores) > 10:
            print(f"   ... y {len(errores) - 10} errores más.")


def insertar_aulas_excel(path_excel):
    """
    Inserta o actualiza aulas desde un archivo Excel.
    Si el nombre del aula ya existe, solo se actualiza el tipo.
    """
    file = Path(path_excel)

    if not file.exists():
        print(f"❌ El archivo {file} no existe.")
        return

    df = pd.read_excel(file)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required_columns = ["nombre", "tipo"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        print(f"❌ Faltan columnas obligatorias: {', '.join(missing)}")
        return

    created = 0
    updated = 0
    errores = []

    with transaction.atomic():
        for index, row in df.iterrows():
            nombre = str(row["nombre"]).strip() if pd.notna(row["nombre"]) else ""
            tipo = str(row["tipo"]).strip().lower() if pd.notna(row["tipo"]) else ""

            if not nombre:
                errores.append(f"Fila {index + 2}: nombre vacío, no se pudo procesar.")
                continue

            if tipo not in ["aula", "lab"]:
                errores.append(
                    f"Fila {index + 2}: tipo '{tipo}' no es válido (permitidos: 'aula', 'lab')."
                )
                continue

            aula, created_flag = Aula.objects.update_or_create(
                nombre=nombre,
                defaults={"tipo": tipo},
            )

            if created_flag:
                created += 1
            else:
                updated += 1

    print(
        f"✅ Importación completada: {created} aulas creadas, {updated} aulas actualizadas."
    )
    if errores:
        print("⚠️ Errores encontrados:")
        for err in errores[:10]:
            print(f"   - {err}")
        if len(errores) > 10:
            print(f"   ... y {len(errores) - 10} errores más.")


def insertar_secretarias_excel(path_excel):
    file = Path(path_excel)

    if not file.exists():
        print(f" El archivo {file} no existe.")
        return

    df = pd.read_excel(file)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required_columns = ["nombre", "email", "dni"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f" Faltan columnas obligatorias: {', '.join(missing)}")
        return

    created = 0
    updated = 0
    errores = []

    with transaction.atomic():
        for index, row in df.iterrows():
            nombre = str(row["nombre"]).strip() if pd.notna(row["nombre"]) else ""
            email = str(row["email"]).strip().lower() if pd.notna(row["email"]) else ""
            dni = str(row["dni"]).strip() if pd.notna(row["dni"]) else ""

            if not email:
                errores.append(f"Fila {index + 2}: email vacío, no se pudo procesar.")
                continue

            secretaria, created_flag = Secretaria.objects.update_or_create(
                email=email,
                defaults={
                    "nombre": nombre,
                    "dni": dni,
                },
            )

            if created_flag:
                created += 1
            else:
                updated += 1

    print(f" Importación completada: {created} creadas, {updated} actualizadas.")
    if errores:
        print(" Errores encontrados:")
        for err in errores[:10]:
            print(f"   - {err}")
        if len(errores) > 10:
            print(f"   ... y {len(errores) - 10} errores más.")


def insertar_matriculas_curso():
    alumnos = list(Alumno.objects.all())
    cursos = list(Curso.objects.all())

    alumnos_por_semestre = {}
    for alumno in alumnos:
        semestre = alumno.calcular_semestre()
        if semestre not in alumnos_por_semestre:
            alumnos_por_semestre[semestre] = []
        alumnos_por_semestre[semestre].append(alumno)

    cursos_por_semestre = {}
    for curso in cursos:
        if curso.semestre not in cursos_por_semestre:
            cursos_por_semestre[curso.semestre] = []
        cursos_por_semestre[curso.semestre].append(curso)

    matriculas_a_crear = []

    for semestre, cursos_sem in cursos_por_semestre.items():
        alumnos_sem = alumnos_por_semestre.get(semestre, [])

        for curso in cursos_sem:
            turno_A = 0
            turno_B = 0
            turno_C = 0

            for alumno in alumnos_sem:
                if turno_A < 40:
                    turno = "A"
                    turno_A += 1
                elif turno_B < 40:
                    turno = "B"
                    turno_B += 1
                elif turno_C < 40:
                    turno = "C"
                    turno_C += 1
                else:
                    break

                matriculas_a_crear.append(
                    MatriculaCurso(alumno=alumno, curso=curso, turno=turno)
                )

    with transaction.atomic():
        MatriculaCurso.objects.bulk_create(matriculas_a_crear, batch_size=500)

    print(f"✅ Matrículas generadas rápidamente: {len(matriculas_a_crear)} registros.")


def insertar_grupos_teoria():
    """
    Crea grupos de teoría para cada curso y turno existente en MatriculaCurso.
    Asigna profesores de forma equitativa (round-robin).
    No asigna alumnos directamente porque ya están vinculados por MatriculaCurso.
    """
    profesores = list(Profesor.objects.all())
    if not profesores:
        print("❌ No hay profesores disponibles en la base de datos.")
        return

    profesor_idx = 0
    created = 0
    existing = 0

    with transaction.atomic():
        cursos_turnos = MatriculaCurso.objects.values("curso", "turno").distinct()

        for ct in cursos_turnos:
            curso = Curso.objects.get(id=ct["curso"])
            turno = ct["turno"]

            grupo, created_flag = GrupoTeoria.objects.get_or_create(
                curso=curso,
                turno=turno,
                defaults={"profesor": profesores[profesor_idx]},
            )

            if created_flag:
                created += 1
                print(
                    f"✅ Grupo creado: {curso.nombre} - Turno {turno} → Profesor: {profesores[profesor_idx].nombre}"
                )
                profesor_idx = (profesor_idx + 1) % len(profesores)
            else:
                existing += 1
                print(
                    f"ℹ️ Grupo ya existía: {curso.nombre} - Turno {turno}. Profesor actual: {grupo.profesor.nombre if grupo.profesor else 'Sin profesor'}"
                )

    print("\n📊 Resumen final:")
    print(f"   ➕ {created} grupos creados")
    print(f"   🔁 {existing} grupos ya existían")


def insertar_grupos_practica():
    """
    Crea un grupo de práctica por cada grupo de teoría,
    manteniendo el mismo turno y profesor.
    Si ya existe, no lo vuelve a crear.
    """
    grupos_teoria = GrupoTeoria.objects.all()
    creados = 0
    omitidos = 0

    with transaction.atomic():
        for gt in grupos_teoria:
            # Verificar si ya existe un grupo de práctica con mismo grupo_teoria y turno
            existe = GrupoPractica.objects.filter(
                grupo_teoria=gt, turno=gt.turno
            ).first()

            if existe:
                omitidos += 1
                continue

            GrupoPractica.objects.create(
                grupo_teoria=gt,
                profesor=gt.profesor,  # Mismo profesor que teoría
                turno=gt.turno,  # Mismo turno que teoría
            )
            creados += 1

    print(f"✅ Grupos de práctica creados: {creados}")
    print(f"ℹ️ Grupos ya existentes omitidos: {omitidos}")


def insertar_notas():
    matriculas = MatriculaCurso.objects.select_related("curso", "alumno")
    notas_a_crear = []

    for matricula in matriculas:
        curso = matricula.curso
        alumno = matricula.alumno

        # Notas Parciales (tipo "P")
        parciales = [
            (1, curso.peso_parcial_1),
            (2, curso.peso_parcial_2),
            (3, curso.peso_parcial_3),
        ]

        # Notas Continuas (tipo "C")
        continuas = [
            (1, curso.peso_continua_1),
            (2, curso.peso_continua_2),
            (3, curso.peso_continua_3),
        ]

        # Crear notas si no existen
        for periodo, peso in parciales:
            if (
                peso > 0
                and not Nota.objects.filter(
                    alumno=alumno, curso=curso, tipo="P", periodo=periodo
                ).exists()
            ):
                notas_a_crear.append(
                    Nota(
                        tipo="P",
                        periodo=periodo,
                        peso=peso,
                        alumno=alumno,
                        curso=curso,
                        valor=None,  # Nota aún no registrada
                    )
                )

        for periodo, peso in continuas:
            if (
                peso > 0
                and not Nota.objects.filter(
                    alumno=alumno, curso=curso, tipo="C", periodo=periodo
                ).exists()
            ):
                notas_a_crear.append(
                    Nota(
                        tipo="C",
                        periodo=periodo,
                        peso=peso,
                        alumno=alumno,
                        curso=curso,
                        valor=None,  # Nota aún no registrada
                    )
                )

    with transaction.atomic():
        Nota.objects.bulk_create(notas_a_crear, batch_size=500)

    print(f"✅ {len(notas_a_crear)} notas generadas exitosamente.")


def insertar_grupos_laboratorio():
    from django.db import transaction

    laboratorios_a_crear = []

    secuencia_turnos = {
        "A": ["A", "C"],
        "B": ["B", "D"],
        "C": ["E", "F"],
    }

    grupos_teoria = GrupoTeoria.objects.all()

    for gt in grupos_teoria:
        turno = gt.turno
        profesor = gt.profesor

        total_alumnos = MatriculaCurso.objects.filter(
            curso=gt.curso, turno=turno
        ).count()

        if total_alumnos == 0:
            continue

        num_labs = (total_alumnos + 19) // 20

        for i in range(num_labs):
            if i < len(secuencia_turnos[turno]):
                lab_turno = secuencia_turnos[turno][i]
            else:
                lab_turno = chr(
                    ord(secuencia_turnos[turno][-1])
                    + (i - len(secuencia_turnos[turno]) + 1) * 2
                )

            laboratorios_a_crear.append(
                GrupoLaboratorio(
                    grupo=lab_turno,
                    grupo_teoria=gt,
                    cupos=20,
                    profesor=profesor,
                )
            )

    with transaction.atomic():
        GrupoLaboratorio.objects.bulk_create(laboratorios_a_crear, batch_size=200)

    print(f" Laboratorios generados correctamente: {len(laboratorios_a_crear)}")


def insertar_matriculas_laboratorios():
    pass


def insertar_horas():
    pass


def insertar_asistencia_profesor():
    pass


def insertar_asistencia_alumno():
    pass


def insertar_data_excel():
    insertar_alumnos_excel("siscad/datos/Alumnos.xlsx")
    insertar_profesores_excel("siscad/datos/TablaProfesores.xlsx")
    insertar_secretarias_excel("siscad/datos/TablaSecretarias.xlsx")
    insertar_aulas_excel("siscad/datos/TablaAulas.xlsx")
    insertar_cursos_excel("siscad/datos/TablaCursos.xlsx")


def generar_data():
    insertar_matriculas_curso()
    insertar_grupos_teoria()
    insertar_grupos_practica()
    insertar_notas()
    insertar_grupos_laboratorio()
    pass
