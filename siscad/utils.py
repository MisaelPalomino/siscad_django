import pandas as pd
from django.db import transaction
from .models import Alumno, Curso
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


def insertar_aula_excel():
    pass


def insertar_matriculas_curso():
    pass


def insertar_grupos_teoria():
    pass


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
