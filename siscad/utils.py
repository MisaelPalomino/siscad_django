import pandas as pd
from django.db import transaction
import datetime
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_time
from django.db.models import Q, Exists, OuterRef

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
    Hora,
    MatriculaLaboratorio,
    AsistenciaAlumno,
    AsistenciaProfesor,
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
        "horas_teoria",
        "horas_practica",
        "horas_laboratorio",
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

                horas_teoria = (
                    int(row["horas_teoria"]) if pd.notna(row["horas_teoria"]) else 0
                )

                horas_practica = (
                    int(row["horas_practica"]) if pd.notna(row["horas_practica"]) else 0
                )

                horas_laboratorio = (
                    int(row["horas_laboratorio"])
                    if pd.notna(row["horas_laboratorio"])
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
                        "horas_teoria": horas_teoria,
                        "horas_practica": horas_practica,
                        "horas_laboratorio": horas_laboratorio,
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
        print(f" El archivo {file} no existe.")
        return

    df = pd.read_excel(file)
    df.columns = [str(col).strip().lower() for col in df.columns]

    required_columns = ["nombre", "tipo"]
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
        f" Importación completada: {created} aulas creadas, {updated} aulas actualizadas."
    )
    if errores:
        print(" Errores encontrados:")
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

    print(f" Matrículas generadas rápidamente: {len(matriculas_a_crear)} registros.")


def insertar_grupos_teoria():
    """
    Crea grupos de teoría para cada curso y turno existente en MatriculaCurso,
    solo si el curso tiene horas de teoría (>0).
    Asigna profesores de forma equitativa (round-robin).
    No asigna alumnos directamente porque ya están vinculados por MatriculaCurso.
    """
    profesores = list(Profesor.objects.all())
    if not profesores:
        print(" No hay profesores disponibles en la base de datos.")
        return

    profesor_idx = 0
    created = 0
    existing = 0

    with transaction.atomic():
        cursos_turnos = MatriculaCurso.objects.values("curso", "turno").distinct()

        for ct in cursos_turnos:
            curso = Curso.objects.get(id=ct["curso"])
            turno = ct["turno"]

            if (
                curso.horas_teoria is None
                or curso.horas_teoria == 0
                or curso.semestre % 2 != 0
            ):
                print(f"Curso sin horas de teoría: {curso.nombre}. No se crea grupo.")
                continue

            grupo, created_flag = GrupoTeoria.objects.get_or_create(
                curso=curso,
                turno=turno,
                defaults={"profesor": profesores[profesor_idx]},
            )

            if created_flag:
                created += 1
                print(
                    f" Grupo creado: {curso.nombre} - Turno {turno} → Profesor: {profesores[profesor_idx].nombre}"
                )
                profesor_idx = (profesor_idx + 1) % len(profesores)
            else:
                existing += 1
                print(
                    f"ℹ Grupo ya existía: {curso.nombre} - Turno {turno}. Profesor actual: {grupo.profesor.nombre if grupo.profesor else 'Sin profesor'}"
                )

    print("\n Resumen final:")
    print(f"    {created} grupos creados")
    print(f"    {existing} grupos ya existían")


def insertar_grupos_practica():
    """
    Crea un grupo de práctica por cada grupo de teoría,
    manteniendo el mismo turno y profesor,
    solo si el curso tiene horas de práctica (>0).
    Si ya existe, no lo vuelve a crear.
    """
    grupos_teoria = GrupoTeoria.objects.all()
    creados = 0
    omitidos = 0
    sin_horas_practica = 0

    with transaction.atomic():
        for gt in grupos_teoria:
            curso = gt.curso

            if (
                curso.horas_practica is None
                or curso.horas_practica == 0
                or curso.semestre % 2 != 0
            ):
                sin_horas_practica += 1
                print(
                    f" Omitido (sin horas de práctica): {curso.nombre} - Turno {gt.turno}"
                )
                continue

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

    print("\n Resumen de creación de grupos de práctica:")
    print(f"    Grupos creados: {creados}")
    print(f"    Grupos ya existentes omitidos: {omitidos}")
    print(f"    Cursos sin horas de práctica omitidos: {sin_horas_practica}")


def insertar_notas():
    matriculas = MatriculaCurso.objects.select_related("curso", "alumno")
    notas_a_crear = []

    for matricula in matriculas:
        curso = matricula.curso
        alumno = matricula.alumno

        # Notas Parciales (tipo "P") - solo si tienen peso > 0
        parciales = [
            (1, curso.peso_parcial_1),
            (2, curso.peso_parcial_2),
            (3, curso.peso_parcial_3),
        ]

        # Notas Continuas (tipo "C") - solo si tienen peso > 0
        continuas = [
            (1, curso.peso_continua_1),
            (2, curso.peso_continua_2),
            (3, curso.peso_continua_3),
        ]

        # Crear notas parciales si no existen y tienen peso > 0
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
                        valor=-1,  # Cambiado de None a -1
                    )
                )

        # Crear notas continuas si no existen y tienen peso > 0
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
                        valor=-1,  # Cambiado de None a -1
                    )
                )

        # Crear nota de sustitutorio si el curso tiene al menos 2 parciales con peso > 0
        # Solo se crea si no existe y el curso tiene parciales 1 y 2
        if (
            curso.peso_parcial_1 > 0
            and curso.peso_parcial_2 > 0
            and not Nota.objects.filter(alumno=alumno, curso=curso, tipo="S").exists()
        ):
            notas_a_crear.append(
                Nota(
                    tipo="S",
                    periodo=1,  # Solo un sustitutorio
                    peso=1,  # Peso por defecto, se ajustará al calcular
                    alumno=alumno,
                    curso=curso,
                    valor=-1,  # Cambiado de None a -1
                )
            )

    with transaction.atomic():
        Nota.objects.bulk_create(notas_a_crear, batch_size=500)

    print(f" {len(notas_a_crear)} notas generadas exitosamente.")


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
        curso = gt.curso

        if (
            curso.horas_laboratorio is None
            or curso.horas_laboratorio == 0
            or curso.semestre % 2 != 0
        ):
            continue

        turno = gt.turno
        profesor = gt.profesor

        total_alumnos = MatriculaCurso.objects.filter(curso=curso, turno=turno).count()

        if total_alumnos == 0:
            continue

        num_labs = (total_alumnos + 19) // 20

        for i in range(num_labs):
            if i < len(secuencia_turnos.get(turno, [])):
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
        if laboratorios_a_crear:
            GrupoLaboratorio.objects.bulk_create(laboratorios_a_crear, batch_size=200)

    print(f" Laboratorios generados correctamente: {len(laboratorios_a_crear)}")


