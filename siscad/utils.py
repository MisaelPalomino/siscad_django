import pandas as pd
from django.db import transaction
from .models import Alumno, Curso, MatriculaCurso, Profesor, Aula, GrupoTeoria
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
                defaults={"profesor": profesores[profesor_idx]}
            )

            if created_flag:
                created += 1
                print(f"✅ Grupo creado: {curso.nombre} - Turno {turno} → Profesor: {profesores[profesor_idx].nombre}")
                profesor_idx = (profesor_idx + 1) % len(profesores)  
            else:
                existing += 1
                print(f"ℹ️ Grupo ya existía: {curso.nombre} - Turno {turno}. Profesor actual: {grupo.profesor.nombre if grupo.profesor else 'Sin profesor'}")

    print("\n📊 Resumen final:")
    print(f"   ➕ {created} grupos creados")
    print(f"   🔁 {existing} grupos ya existían")


def insertar_grupos_practica():
    pass


def insertar_notas():
    pass


def insertar_grupos_laboratorio():
    pass


def insertar_matriculas_laboratorios():
    pass


def insertar_horas():
    pass


def insertar_asistencia_profesor():
    pass


def insertar_asistencia_alumno():
    pass