# DÍAS y TURNOS
DIAS = ["L", "M", "X", "J", "V"]  # Lunes-Viernes

# Turnos: A/C -> mañana, B/D -> tarde
TURNOS = {
    "A": {
        "nombre": "Mañana",
        "inicio": datetime.time(7, 0),
        "fin": datetime.time(15, 50),
    },
    "B": {
        "nombre": "Tarde",
        "inicio": datetime.time(12, 20),
        "fin": datetime.time(21, 20),
    },
    "C": {
        "nombre": "Mañana",
        "inicio": datetime.time(7, 0),
        "fin": datetime.time(15, 50),
    },
    "D": {
        "nombre": "Tarde",
        "inicio": datetime.time(12, 20),
        "fin": datetime.time(21, 20),
    },
}

CLASS_MIN = 50
BREAK_MIN = 10


def generar_bloques(inicio, fin):
    """
    Genera una timeline (lista de entries) para un turno:
    cada entry es dict {'type': 'class'|'break', 'start': time, 'end': time}
    con receso cada 2 bloques de clase.
    """
    timeline = []
    cur = datetime.datetime.combine(datetime.date.today(), inicio)
    limite = datetime.datetime.combine(datetime.date.today(), fin)
    count_class = 0

    while True:
        # intentar añadir clase
        if cur + datetime.timedelta(minutes=CLASS_MIN) > limite:
            break
        start_class = cur.time()
        end_class_dt = cur + datetime.timedelta(minutes=CLASS_MIN)
        end_class = end_class_dt.time()
        timeline.append({"type": "class", "start": start_class, "end": end_class})
        cur = end_class_dt
        count_class += 1

        # cada 2 clases insertar break si hay espacio
        if count_class % 2 == 0:
            if cur + datetime.timedelta(minutes=BREAK_MIN) <= limite:
                start_break = cur.time()
                end_break = (cur + datetime.timedelta(minutes=BREAK_MIN)).time()
                timeline.append(
                    {"type": "break", "start": start_break, "end": end_break}
                )
                cur = cur + datetime.timedelta(minutes=BREAK_MIN)
            else:
                break

    return timeline


def try_assign_sequence(
    dia,
    turno_key,
    timeline,
    sessions_needed,
    semestre,
    profesor_obj,
    tipo_aula,
    busy_sem,
    busy_prof,
    busy_aula,
):
    """
    Intenta encontrar en `timeline` un segmento que contenga `sessions_needed` bloques 'class'
    respetando que los índices de 'class' y 'break' estén en orden (internally timeline has breaks).
    Devuelve lista de asignaciones [{'idx': int, 'start': time, 'end': time, 'aula': Aula}] o [] si no hay.
    Requiere que la MISMA aula esté libre en todos los class slots (mejor continuidad).
    """
    # calcular cuantos breaks internos aparecerán en una secuencia continua
    internal_breaks = (sessions_needed - 1) // 2 if sessions_needed > 1 else 0
    total_len = sessions_needed + internal_breaks

    tl_len = len(timeline)
    if total_len > tl_len:
        return []

    # buscamos todos los start indices posibles
    for start_idx in range(0, tl_len - total_len + 1):
        segment = timeline[start_idx : start_idx + total_len]
        # comprobar que segment tiene la cantidad correcta de 'class' y 'break' en posiciones adecuadas
        class_positions = [i for i, e in enumerate(segment) if e["type"] == "class"]
        if len(class_positions) != sessions_needed:
            continue

        # obtenemos índices reales en timeline para cada class
        real_indices = [start_idx + pos for pos in class_positions]

        # buscar aulas candidatas del tipo requerido
        candidate_aulas = (
            [a for a in Aula.objects.all() if (a.tipo and a.tipo.lower() == "lab")]
            if tipo_aula == "lab"
            else [
                a
                for a in Aula.objects.all()
                if not (a.tipo and a.tipo.lower() == "lab")
            ]
        )
        if not candidate_aulas:
            return []

        # probar aulas una por una
        for aula in candidate_aulas:
            conflict = False
            assigned = []
            for idx in real_indices:
                # chequeos de ocupación
                if busy_sem.get((semestre, dia, turno_key, idx)):
                    conflict = True
                    break
                if profesor_obj and busy_prof.get(
                    (profesor_obj.id, dia, turno_key, idx)
                ):
                    conflict = True
                    break
                if busy_aula.get((aula.id, dia, turno_key, idx)):
                    conflict = True
                    break
                # si ok, añadir asignación tentativa
                assigned.append(
                    {
                        "idx": idx,
                        "start": timeline[idx]["start"],
                        "end": timeline[idx]["end"],
                        "aula": aula,
                    }
                )
            if conflict:
                continue
            # reservar definitivamente
            for a in assigned:
                busy_sem[(semestre, dia, turno_key, a["idx"])] = True
                if profesor_obj:
                    busy_prof[(profesor_obj.id, dia, turno_key, a["idx"])] = True
                busy_aula[(a["aula"].id, dia, turno_key, a["idx"])] = True
            return assigned
    return []


def generar_horarios_modeloA():
    """
    Genera horarios modelo A y exporta a siscad/horarios_debug.xlsx.
    También crea todas las horas vacías (disponibles para reservas).
    """

    print("🧩 Generando horarios modelo A con horas vacías...")

    # Preparar timelines por turno (A,B,C,D)
    TIMELINES = {k: generar_bloques(v["inicio"], v["fin"]) for k, v in TURNOS.items()}
    DIAS_SEMANA = ["L", "M", "X", "J", "V"]

    # Estructuras de ocupación
    busy_prof = {}
    busy_sem = {}
    busy_aula = {}

    # Cargar aulas una vez
    all_aulas = list(Aula.objects.all())
    aulas_by_type = {
        "lab": [a for a in all_aulas if a.tipo and a.tipo.lower() == "lab"],
        "aula": [a for a in all_aulas if not (a.tipo and a.tipo.lower() == "lab")],
    }

    # =========================================================
    # 🔹 PASO 1: CREAR TODAS LAS HORAS VACÍAS (tipo=None)
    # =========================================================
    print("🔸 Generando horas vacías...")
    created_count = 0

    for aula in all_aulas:
        for dia in DIAS_SEMANA:
            for turno_key, timeline in TIMELINES.items():
                for bloque in timeline:
                    if bloque["type"] == "class":  # ignoramos los recesos
                        hora_inicio = bloque["start"]
                        hora_fin = bloque["end"]

                        _, created = Hora.objects.get_or_create(
                            dia=dia,
                            aula=aula,
                            hora_inicio=hora_inicio,
                            hora_fin=hora_fin,
                            defaults={"tipo": None},
                        )
                        if created:
                            created_count += 1

    print(f"✅ Horas vacías creadas o ya existentes: {created_count}")

    # =========================================================
    # 🔹 PASO 2: CONTINUAR CON GENERACIÓN NORMAL
    # =========================================================

    datos = []
    problemas = []

    cursos_par = [
        c
        for c in Curso.objects.all()
        if isinstance(c.semestre, int) and c.semestre % 2 == 0
    ]

    grupos_teoria = list(GrupoTeoria.objects.select_related("curso", "profesor").all())
    grupos_practica = list(
        GrupoPractica.objects.select_related(
            "grupo_teoria__curso", "profesor", "grupo_teoria"
        ).all()
    )
    grupos_laboratorio = list(
        GrupoLaboratorio.objects.select_related(
            "grupo_teoria__curso", "profesor", "grupo_teoria"
        ).all()
    )

    # =========================================================
    # 🔹 TEORÍA
    # =========================================================
    for gt in grupos_teoria:
        curso = gt.curso
        if curso not in cursos_par:
            continue
        sessions_needed = int(curso.horas_teoria or 0)
        if sessions_needed <= 0:
            continue

        turno_codigo = getattr(gt, "turno", None) or "A"
        if turno_codigo not in TIMELINES:
            turno_codigo = "A"
        timeline = TIMELINES[turno_codigo]

        assigned_any = False
        for dia in DIAS_SEMANA:
            tipo_aula = "aula"
            assigned = try_assign_sequence(
                dia,
                turno_codigo,
                timeline,
                sessions_needed,
                curso.semestre,
                gt.profesor,
                tipo_aula,
                busy_sem,
                busy_prof,
                busy_aula,
            )
            if assigned:
                for block_no, a in enumerate(assigned, start=1):
                    Hora.objects.filter(
                        dia=dia,
                        aula=a["aula"],
                        hora_inicio=a["start"],
                        hora_fin=a["end"],
                    ).update(tipo="T", grupo_teoria=gt)

                    datos.append(
                        {
                            "Curso": curso.nombre,
                            "Código Curso": curso.codigo,
                            "Semestre": curso.semestre,
                            "Grupo (Teoría id)": gt.id,
                            "Tipo Sesión": "Teoría",
                            "Día": dia,
                            "Turno": turno_codigo,
                            "Bloque Nº": block_no,
                            "Inicio": a["start"].strftime("%H:%M"),
                            "Fin": a["end"].strftime("%H:%M"),
                            "Profesor": getattr(gt.profesor, "nombre", ""),
                            "Aula": a["aula"].nombre,
                        }
                    )
                assigned_any = True
                break

        if not assigned_any:
            problemas.append(
                {
                    "Elemento": f"Teoría {curso.nombre} (grupo id {gt.id})",
                    "Horas solicitadas": sessions_needed,
                    "Motivo": "No se encontró segmento continuo libre",
                }
            )

    # =========================================================
    # 🔹 PRÁCTICA
    # =========================================================
    for gp in grupos_practica:
        gt = getattr(gp, "grupo_teoria", None)
        if not gt:
            continue
        curso = gt.curso
        if curso not in cursos_par:
            continue
        sessions_needed = int(curso.horas_practica or 0)
        if sessions_needed <= 0:
            continue

        turno_codigo = getattr(gp, "turno", None) or getattr(gt, "turno", None) or "A"
        if turno_codigo not in TIMELINES:
            turno_codigo = "A"
        timeline = TIMELINES[turno_codigo]

        assigned_any = False
        for dia in DIAS_SEMANA:
            tipo_aula = "aula"
            assigned = try_assign_sequence(
                dia,
                turno_codigo,
                timeline,
                sessions_needed,
                curso.semestre,
                gp.profesor or gt.profesor,
                tipo_aula,
                busy_sem,
                busy_prof,
                busy_aula,
            )
            if assigned:
                for block_no, a in enumerate(assigned, start=1):
                    Hora.objects.filter(
                        dia=dia,
                        aula=a["aula"],
                        hora_inicio=a["start"],
                        hora_fin=a["end"],
                    ).update(tipo="P", grupo_practica=gp)
                assigned_any = True
                break

        if not assigned_any:
            problemas.append(
                {
                    "Elemento": f"Práctica {curso.nombre} (gp id {gp.id})",
                    "Horas solicitadas": sessions_needed,
                    "Motivo": "No se encontró segmento continuo libre",
                }
            )

    # =========================================================
    # 🔹 LABORATORIO
    # =========================================================
    for gl in grupos_laboratorio:
        gt = getattr(gl, "grupo_teoria", None)
        if not gt:
            continue
        curso = gt.curso
        if curso not in cursos_par:
            continue
        sessions_needed = int(curso.horas_laboratorio or 0)
        if sessions_needed <= 0:
            continue

        turno_codigo = getattr(gl, "turno", None) or getattr(gt, "turno", "A")
        if turno_codigo not in TIMELINES:
            turno_codigo = "A"
        timeline = TIMELINES[turno_codigo]

        assigned_any = False
        for dia in DIAS_SEMANA:
            tipo_aula = "lab"
            assigned = try_assign_sequence(
                dia,
                turno_codigo,
                timeline,
                sessions_needed,
                curso.semestre,
                gl.profesor or gt.profesor,
                tipo_aula,
                busy_sem,
                busy_prof,
                busy_aula,
            )
            if assigned:
                for block_no, a in enumerate(assigned, start=1):
                    Hora.objects.filter(
                        dia=dia,
                        aula=a["aula"],
                        hora_inicio=a["start"],
                        hora_fin=a["end"],
                    ).update(tipo="L", grupo_laboratorio=gl)
                assigned_any = True
                break

        if not assigned_any:
            problemas.append(
                {
                    "Elemento": f"Laboratorio {curso.nombre} (gl id {gl.id})",
                    "Horas solicitadas": sessions_needed,
                    "Motivo": "No se encontró segmento continuo libre",
                }
            )

    # =========================================================
    # 🔹 EXPORTAR A EXCEL
    # =========================================================
    base_dir = settings.BASE_DIR
    ruta_directorio = os.path.join(base_dir, "siscad", "datos")
    os.makedirs(ruta_directorio, exist_ok=True)
    ruta_archivo = os.path.join(ruta_directorio, "horarios_debug.xlsx")

    df = pd.DataFrame(datos)
    df.to_excel(ruta_archivo, index=False)

    if problemas:
        pd.DataFrame(problemas).to_excel(
            ruta_archivo.replace(".xlsx", "_problemas.xlsx"), index=False
        )

    print(f"✅ Horarios generados y exportados a: {ruta_archivo}")
    if problemas:
        print(f"⚠️ {len(problemas)} conflictos detectados.")

    return ruta_archivo


def cargar_horarios_desde_excel(ruta_excel="siscad/datos/horarios_debug.xlsx"):
    """
    Lee el archivo Excel generado y crea registros en el modelo Hora.
    """
    try:
        df = pd.read_excel(ruta_excel)
    except Exception as e:
        print(f" Error al leer el archivo Excel: {e}")
        return

    tipo_map = {"Teoría": "T", "Práctica": "P", "Laboratorio": "L", "Receso": "R"}

    creados = 0
    omitidos = 0

    with transaction.atomic():
        for _, row in df.iterrows():
            try:
                tipo_sesion_humano = row.get("Tipo Sesión")
                tipo_sesion = tipo_map.get(tipo_sesion_humano)

                if tipo_sesion is None:
                    print(f" Tipo de sesión desconocido en fila: {tipo_sesion_humano}")
                    omitidos += 1
                    continue

                # Normalizar aula como string
                aula_nombre = str(row.get("Aula", "")).strip()
                if aula_nombre.endswith(".0"):
                    aula_nombre = aula_nombre[:-2]  # Elimina .0

                aula = Aula.objects.filter(nombre=aula_nombre).first()
                if not aula:
                    print(f" Aula no encontrada: {aula_nombre}")
                    omitidos += 1
                    continue

                # Manejo de receso
                if tipo_sesion == "R":
                    hora_inicio = datetime.datetime.strptime(
                        str(row["Inicio"]), "%H:%M"
                    ).time()
                    hora_fin = datetime.datetime.strptime(
                        str(row["Fin"]), "%H:%M"
                    ).time()
                    Hora.objects.create(
                        dia=row["Día"],
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        tipo="R",
                        aula=aula,
                    )
                    creados += 1
                    continue

                # Buscar el grupo según el tipo
                grupo_obj = None
                if tipo_sesion == "T":
                    grupo_obj = GrupoTeoria.objects.filter(
                        id=row.get("Grupo (Teoría id)")
                    ).first()
                elif tipo_sesion == "P":
                    grupo_obj = GrupoPractica.objects.filter(
                        id=row.get("Grupo (Práctica id)")
                    ).first()
                elif tipo_sesion == "L":
                    grupo_obj = GrupoLaboratorio.objects.filter(
                        id=row.get("Grupo (Lab id)")
                    ).first()

                if not grupo_obj:
                    print(f" No se encontró el grupo para la fila: {row}")
                    omitidos += 1
                    continue

                hora_inicio = datetime.datetime.strptime(
                    str(row["Inicio"]), "%H:%M"
                ).time()
                hora_fin = datetime.datetime.strptime(str(row["Fin"]), "%H:%M").time()

                hora = Hora(
                    dia=row["Día"],
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    tipo=tipo_sesion,
                    aula=aula,
                )

                if tipo_sesion == "T":
                    hora.grupo_teoria = grupo_obj
                elif tipo_sesion == "P":
                    hora.grupo_practica = grupo_obj
                elif tipo_sesion == "L":
                    hora.grupo_laboratorio = grupo_obj

                hora.save()
                creados += 1

            except Exception as e:
                print(f" Error al procesar fila: {row}. Error: {e}")
                omitidos += 1
                continue

    print(f" Horarios insertados: {creados}")
    print(f"ℹ Filas omitidas: {omitidos}")


def insertar_matriculas_laboratorio():
    """
    Función para generar automáticamente matrículas de laboratorio
    basándose en las matrículas de curso existentes.
    """
    print("Iniciando proceso de matrículas automáticas de laboratorio...")

    with transaction.atomic():
        # Subconsulta para verificar si ya tiene matrícula de laboratorio en el mismo curso
        matricula_lab_existente = MatriculaLaboratorio.objects.filter(
            alumno=OuterRef("alumno"),
            grupo_laboratorio__grupo_teoria__curso=OuterRef("curso"),
        )

        # Obtener matrículas de curso que no tienen laboratorio asignado en el mismo curso
        matriculas_sin_lab = MatriculaCurso.objects.filter(
            ~Exists(matricula_lab_existente)
        ).select_related("alumno", "curso")

        print(f"Encontradas {matriculas_sin_lab.count()} matrículas sin laboratorio")

        matriculas_creadas = 0
        errores = 0

        for matricula in matriculas_sin_lab:
            try:
                alumno = matricula.alumno
                curso = matricula.curso
                turno_alumno = matricula.turno

                print(
                    f"Procesando: {alumno.nombre} - {curso.nombre} (Turno {turno_alumno})"
                )

                # Buscar grupos de laboratorio disponibles para este curso
                grupos_lab = (
                    GrupoLaboratorio.objects.filter(
                        grupo_teoria__curso=curso, cupos__gt=0
                    )
                    .select_related("profesor")
                    .order_by("grupo")
                )

                if not grupos_lab:
                    print(f"   No hay grupos de laboratorio para {curso.nombre}")
                    errores += 1
                    continue

                grupos_prioritarios = []
                grupos_secundarios = []
                otros_grupos = []

                for grupo in grupos_lab:
                    # Prioridad 1: Mismo grupo que el turno (A→A, B→B, C→C)
                    if grupo.grupo == turno_alumno:
                        grupos_prioritarios.append(grupo)
                    # Prioridad 2: Grupos según reglas específicas
                    elif (
                        (turno_alumno == "A" and grupo.grupo == "C")
                        or (turno_alumno == "B" and grupo.grupo == "D")
                        or (turno_alumno == "C" and grupo.grupo == "A")
                    ):
                        grupos_secundarios.append(grupo)
                    # Prioridad 3: Otros grupos disponibles
                    else:
                        otros_grupos.append(grupo)

                # Seleccionar grupo por prioridad
                grupo_seleccionado = None

                if grupos_prioritarios:
                    grupo_seleccionado = grupos_prioritarios[0]
                    tipo = "prioritario"
                elif grupos_secundarios:
                    grupo_seleccionado = grupos_secundarios[0]
                    tipo = "secundario"
                elif otros_grupos:
                    grupo_seleccionado = otros_grupos[0]
                    tipo = "disponible"
                else:
                    print(f" No hay grupos disponibles con cupos")
                    errores += 1
                    continue

                # Verificar nuevamente que no esté matriculado (por si acaso)
                if MatriculaLaboratorio.objects.filter(
                    alumno=alumno, grupo_laboratorio__grupo_teoria__curso=curso
                ).exists():
                    print(f" Ya está matriculado en un laboratorio de este curso")
                    continue

                # Crear la matrícula de laboratorio
                matricula_lab = MatriculaLaboratorio(
                    alumno=alumno, grupo_laboratorio=grupo_seleccionado
                )
                matricula_lab.save()

                # Decrementar cupos
                grupo_seleccionado.cupos -= 1
                grupo_seleccionado.save()

                matriculas_creadas += 1
                print(
                    f"  🎓 Matrícula creada: Lab {grupo_seleccionado.grupo} ({tipo}) - Cupos restantes: {grupo_seleccionado.cupos}"
                )

            except Exception as e:
                print(f"   Error procesando matrícula: {str(e)}")
                errores += 1
                continue

        print(f"\n📊 Resumen del proceso:")
        print(f"   Matrículas procesadas: {matriculas_sin_lab.count()}")
        print(f"   Matrículas creadas: {matriculas_creadas}")
        print(f"   Errores: {errores}")

        return matriculas_creadas


def insertar_data_excel():
    insertar_alumnos_excel("siscad/datos/Alumnos.xlsx")
    insertar_profesores_excel("siscad/datos/TablaProfesores.xlsx")
    insertar_secretarias_excel("siscad/datos/TablaSecretarias.xlsx")
    insertar_aulas_excel("siscad/datos/TablaAulas.xlsx")
    insertar_cursos_excel("siscad/datos/TablaCursosHoras.xlsx")


def generar_data():
    insertar_matriculas_curso()
    insertar_grupos_teoria()
    insertar_grupos_practica()
    insertar_notas()
    insertar_grupos_laboratorio()
    generar_horarios_modeloA()
    cargar_horarios_desde_excel()
    # insertar_matriculas_laboratorio()
    ejecutar_generacion_asistencias()
    ejecutar_generacion_asistencias_profesores()


def insertar_asistencia_alumno():
    """
    Función para pregenerar asistencias de alumnos desde el 2 de septiembre 2025 hasta el 25 de diciembre 2025.
    - Desde 02-09-2025 hasta hoy (28-10-2025): Todas las asistencias como Presente
    - Desde mañana (29-10-2025) hasta 25-12-2025: Todas las asistencias como Falta
    """
    print(" INICIANDO GENERACIÓN DE ASISTENCIAS AUTOMÁTICAS 2025...")

    # Fechas importantes CORREGIDAS para 2025
    fecha_inicio = datetime.date(2025, 9, 2)  # 2 de septiembre de 2025
    fecha_fin = datetime.date(2025, 12, 25)  # 25 de diciembre de 2025
    fecha_hoy = datetime.date(2025, 10, 28)  # 28 de octubre de 2025 (hoy)

    print(f" Rango de fechas: {fecha_inicio} hasta {fecha_fin}")
    print(f" Fecha de hoy: {fecha_hoy}")
    print(f" Presentes desde: {fecha_inicio} hasta {fecha_hoy}")
    print(f" Faltas desde: {fecha_hoy + datetime.timedelta(days=1)} hasta {fecha_fin}")

    with transaction.atomic():
        asistencias_creadas = 0
        errores = 0

        # Obtener todos los alumnos con matrículas
        alumnos = Alumno.objects.filter(
            Q(matriculas_curso__isnull=False) | Q(matriculas_laboratorio__isnull=False)
        ).distinct()

        print(f" Procesando {alumnos.count()} alumnos...")

        for alumno in alumnos:
            try:
                # Obtener horarios del alumno (teoría, práctica y laboratorio)
                horarios_alumno = obtener_horarios_alumno(alumno)

                if not horarios_alumno:
                    print(f"    No se encontraron horarios para {alumno.nombre}")
                    continue

                # Generar asistencias para cada fecha en el rango
                fecha_actual = fecha_inicio
                while fecha_actual <= fecha_fin:
                    # Solo días de semana (Lunes a Viernes)
                    if fecha_actual.weekday() < 5:  # 0=Lunes, 4=Viernes
                        asistencias_fecha = generar_asistencias_fecha(
                            alumno, fecha_actual, horarios_alumno, fecha_hoy
                        )
                        asistencias_creadas += asistencias_fecha

                    fecha_actual += datetime.timedelta(days=1)

            except Exception as e:
                print(f"    Error procesando alumno {alumno.nombre}: {str(e)}")
                errores += 1
                continue

        print(f"\n RESUMEN FINAL:")
        print(f"   Asistencias creadas: {asistencias_creadas}")
        print(f"   Errores: {errores}")

        return asistencias_creadas


def obtener_horarios_alumno(alumno):
    """
    Obtiene todos los horarios (teoría, práctica, laboratorio) de un alumno
    """
    # Obtener matrículas de curso
    matriculas_curso = MatriculaCurso.objects.filter(alumno=alumno)
    cursos_turnos = {m.curso_id: m.turno for m in matriculas_curso}
    cursos_ids = list(cursos_turnos.keys())

    # Obtener matrículas de laboratorio
    matriculas_lab = MatriculaLaboratorio.objects.filter(alumno=alumno)
    grupos_lab_ids = [ml.grupo_laboratorio_id for ml in matriculas_lab]

    # Consultar horarios
    horarios = (
        Hora.objects.filter(
            # Teoría del mismo turno
            Q(
                grupo_teoria__curso_id__in=cursos_ids,
                grupo_teoria__turno__in=[turno for turno in cursos_turnos.values()],
            )
            |
            # Práctica del mismo turno
            Q(
                grupo_practica__grupo_teoria__curso_id__in=cursos_ids,
                grupo_practica__turno__in=[turno for turno in cursos_turnos.values()],
            )
            |
            # Laboratorios matriculados
            Q(grupo_laboratorio_id__in=grupos_lab_ids)
        )
        .select_related(
            "grupo_teoria__curso",
            "grupo_practica__grupo_teoria__curso",
            "grupo_laboratorio__grupo_teoria__curso",
        )
        .order_by("dia", "hora_inicio")
    )

    return horarios


def generar_asistencias_fecha(alumno, fecha, horarios_alumno, fecha_hoy):
    """
    Genera asistencias para un alumno en una fecha específica (solo teoría y práctica)
    """
    asistencias_creadas = 0
    dia_semana = fecha.strftime("%A")

    dias_map = {
        "Monday": "L",
        "Tuesday": "M",
        "Wednesday": "X",
        "Thursday": "J",
        "Friday": "V",
    }

    dia_codigo = dias_map.get(dia_semana)
    if not dia_codigo:
        return 0

    horarios_dia = [h for h in horarios_alumno if h.dia == dia_codigo]

    if not horarios_dia:
        return 0

    estado = "P" if fecha <= fecha_hoy else "F"

    horarios_procesados = set()

    for hora in horarios_dia:
        try:
            if hora.grupo_teoria:
                curso_id = hora.grupo_teoria.curso_id
                tipo = "T"
            elif hora.grupo_practica:
                curso_id = hora.grupo_practica.grupo_teoria.curso_id
                tipo = "P"
            else:
                continue

            clave_curso = f"{curso_id}_{dia_codigo}_{tipo}"

            if clave_curso in horarios_procesados:
                continue

            horarios_procesados.add(clave_curso)

            # Evitar duplicados
            asistencia_existente = AsistenciaAlumno.objects.filter(
                alumno=alumno, fecha=fecha, hora=hora
            ).exists()

            if asistencia_existente:
                continue

            # Crear asistencia
            asistencia = AsistenciaAlumno(
                alumno=alumno, fecha=fecha, estado=estado, hora=hora
            )
            asistencia.save()
            asistencias_creadas += 1

            curso_nombre = (
                hora.grupo_teoria.curso.nombre
                if hora.grupo_teoria
                else hora.grupo_practica.grupo_teoria.curso.nombre
            )

            estado_display = " PRESENTE" if estado == "P" else " FALTA"

        except Exception as e:
            print(f"       Error en asistencia {fecha}: {str(e)}")
            continue

    return asistencias_creadas


def mostrar_estadisticas_asistencias():
    """
    Muestra estadísticas de las asistencias generadas
    """
    print("\n" + "=" * 60)
    print(" ESTADÍSTICAS DE ASISTENCIAS 2025")
    print("=" * 60)

    total_asistencias = AsistenciaAlumno.objects.count()
    presentes = AsistenciaAlumno.objects.filter(estado="P").count()
    faltas = AsistenciaAlumno.objects.filter(estado="F").count()

    print(f" Total de asistencias: {total_asistencias}")
    print(f" Presentes (hasta 28-10-2025): {presentes}")
    print(f" Faltas (desde 29-10-2025): {faltas}")

    if total_asistencias > 0:
        porcentaje_presente = (presentes / total_asistencias) * 100
        print(f" Porcentaje de asistencia: {porcentaje_presente:.1f}%")

    print(f"\n Distribución por meses:")
    meses = AsistenciaAlumno.objects.dates("fecha", "month")
    for mes in meses:
        asistencias_mes = AsistenciaAlumno.objects.filter(
            fecha__year=mes.year, fecha__month=mes.month
        )
        presentes_mes = asistencias_mes.filter(estado="P").count()
        total_mes = asistencias_mes.count()

        if total_mes > 0:
            porcentaje_mes = (presentes_mes / total_mes) * 100
            print(
                f"   {mes.strftime('%B %Y')}: {presentes_mes}/{total_mes} ({porcentaje_mes:.1f}%)"
            )


def limpiar_asistencias():
    """
    Elimina todas las asistencias (solo para testing)
    """
    print("  ELIMINANDO TODAS LAS ASISTENCIAS...")

    count = AsistenciaAlumno.objects.count()
    AsistenciaAlumno.objects.all().delete()

    print(f"  Eliminadas {count} asistencias")


def ejecutar_generacion_asistencias():
    """
    Función principal para ejecutar la generación de asistencias 2025
    """
    print(" INICIANDO GENERACIÓN MASIVA DE ASISTENCIAS 2025")
    print("=" * 70)

    mostrar_estadisticas_asistencias()

    print("\n GENERANDO ASISTENCIAS...")
    asistencias_creadas = insertar_asistencia_alumno()

    mostrar_estadisticas_asistencias()

    print(f"\n Proceso completado. Asistencias creadas: {asistencias_creadas}")

    return asistencias_creadas


def insertar_asistencia_profesor():
    """
    Función para pregenerar asistencias de profesores desde el 2 de septiembre 2025 hasta el 25 de diciembre 2025.
    - Desde 02-09-2025 hasta hoy: Todas las asistencias como Presente
    - Desde mañana hasta 25-12-2025: Todas las asistencias como Falta
    - Solo primera hora de cada curso por día (evita duplicados en horas seguidas)
    """
    print("🚀 INICIANDO GENERACIÓN DE ASISTENCIAS DE PROFESORES...")

    # Fechas importantes
    fecha_inicio = datetime.date(2025, 9, 2)  # 2 de septiembre de 2025
    fecha_fin = datetime.date(2025, 12, 25)  # 25 de diciembre de 2025
    fecha_hoy = datetime.datetime.now().date()  # Fecha actual del sistema

    if fecha_hoy < fecha_fin:
        print(
            f" Faltas desde: {fecha_hoy + datetime.timedelta(days=1)} hasta {fecha_fin}"
        )
    else:
        print("ℹ  Ya pasó la fecha final, todas las asistencias serán presentes")

    with transaction.atomic():
        asistencias_creadas = 0
        errores = 0

        # Obtener todos los profesores con horarios asignados
        profesores = Profesor.objects.filter(
            Q(grupos_teoria__isnull=False)
            | Q(grupos_practica__isnull=False)
            | Q(grupos_laboratorio__isnull=False)
        ).distinct()

        print(f" Procesando {profesores.count()} profesores...")

        for profesor in profesores:
            try:
                # Obtener horarios del profesor (teoría, práctica y laboratorio)
                horarios_profesor = obtener_horarios_profesor(profesor)

                if not horarios_profesor:
                    print(f"     No se encontraron horarios para {profesor.nombre}")
                    continue

                # Generar asistencias para cada fecha en el rango
                fecha_actual = fecha_inicio
                while fecha_actual <= fecha_fin:
                    # Solo días de semana (Lunes a Viernes)
                    if fecha_actual.weekday() < 5:  # 0=Lunes, 4=Viernes
                        asistencias_fecha = generar_asistencias_fecha_profesor(
                            profesor, fecha_actual, horarios_profesor, fecha_hoy
                        )
                        asistencias_creadas += asistencias_fecha

                    fecha_actual += datetime.timedelta(days=1)

            except Exception as e:
                print(f"    Error procesando profesor {profesor.nombre}: {str(e)}")
                errores += 1
                continue

        print(f"\n RESUMEN FINAL:")
        print(f"   Asistencias creadas: {asistencias_creadas}")
        print(f"   Errores: {errores}")

        return asistencias_creadas


def obtener_horarios_profesor(profesor):
    """
    Obtiene todos los horarios (teoría, práctica, laboratorio) de un profesor
    """
    horarios = (
        Hora.objects.filter(
            Q(grupo_teoria__profesor=profesor)
            | Q(grupo_practica__profesor=profesor)
            | Q(grupo_laboratorio__profesor=profesor)
        )
        .select_related(
            "grupo_teoria__curso",
            "grupo_practica__grupo_teoria__curso",
            "grupo_laboratorio__grupo_teoria__curso",
        )
        .order_by("dia", "hora_inicio")
    )

    return horarios


def generar_asistencias_fecha_profesor(profesor, fecha, horarios_profesor, fecha_hoy):
    """
    Genera asistencias para un profesor en una fecha específica
    """
    asistencias_creadas = 0
    dia_semana = fecha.strftime("%A")

    # Mapeo de días en español a códigos de la base de datos
    dias_map = {
        "Monday": "L",
        "Tuesday": "M",
        "Wednesday": "X",
        "Thursday": "J",
        "Friday": "V",
    }

    dia_codigo = dias_map.get(dia_semana)
    if not dia_codigo:
        return 0

    # Filtrar horarios para este día
    horarios_dia = [h for h in horarios_profesor if h.dia == dia_codigo]

    if not horarios_dia:
        return 0

    # Determinar estado según la fecha
    estado = (
        "P" if fecha <= fecha_hoy else "F"
    )  # Presente hasta hoy, Falta desde mañana

    # Agrupar horarios por curso para evitar duplicados en horas seguidas
    horarios_procesados = set()

    for hora in horarios_dia:
        try:
            # Identificar el curso para agrupar
            if hora.grupo_teoria:
                curso_id = hora.grupo_teoria.curso_id
                tipo = "T"
                grupo_id = hora.grupo_teoria_id
            elif hora.grupo_practica:
                curso_id = hora.grupo_practica.grupo_teoria.curso_id
                tipo = "P"
                grupo_id = hora.grupo_practica_id
            elif hora.grupo_laboratorio:
                curso_id = hora.grupo_laboratorio.grupo_teoria.curso_id
                tipo = "L"
                grupo_id = hora.grupo_laboratorio_id
            else:
                continue

            # Clave única para el curso y grupo en este día (evita horas seguidas del mismo grupo)
            clave_curso_grupo = f"{curso_id}_{grupo_id}_{dia_codigo}_{tipo}"

            # Si ya procesamos este curso+grupo en este día, saltar (solo primera hora)
            if clave_curso_grupo in horarios_procesados:
                continue

            # Marcar como procesado
            horarios_procesados.add(clave_curso_grupo)

            # Verificar si ya existe esta asistencia
            asistencia_existente = AsistenciaProfesor.objects.filter(
                profesor=profesor, fecha=fecha, hora=hora
            ).exists()

            if asistencia_existente:
                continue

            # Crear la asistencia
            asistencia = AsistenciaProfesor(
                profesor=profesor, fecha=fecha, estado=estado, hora=hora
            )
            asistencia.save()

            asistencias_creadas += 1

            # Debug informativo
            curso_nombre = ""
            if hora.grupo_teoria:
                curso_nombre = hora.grupo_teoria.curso.nombre
                grupo_info = f"T-{hora.grupo_teoria.turno}"
            elif hora.grupo_practica:
                curso_nombre = hora.grupo_practica.grupo_teoria.curso.nombre
                grupo_info = f"P-{hora.grupo_practica.turno}"
            elif hora.grupo_laboratorio:
                curso_nombre = hora.grupo_laboratorio.grupo_teoria.curso.nombre
                grupo_info = f"L-{hora.grupo_laboratorio.grupo}"

            estado_display = " PRESENTE" if estado == "P" else "❌ FALTA"

        except Exception as e:
            print(f"       Error en asistencia {fecha}: {str(e)}")
            continue

    return asistencias_creadas


# Función para mostrar estadísticas de asistencias de profesores - CORREGIDA
def mostrar_estadisticas_asistencias_profesores():
    """
    Muestra estadísticas de las asistencias generadas para profesores
    """
    print("\n" + "=" * 60)
    print("📊 ESTADÍSTICAS DE ASISTENCIAS DE PROFESORES 2025")
    print("=" * 60)

    total_asistencias = AsistenciaProfesor.objects.count()
    presentes = AsistenciaProfesor.objects.filter(estado="P").count()
    faltas = AsistenciaProfesor.objects.filter(estado="F").count()

    print(f" Total de asistencias: {total_asistencias}")
    print(f" Presentes (hasta {datetime.datetime.now().date()}): {presentes}")
    print(
        f" Faltas (desde {datetime.datetime.now().date() + datetime.timedelta(days=1)}): {faltas}"
    )

    if total_asistencias > 0:
        porcentaje_presente = (presentes / total_asistencias) * 100
        print(f" Porcentaje de asistencia: {porcentaje_presente:.1f}%")

    # Estadísticas por profesor - CORREGIDO: usar 'asistencias' en lugar de 'asistencias_profesor'
    print(f"\n Distribución por profesores:")
    profesores_con_asistencia = Profesor.objects.filter(
        asistencias__isnull=False
    ).distinct()

    for profesor in profesores_con_asistencia[:10]:  # Mostrar solo primeros 10
        asistencias_profesor = profesor.asistencias.count()
        presentes_profesor = profesor.asistencias.filter(estado="P").count()

        porcentaje_profesor = (
            (presentes_profesor / asistencias_profesor * 100)
            if asistencias_profesor > 0
            else 0
        )
        print(
            f"   {profesor.nombre}: {asistencias_profesor} registros ({presentes_profesor} presentes - {porcentaje_profesor:.1f}%)"
        )

    if profesores_con_asistencia.count() > 10:
        print(f"   ... y {profesores_con_asistencia.count() - 10} profesores más")


# Función para limpiar asistencias de profesores (solo testing)
def limpiar_asistencias_profesores():
    """
    Elimina todas las asistencias de profesores (solo para testing)
    """
    print("  ELIMINANDO TODAS LAS ASISTENCIAS DE PROFESORES...")

    count = AsistenciaProfesor.objects.count()
    AsistenciaProfesor.objects.all().delete()

    print(f"  Eliminadas {count} asistencias de profesores")


# Función principal
def ejecutar_generacion_asistencias_profesores():
    """
    Función principal para ejecutar la generación de asistencias de profesores
    """
    print(" INICIANDO GENERACIÓN MASIVA DE ASISTENCIAS DE PROFESORES 2025")
    print("=" * 70)

    # Mostrar estadísticas antes
    mostrar_estadisticas_asistencias_profesores()

    # Ejecutar generación
    print("\n GENERANDO ASISTENCIAS DE PROFESORES...")
    asistencias_creadas = insertar_asistencia_profesor()

    # Mostrar estadísticas después
    mostrar_estadisticas_asistencias_profesores()

    print(f"\n Proceso completado. Asistencias creadas: {asistencias_creadas}")

    return asistencias_creadas
