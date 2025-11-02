from datetime import date, datetime, timedelta

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count

from .forms import UploadExcelForm


import openpyxl
from openpyxl.utils import get_column_letter
from .models import (
    Profesor,
    Alumno,
    Secretaria,
    Administrador,
    Nota,
    Curso,
    MatriculaCurso,
    GrupoTeoria,
    GrupoLaboratorio,
    MatriculaLaboratorio,
    Hora,
    AsistenciaAlumno,
    GrupoPractica,
    AsistenciaProfesor,
)
import pandas as pd


def inicio(request):
    nombre = request.session.get("nombre")
    rol = request.session.get("rol")
    if not nombre:
        return redirect("login")

    return render(request, "siscad/inicio.html", {"nombre": nombre, "rol": rol})


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        dni = request.POST.get("dni")

        usuario = None
        rol = None

        if Profesor.objects.filter(email=email, dni=dni).exists():
            usuario = Profesor.objects.get(email=email, dni=dni)
            rol = "Profesor"
        elif Alumno.objects.filter(email=email, dni=dni).exists():
            usuario = Alumno.objects.get(email=email, dni=dni)
            rol = "Alumno"
        elif Secretaria.objects.filter(email=email, dni=dni).exists():
            usuario = Secretaria.objects.get(email=email, dni=dni)
            rol = "Secretaria"
        elif Administrador.objects.filter(email=email, dni=dni).exists():
            usuario = Administrador.objects.get(email=email, dni=dni)
            rol = "Administrador"

        if usuario:
            request.session["usuario_id"] = usuario.id
            request.session["rol"] = rol
            request.session["nombre"] = usuario.nombre
            request.session["email"] = email
            messages.success(request, f"Bienvenido {rol} {usuario.nombre}")

            return redirect(f"inicio_{rol.lower()}")

        else:
            messages.error(request, "Email o DNI incorrectos")

    return render(request, "siscad/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


# =======================Vista de Secretaria ===============================================
def inicio_secretaria(request):
    rol = request.session.get("rol")

    if rol != "Secretaria":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")
    return render(
        request, "siscad/secretaria/menu.html", {"nombre": nombre, "rol": rol}
    )


def insertar_alumnos_excel(request):
    if request.method == "POST":
        form = UploadExcelForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]

            try:
                df = pd.read_excel(file)
                df.columns = [str(col).strip().lower() for col in df.columns]

                required_columns = [
                    "apellidop",
                    "apellidom",
                    "nombres",
                    "correo",
                    "dni",
                    "cui",
                ]
                missing = [col for col in required_columns if col not in df.columns]
                if missing:
                    messages.error(
                        request, f"Faltan columnas obligatorias: {', '.join(missing)}"
                    )
                    return redirect("insertar_alumnos_excel")

                created = 0
                updated = 0
                errores = []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        apellidop = (
                            str(row["apellidop"]).strip()
                            if pd.notna(row["apellidop"])
                            else ""
                        )
                        apellidom = (
                            str(row["apellidom"]).strip()
                            if pd.notna(row["apellidom"])
                            else ""
                        )
                        nombres = (
                            str(row["nombres"]).strip()
                            if pd.notna(row["nombres"])
                            else ""
                        )
                        email = (
                            str(row["correo"]).strip().lower()
                            if pd.notna(row["correo"])
                            else ""
                        )
                        dni = str(row["dni"]).strip() if pd.notna(row["dni"]) else ""
                        cui = str(row["cui"]).strip() if pd.notna(row["cui"]) else ""

                        nombre = f"{apellidop} {apellidom} {nombres}".strip()

                        if not email:
                            errores.append(
                                f"Fila {index + 2}: email vacío, no se pudo procesar."
                            )
                            continue

                        alumno, created_flag = Alumno.objects.update_or_create(
                            email=email,
                            defaults={"nombre": nombre, "dni": dni, "cui": cui},
                        )

                        created += 1 if created_flag else updated + 1

                messages.success(
                    request,
                    f"✅ Importación completada: {created} creados, {updated} actualizados.",
                )
                if errores:
                    for err in errores[:10]:
                        messages.warning(request, err)

                return redirect("insertar_alumnos_excel")

            except Exception as e:
                messages.error(request, f"❌ Error leyendo el archivo: {e}")
                return redirect("insertar_alumnos_excel")

    else:
        form = UploadExcelForm()

    alumnos = Alumno.objects.all()

    return render(
        request,
        "siscad/secretaria/insertar_alumnos_excel.html",
        {"form": form, "alumnos": alumnos},
    )


def listar_alumno_grupo_teoria(request):
    alumnos = []
    curso_id = request.POST.get("curso_id", "")
    turno = request.POST.get("turno", "")
    semestre_tipo = request.POST.get("semestre_tipo", "")

    # Filtrar cursos según semestre seleccionado
    todos_cursos = Curso.objects.all()
    if semestre_tipo == "par":
        cursos = [c for c in todos_cursos if c.semestre % 2 == 0]
    elif semestre_tipo == "impar":
        cursos = [c for c in todos_cursos if c.semestre % 2 != 0]
    else:
        cursos = todos_cursos

    # Obtener turnos disponibles y alumnos si se seleccionó curso
    turnos = []
    if request.method == "POST" and curso_id:
        turnos = (
            GrupoTeoria.objects.filter(curso_id=curso_id)
            .values_list("turno", flat=True)
            .distinct()
        )

        if turno:
            matriculas = MatriculaCurso.objects.filter(curso_id=curso_id, turno=turno)
            alumnos = [matricula.alumno for matricula in matriculas]

        # Descargar Excel
        if "descargar_excel" in request.POST and alumnos:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Alumnos"

            # Encabezados
            headers = ["Nombre", "Email", "DNI", "CUI"]
            for col_num, header in enumerate(headers, 1):
                ws[f"{get_column_letter(col_num)}1"] = header

            # Datos de alumnos
            for row_num, alumno in enumerate(alumnos, 2):
                ws[f"A{row_num}"] = alumno.nombre
                ws[f"B{row_num}"] = alumno.email
                ws[f"C{row_num}"] = alumno.dni
                ws[f"D{row_num}"] = alumno.cui

            # Nombre del archivo con curso y turno
            curso_nombre = Curso.objects.get(id=curso_id).nombre
            archivo_nombre = f"Alumnos_{curso_nombre}_Turno_{turno}.xlsx"

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="{archivo_nombre}"'
            wb.save(response)
            return response

    return render(
        request,
        "siscad/secretaria/listar_alumnos_grupo_teoria.html",
        {
            "alumnos": alumnos,
            "cursos": cursos,
            "turnos": turnos,
            "curso_id": curso_id,
            "turno": turno,
            "semestre_tipo": semestre_tipo,
        },
    )


def listar_grupos_laboratorio(request):
    laboratorios = GrupoLaboratorio.objects.select_related(
        "grupo_teoria", "grupo_teoria__curso", "profesor"
    ).all()

    if request.method == "POST":
        # Actualizar cupos de un laboratorio
        if "actualizar_cupos" in request.POST:
            lab_id = request.POST.get("lab_id")
            nuevos_cupos = request.POST.get("cupos")

            if lab_id and nuevos_cupos:
                try:
                    lab = GrupoLaboratorio.objects.get(id=lab_id)
                    lab.cupos = int(nuevos_cupos)
                    lab.save()
                    messages.success(
                        request,
                        f"Cupos actualizados para {lab.grupo_teoria.curso.nombre} - Lab {lab.grupo}",
                    )
                    return redirect("listar_grupos_laboratorio")
                except GrupoLaboratorio.DoesNotExist:
                    messages.error(request, "Laboratorio no encontrado")
                except ValueError:
                    messages.error(request, "El número de cupos debe ser un entero")

        # Descargar Excel
        elif "descargar_excel" in request.POST:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Laboratorios"

            headers = [
                "Curso",
                "Grupo Teoría",
                "Grupo Laboratorio",
                "Profesor",
                "Cupos",
            ]
            for col_num, header in enumerate(headers, 1):
                ws[f"{get_column_letter(col_num)}1"] = header

            for row_num, lab in enumerate(laboratorios, 2):
                ws[f"A{row_num}"] = lab.grupo_teoria.curso.nombre
                ws[f"B{row_num}"] = lab.grupo_teoria.turno
                ws[f"C{row_num}"] = lab.grupo
                ws[f"D{row_num}"] = (
                    lab.profesor.nombre if lab.profesor else "Sin asignar"
                )
                ws[f"E{row_num}"] = lab.cupos

            archivo_nombre = "Laboratorios_Disponibles.xlsx"
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="{archivo_nombre}"'
            wb.save(response)
            return response

    return render(
        request,
        "siscad/secretaria/listar_grupos_laboratorio.html",
        {"laboratorios": laboratorios},
    )


def listar_alumno_grupo_laboratorio(request):
    cursos = Curso.objects.all()
    laboratorios = []
    alumnos = []
    curso_id = None
    lab_id = None

    if request.method == "POST":
        curso_id = request.POST.get("curso_id")
        lab_id = request.POST.get("lab_id")

        # Filtrar laboratorios por curso seleccionado
        if curso_id:
            laboratorios = GrupoLaboratorio.objects.filter(
                grupo_teoria__curso_id=curso_id
            )

        # Buscar alumnos
        if lab_id and "buscar_alumnos" in request.POST:
            matriculas = MatriculaLaboratorio.objects.filter(
                grupo_laboratorio_id=lab_id
            )
            alumnos = [m.alumno for m in matriculas]

        # Descargar Excel
        if lab_id and "descargar_excel" in request.POST:
            matriculas = MatriculaLaboratorio.objects.filter(
                grupo_laboratorio_id=lab_id
            )
            alumnos = [m.alumno for m in matriculas]

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Alumnos Laboratorio"

            headers = ["Nombre", "Email", "DNI", "CUI"]
            for col_num, header in enumerate(headers, 1):
                ws[f"{get_column_letter(col_num)}1"] = header

            for row_num, alumno in enumerate(alumnos, 2):
                ws[f"A{row_num}"] = alumno.nombre
                ws[f"B{row_num}"] = alumno.email
                ws[f"C{row_num}"] = alumno.dni
                ws[f"D{row_num}"] = alumno.cui

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = (
                'attachment; filename="Alumnos_Laboratorio.xlsx"'
            )
            wb.save(response)
            return response

    return render(
        request,
        "siscad/secretaria/listar_alumno_grupo_laboratorio.html",
        {
            "cursos": cursos,
            "laboratorios": laboratorios,
            "alumnos": alumnos,
            "curso_id": curso_id,
            "lab_id": lab_id,
        },
    )


def visualizar_horarios_aulas(request):
    dias = ["L", "M", "X", "J", "V"]
    dias_nombres = {
        "L": "Lunes",
        "M": "Martes",
        "X": "Miércoles",
        "J": "Jueves",
        "V": "Viernes",
    }

    dias_lista = [(clave, dias_nombres[clave]) for clave in dias]

    horarios = Hora.objects.select_related(
        "aula",
        "grupo_teoria__curso",
        "grupo_practica__grupo_teoria__curso",
        "grupo_laboratorio__grupo_teoria__curso",
    ).order_by("aula__nombre", "hora_inicio")

    tabla_horarios = {}

    for h in horarios:
        if not h.aula:
            continue

        aula = h.aula.nombre
        bloque = f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
        dia = h.dia

        if aula not in tabla_horarios:
            tabla_horarios[aula] = {}

        if bloque not in tabla_horarios[aula]:
            tabla_horarios[aula][bloque] = {d: "" for d in dias}

        if h.grupo_teoria:
            curso = h.grupo_teoria.curso.nombre
            grupo = f"T{h.grupo_teoria.id}"
        elif h.grupo_practica:
            curso = h.grupo_practica.grupo_teoria.curso.nombre
            grupo = f"P{h.grupo_practica.id}"
        elif h.grupo_laboratorio:
            curso = h.grupo_laboratorio.grupo_teoria.curso.nombre
            grupo = f"L{h.grupo_laboratorio.id}"
        else:
            curso = "Receso"
            grupo = ""

        tabla_horarios[aula][bloque][dia] = f"{curso} ({grupo})"

    for aula in tabla_horarios:
        tabla_horarios[aula] = dict(
            sorted(tabla_horarios[aula].items(), key=lambda x: x[0])
        )

    context = {
        "dias_lista": dias_lista,
        "tabla_horarios": {
            aula: [
                {
                    "bloque": bloque,
                    "dias": [(dia, dias_data[dia]) for dia, _ in dias_lista],
                }
                for bloque, dias_data in bloques.items()
            ]
            for aula, bloques in tabla_horarios.items()
        },
    }

    return render(request, "siscad/secretaria/visualizar_horarios_aulas.html", context)


# =======================Vista de Alumno====================================================
def inicio_alumno(request):
    rol = request.session.get("rol")

    if rol != "Alumno":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")
    return render(request, "siscad/alumno/menu.html", {"nombre": nombre, "rol": rol})


def visualizar_notas(request):
    rol = request.session.get("rol")

    if rol != "Alumno":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")

    try:
        alumno = request.user.alumno
    except:
        from .models import Alumno

        alumno = Alumno.objects.filter(nombre=nombre).first()

    if not alumno:
        return redirect("inicio_alumno")

    matriculas = MatriculaCurso.objects.filter(alumno=alumno).select_related("curso")

    notas_por_curso = []

    for matricula in matriculas:
        curso = matricula.curso
        turno = matricula.turno

        notas_curso = Nota.objects.filter(alumno=alumno, curso=curso).order_by(
            "tipo", "periodo"
        )

        suma_ponderada = 0
        total_pesos = 0

        notas_parciales = []
        notas_continuas = []

        for nota in notas_curso:
            # Tratar las notas nulas como 0
            valor_nota = nota.valor if nota.valor is not None else 0

            suma_ponderada += valor_nota * nota.peso
            total_pesos += nota.peso

            if nota.tipo == "P":
                notas_parciales.append(
                    {
                        "valor": valor_nota,
                        "peso": nota.peso,
                        "periodo": nota.periodo,
                    }
                )
            elif nota.tipo == "C":
                notas_continuas.append(
                    {
                        "valor": valor_nota,
                        "peso": nota.peso,
                        "periodo": nota.periodo,
                    }
                )

        promedio_final = suma_ponderada / total_pesos if total_pesos > 0 else 0

        promedio_parcial = (
            sum([n["valor"] for n in notas_parciales]) / len(notas_parciales)
            if notas_parciales
            else 0
        )
        promedio_continua = (
            sum([n["valor"] for n in notas_continuas]) / len(notas_continuas)
            if notas_continuas
            else 0
        )

        if promedio_continua <= 0:
            promedio_continua = 0
        if promedio_parcial <= 0:
            promedio_parcial = 0

        notas_por_curso.append(
            {
                "curso": curso.nombre,
                "codigo_curso": curso.codigo,
                "turno": turno,
                "notas": list(notas_curso),
                "promedio_final": round(promedio_final, 2),
                "promedio_parcial": round(promedio_parcial, 2),
                "promedio_continua": round(promedio_continua, 2),
                "total_notas": len(notas_curso),
                "total_pesos": total_pesos,
                "notas_parciales": notas_parciales,
                "notas_continuas": notas_continuas,
                "suma_ponderada": round(suma_ponderada, 2),
            }
        )

    context = {
        "alumno": alumno,
        "notas_por_curso": notas_por_curso,
        "total_cursos": len(notas_por_curso),
        "semestre_actual": alumno.calcular_semestre() or "No asignado",
        "nombre": nombre,
        "rol": rol,
    }

    return render(request, "siscad/alumno/visualizar_notas.html", context)


def visualizar_horario_alumno(request):
    # 1. Obtener el alumno logueado usando el email de la sesión
    if "email" not in request.session:
        return redirect("login")

    email = request.session["email"]

    try:
        alumno = Alumno.objects.get(email=email)
    except Alumno.DoesNotExist:
        return redirect("login")
    except Alumno.MultipleObjectsReturned:
        alumno = Alumno.objects.filter(email=email).first()

    # 2. Obtener todas sus matrículas de curso
    matriculas_curso = MatriculaCurso.objects.filter(alumno=alumno).select_related(
        "curso"
    )
    print(
        f"DEBUG: Matrículas de curso del alumno: {[(m.curso.nombre, m.turno) for m in matriculas_curso]}"
    )

    # 3. Obtener todas sus matrículas de laboratorio
    matriculas_lab = MatriculaLaboratorio.objects.filter(alumno=alumno).select_related(
        "grupo_laboratorio__grupo_teoria__curso", "grupo_laboratorio__profesor"
    )
    print(
        f"DEBUG: Matrículas de laboratorio del alumno: {[f'{ml.grupo_laboratorio.grupo_teoria.curso.nombre} - Lab {ml.grupo_laboratorio.grupo}' for ml in matriculas_lab]}"
    )

    # 4. Obtener todos los cursos inscritos y sus turnos (para teoría y práctica)
    cursos_turnos = {m.curso_id: m.turno for m in matriculas_curso}
    cursos_ids = list(cursos_turnos.keys())

    # 5. Obtener IDs de grupos de laboratorio matriculados (para laboratorios)
    grupos_lab_ids = [ml.grupo_laboratorio_id for ml in matriculas_lab]

    if not cursos_ids and not grupos_lab_ids:
        cursos_ids = []
        grupos_lab_ids = []

    # 6. Buscar horarios relacionados - AHORA INCLUYENDO LABORATORIOS
    horarios = (
        Hora.objects.select_related(
            "aula",
            "grupo_teoria__curso",
            "grupo_practica__grupo_teoria__curso",
            "grupo_laboratorio__grupo_teoria__curso",
            "grupo_laboratorio__profesor",
        )
        .filter(
            # Coincidencia con teoría del mismo turno
            Q(
                grupo_teoria__curso_id__in=cursos_ids,
                grupo_teoria__turno__in=[turno for turno in cursos_turnos.values()],
            )
            |
            # Coincidencia con práctica del mismo turno
            Q(
                grupo_practica__grupo_teoria__curso_id__in=cursos_ids,
                grupo_practica__turno__in=[turno for turno in cursos_turnos.values()],
            )
            |
            # Coincidencia con laboratorios matriculados
            Q(grupo_laboratorio_id__in=grupos_lab_ids)
        )
        .order_by("dia", "hora_inicio")
    )

    print(
        f"DEBUG: Horarios encontrados (teoría + práctica + laboratorio): {horarios.count()}"
    )

    # Debug detallado de horarios encontrados
    for h in horarios:
        if h.grupo_teoria:
            tipo = "Teoría"
            curso_nombre = h.grupo_teoria.curso.nombre
            turno_info = f"T-{h.grupo_teoria.turno}"
        elif h.grupo_practica:
            tipo = "Práctica"
            curso_nombre = h.grupo_practica.grupo_teoria.curso.nombre
            turno_info = f"P-{h.grupo_practica.turno}"
        elif h.grupo_laboratorio:
            tipo = "Laboratorio"
            curso_nombre = h.grupo_laboratorio.grupo_teoria.curso.nombre
            turno_info = f"L-{h.grupo_laboratorio.grupo}"
        else:
            tipo = "Otro"
            curso_nombre = "Desconocido"
            turno_info = ""

        print(
            f"DEBUG Horario: {h.dia} {h.hora_inicio}-{h.hora_fin} - {tipo}: {curso_nombre} {turno_info} - Aula: {h.aula.nombre if h.aula else 'Sin aula'}"
        )

    # 7. Construir estructura para mostrar
    dias_lista = [
        ("L", "Lunes"),
        ("M", "Martes"),
        ("X", "Miércoles"),
        ("J", "Jueves"),
        ("V", "Viernes"),
    ]

    # Crear estructura de datos
    tabla_horarios = {}
    for h in horarios:
        bloque = f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
        dia = h.dia

        # Determinar si el horario debe mostrarse (filtrado por turno para teoría/práctica)
        mostrar_horario = False
        info_curso = ""

        if h.grupo_teoria:
            curso_id = h.grupo_teoria.curso_id
            turno_horario = h.grupo_teoria.turno
            turno_alumno = cursos_turnos.get(curso_id)

            # Mostrar solo si el turno coincide
            if turno_horario == turno_alumno:
                mostrar_horario = True
                curso = h.grupo_teoria.curso.nombre
                grupo = f"T-{turno_horario}"
                aula_info = f" ({h.aula.nombre})" if h.aula else ""
                info_curso = f"{curso} {grupo}{aula_info}"

        elif h.grupo_practica:
            curso_id = h.grupo_practica.grupo_teoria.curso_id
            turno_horario = h.grupo_practica.turno
            turno_alumno = cursos_turnos.get(curso_id)

            # Mostrar solo si el turno coincide
            if turno_horario == turno_alumno:
                mostrar_horario = True
                curso = h.grupo_practica.grupo_teoria.curso.nombre
                grupo = f"P-{turno_horario}"
                aula_info = f" ({h.aula.nombre})" if h.aula else ""
                info_curso = f"{curso} {grupo}{aula_info}"

        elif h.grupo_laboratorio:
            # Para laboratorios, mostrar siempre (ya están filtrados por matrícula)
            mostrar_horario = True
            curso = h.grupo_laboratorio.grupo_teoria.curso.nombre
            grupo = f"L-{h.grupo_laboratorio.grupo}"
            aula_info = f" ({h.aula.nombre})" if h.aula else ""
            profesor_info = (
                f" - {h.grupo_laboratorio.profesor.nombre}"
                if h.grupo_laboratorio.profesor
                else ""
            )
            info_curso = f"{curso} {grupo}{aula_info}{profesor_info}"

        # Si el horario debe mostrarse, agregarlo a la tabla
        if mostrar_horario and info_curso:
            # Usar "Horario General" como clave única para simplificar
            aula_key = "Horario General"

            if aula_key not in tabla_horarios:
                tabla_horarios[aula_key] = {}

            if bloque not in tabla_horarios[aula_key]:
                tabla_horarios[aula_key][bloque] = {d: "" for d, _ in dias_lista}

            tabla_horarios[aula_key][bloque][dia] = info_curso

    # Ordenar por hora
    for aula in tabla_horarios:
        tabla_horarios[aula] = dict(
            sorted(tabla_horarios[aula].items(), key=lambda x: x[0])
        )

    # Crear la estructura final
    context = {
        "alumno": alumno,
        "dias_lista": dias_lista,
        "tabla_horarios": {
            aula: [
                {
                    "bloque": bloque,
                    "dias": [(dia, dias_data[dia]) for dia, _ in dias_lista],
                }
                for bloque, dias_data in bloques.items()
            ]
            for aula, bloques in tabla_horarios.items()
        },
        "tiene_laboratorios": len(grupos_lab_ids) > 0,
        "total_laboratorios": len(grupos_lab_ids),
    }

    return render(request, "siscad/alumno/visualizar_horario_alumno.html", context)


def matricula_laboratorio(request):
    # 1. Obtener el alumno logueado
    if "email" not in request.session:
        return redirect("login")

    email = request.session["email"]

    try:
        alumno = Alumno.objects.get(email=email)
    except Alumno.DoesNotExist:
        messages.error(request, "Alumno no encontrado.")
        return redirect("login")
    except Alumno.MultipleObjectsReturned:
        alumno = Alumno.objects.filter(email=email).first()

    # 2. Obtener los cursos matriculados
    matriculas_curso = MatriculaCurso.objects.filter(
        alumno_id=alumno.id
    ).select_related("curso")

    if not matriculas_curso:
        messages.warning(request, "No tienes cursos matriculados.")
        return redirect("inicio_alumno")

    # 3. Procesar matrícula de laboratorio
    if request.method == "POST":
        grupo_lab_id = request.POST.get("grupo_laboratorio")

        if not grupo_lab_id:
            messages.error(request, "Debes seleccionar un grupo de laboratorio.")
            return redirect("matricula_laboratorio")

        try:
            with transaction.atomic():
                grupo_lab = GrupoLaboratorio.objects.select_related(
                    "grupo_teoria__curso", "profesor"
                ).get(id=grupo_lab_id)

                # Verificar que el alumno esté matriculado en el curso correspondiente
                matricula_curso = matriculas_curso.filter(
                    curso_id=grupo_lab.grupo_teoria.curso_id
                ).first()

                if not matricula_curso:
                    messages.error(request, "No estás matriculado en este curso.")
                    return redirect("matricula_laboratorio")

                # Verificar si ya está matriculado en un laboratorio de ese curso
                matricula_existente = MatriculaLaboratorio.objects.filter(
                    alumno_id=alumno.id,
                    grupo_laboratorio__grupo_teoria__curso_id=grupo_lab.grupo_teoria.curso_id,
                ).exists()

                if matricula_existente:
                    messages.error(
                        request,
                        f"Ya estás matriculado en un laboratorio de {grupo_lab.grupo_teoria.curso.nombre}.",
                    )
                    return redirect("matricula_laboratorio")

                # Verificar cupos
                if grupo_lab.cupos <= 0:
                    messages.error(
                        request,
                        "No hay cupos disponibles en este grupo de laboratorio.",
                    )
                    return redirect("matricula_laboratorio")

                # Crear matrícula
                matricula_lab = MatriculaLaboratorio(
                    alumno_id=alumno.id, grupo_laboratorio_id=grupo_lab.id
                )
                matricula_lab.save()

                # Actualizar cupos
                grupo_lab.cupos -= 1
                grupo_lab.save()

                generar_asistencias_laboratorio(alumno, grupo_lab)

                messages.success(
                    request,
                    f"Te has matriculado exitosamente en el laboratorio de {grupo_lab.grupo_teoria.curso.nombre} y se generaron tus asistencias.",
                )
                return redirect("matricula_laboratorio")

        except GrupoLaboratorio.DoesNotExist:
            messages.error(request, "El grupo de laboratorio seleccionado no existe.")
        except Exception as e:
            messages.error(request, f"Error al realizar la matrícula: {str(e)}")

    # 4. Obtener laboratorios disponibles
    laboratorios_disponibles = []

    for matricula in matriculas_curso:
        curso = matricula.curso
        turno_alumno = matricula.turno

        grupos_lab = (
            GrupoLaboratorio.objects.select_related("grupo_teoria__curso", "profesor")
            .filter(
                grupo_teoria__curso_id=curso.id,
                cupos__gt=0,
            )
            .exclude(matriculas_laboratorio__alumno_id=alumno.id)
        )

        grupos_compatibles = [
            g
            for g in grupos_lab
            if g.grupo == turno_alumno or g.grupo not in ["A", "B", "C"]
        ]

        if grupos_compatibles:
            laboratorios_disponibles.append(
                {
                    "curso": curso,
                    "turno_alumno": turno_alumno,
                    "grupos": grupos_compatibles,
                    "ya_matriculado": MatriculaLaboratorio.objects.filter(
                        alumno_id=alumno.id,
                        grupo_laboratorio__grupo_teoria__curso_id=curso.id,
                    ).exists(),
                }
            )

    # 5. Matrículas actuales
    matriculas_lab_actuales = MatriculaLaboratorio.objects.filter(
        alumno_id=alumno.id
    ).select_related(
        "grupo_laboratorio__grupo_teoria__curso", "grupo_laboratorio__profesor"
    )

    context = {
        "alumno": alumno,
        "laboratorios_disponibles": laboratorios_disponibles,
        "matriculas_lab_actuales": matriculas_lab_actuales,
    }

    return render(request, "siscad/alumno/matricula_laboratorio.html", context)


from datetime import date, timedelta


def generar_asistencias_laboratorio(alumno, grupo_lab):
    """
    Genera asistencias para el laboratorio matriculado por el alumno,
    desde el 2 de septiembre 2025 hasta el 25 de diciembre 2025.
    Si el laboratorio tiene horas consecutivas (bloques), se genera una sola asistencia por bloque.
    """
    print(
        f"🔧 Generando asistencias de laboratorio para {alumno.nombre} - {grupo_lab.grupo_teoria.curso.nombre}"
    )

    # Rango de fechas
    fecha_inicio = date(2025, 9, 2)
    fecha_fin = date(2025, 12, 25)
    fecha_hoy = date.today()

    asistencias_creadas = 0

    # Obtener los horarios del grupo de laboratorio
    horarios_lab = (
        Hora.objects.filter(grupo_laboratorio=grupo_lab)
        .select_related("grupo_laboratorio__grupo_teoria__curso")
        .order_by("dia", "hora_inicio")
    )

    if not horarios_lab.exists():
        print(f"   ⚠️ No se encontraron horarios para el laboratorio {grupo_lab.id}")
        return 0

    # Mapear días
    dias_map = {
        "Monday": "L",
        "Tuesday": "M",
        "Wednesday": "X",
        "Thursday": "J",
        "Friday": "V",
    }

    # Recorrer días desde inicio a fin
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        if fecha_actual.weekday() < 5:  # Solo lunes a viernes
            dia_codigo = dias_map.get(fecha_actual.strftime("%A"))

            # Horarios del laboratorio en ese día
            horarios_dia = [h for h in horarios_lab if h.dia == dia_codigo]
            if horarios_dia:
                # Agrupar bloques consecutivos
                horarios_dia.sort(key=lambda h: h.hora_inicio)
                bloques = []
                bloque_actual = [horarios_dia[0]]

                for i in range(1, len(horarios_dia)):
                    anterior = bloque_actual[-1]
                    actual = horarios_dia[i]
                    if actual.hora_inicio == anterior.hora_fin:
                        bloque_actual.append(actual)
                    else:
                        bloques.append(bloque_actual)
                        bloque_actual = [actual]
                bloques.append(bloque_actual)

                estado = "P" if fecha_actual <= fecha_hoy else "F"

                for bloque in bloques:
                    try:
                        hora_inicio = bloque[0].hora_inicio
                        hora_fin = bloque[-1].hora_fin
                        hora_referencia = bloque[0]

                        # Evitar duplicados
                        asistencia_existente = AsistenciaAlumno.objects.filter(
                            alumno=alumno,
                            fecha=fecha_actual,
                            hora__grupo_laboratorio=grupo_lab,
                        ).exists()

                        if asistencia_existente:
                            continue

                        # Crear asistencia
                        asistencia = AsistenciaAlumno(
                            alumno=alumno,
                            fecha=fecha_actual,
                            estado=estado,
                            hora=hora_referencia,
                        )
                        asistencia.save()
                        asistencias_creadas += 1

                        estado_display = "PRESENTE" if estado == "P" else "FALTA"
                        print(
                            f"   {fecha_actual} - {grupo_lab.grupo_teoria.curso.nombre} (Lab) - {estado_display}"
                        )

                    except Exception as e:
                        print(f"   ❌ Error generando asistencia {fecha_actual}: {e}")
                        continue

        fecha_actual += timedelta(days=1)

    print(f"✅ Total asistencias generadas: {asistencias_creadas}")
    return asistencias_creadas


def visualizar_asistencias_alumno(request):
    # 1. Obtener el alumno logueado
    if "email" not in request.session:
        return redirect("login")

    email = request.session["email"]

    try:
        alumno = Alumno.objects.get(email=email)
    except Alumno.DoesNotExist:
        return redirect("login")
    except Alumno.MultipleObjectsReturned:
        alumno = Alumno.objects.filter(email=email).first()

    # 2. Obtener cursos matriculados (tanto de curso como de laboratorio)
    cursos_matriculados = obtener_cursos_alumno(alumno)

    # 3. Procesar filtro por curso si se envió
    curso_seleccionado_id = request.GET.get("curso_id")
    curso_seleccionado = None
    asistencias_curso = []
    estadisticas_curso = {}

    if curso_seleccionado_id:
        try:
            curso_seleccionado = Curso.objects.get(id=curso_seleccionado_id)
            asistencias_curso = obtener_asistencias_curso(alumno, curso_seleccionado)
            estadisticas_curso = calcular_estadisticas_asistencias(asistencias_curso)
        except Curso.DoesNotExist:
            pass

    # 4. Preparar contexto
    context = {
        "alumno": alumno,
        "cursos_matriculados": cursos_matriculados,
        "curso_seleccionado": curso_seleccionado,
        "asistencias_curso": asistencias_curso,
        "estadisticas_curso": estadisticas_curso,
        "hoy": datetime.now().date(),  # Fecha actual corregida para 2025
        "anio_actual": 2025,
    }

    return render(request, "siscad/alumno/visualizar_asistencias_alumno.html", context)


def obtener_cursos_alumno(alumno):
    """
    Obtiene todos los cursos en los que el alumno está matriculado
    (tanto de MatriculaCurso como de MatriculaLaboratorio)
    """
    cursos = []

    # Cursos de teoría/práctica
    matriculas_curso = MatriculaCurso.objects.filter(alumno=alumno).select_related(
        "curso"
    )
    for matricula in matriculas_curso:
        cursos.append(
            {
                "id": matricula.curso.id,
                "nombre": matricula.curso.nombre,
                "tipo": "Curso",
                "turno": matricula.turno,
                "matricula_id": matricula.id,
            }
        )

    # Cursos de laboratorio (sin duplicados con los de teoría)
    matriculas_lab = MatriculaLaboratorio.objects.filter(alumno=alumno).select_related(
        "grupo_laboratorio__grupo_teoria__curso"
    )

    for matricula in matriculas_lab:
        curso = matricula.grupo_laboratorio.grupo_teoria.curso
        # Solo agregar si no está ya en la lista
        if not any(c["id"] == curso.id for c in cursos):
            cursos.append(
                {
                    "id": curso.id,
                    "nombre": curso.nombre,
                    "tipo": "Laboratorio",
                    "grupo_lab": matricula.grupo_laboratorio.grupo,
                    "matricula_id": matricula.id,
                }
            )

    return cursos


def obtener_asistencias_curso(alumno, curso):
    """
    Obtiene todas las asistencias del alumno para un curso específico
    """
    # Obtener asistencias relacionadas con este curso
    asistencias = (
        AsistenciaAlumno.objects.filter(alumno=alumno)
        .filter(
            Q(hora__grupo_teoria__curso=curso)
            | Q(hora__grupo_practica__grupo_teoria__curso=curso)
            | Q(hora__grupo_laboratorio__grupo_teoria__curso=curso)
        )
        .select_related(
            "hora__grupo_teoria__curso",
            "hora__grupo_practica__grupo_teoria__curso",
            "hora__grupo_laboratorio__grupo_teoria__curso",
        )
        .order_by("-fecha", "hora__hora_inicio")
    )

    # Formatear los datos para el template
    asistencias_formateadas = []
    for asistencia in asistencias:
        # Determinar tipo de clase y información
        tipo_clase = "Desconocido"
        detalle_clase = ""

        if asistencia.hora.grupo_teoria:
            tipo_clase = "Teoría"
            detalle_clase = f"T-{asistencia.hora.grupo_teoria.turno}"
        elif asistencia.hora.grupo_practica:
            tipo_clase = "Práctica"
            detalle_clase = f"P-{asistencia.hora.grupo_practica.turno}"
        elif asistencia.hora.grupo_laboratorio:
            tipo_clase = "Laboratorio"
            detalle_clase = f"L-{asistencia.hora.grupo_laboratorio.grupo}"

        asistencias_formateadas.append(
            {
                "fecha": asistencia.fecha,
                "dia_semana": asistencia.fecha.strftime("%A"),
                "hora_inicio": asistencia.hora.hora_inicio.strftime("%H:%M"),
                "hora_fin": asistencia.hora.hora_fin.strftime("%H:%M"),
                "tipo_clase": tipo_clase,
                "detalle_clase": detalle_clase,
                "estado": asistencia.estado,
                "estado_display": asistencia.get_estado_display(),
                "aula": asistencia.hora.aula.nombre
                if asistencia.hora.aula
                else "Sin aula",
                "es_pasado": asistencia.fecha < datetime.now().date(),
            }
        )

    return asistencias_formateadas


def calcular_estadisticas_asistencias(asistencias):
    """
    Calcula estadísticas de asistencias para un curso
    """
    if not asistencias:
        return {}

    total = len(asistencias)
    presentes = len([a for a in asistencias if a["estado"] == "P"])
    faltas = len([a for a in asistencias if a["estado"] == "F"])

    # Separar por tipo de clase
    teorias = [a for a in asistencias if a["tipo_clase"] == "Teoría"]
    practicas = [a for a in asistencias if a["tipo_clase"] == "Práctica"]
    laboratorios = [a for a in asistencias if a["tipo_clase"] == "Laboratorio"]

    # Calcular porcentajes
    porcentaje_asistencia = (presentes / total * 100) if total > 0 else 0

    return {
        "total": total,
        "presentes": presentes,
        "faltas": faltas,
        "porcentaje_asistencia": round(porcentaje_asistencia, 1),
        "teorias_total": len(teorias),
        "teorias_presentes": len([t for t in teorias if t["estado"] == "P"]),
        "practicas_total": len(practicas),
        "practicas_presentes": len([p for p in practicas if p["estado"] == "P"]),
        "laboratorios_total": len(laboratorios),
        "laboratorios_presentes": len([l for l in laboratorios if l["estado"] == "P"]),
    }


# =======================Vista de Profesor====================================================
def inicio_profesor(request):
    rol = request.session.get("rol")

    if rol != "Profesor":
        request.session["rol"] = "Ninguno"
        return redirect("login")

    nombre = request.session.get("nombre")
    return render(request, "siscad/profesor/menu.html", {"nombre": nombre, "rol": rol})


def visualizar_horario_profesor(request):
    # 1. Obtener el profesor logueado usando el email de la sesión
    if "email" not in request.session:
        return redirect("login")

    email = request.session["email"]

    try:
        profesor = Profesor.objects.get(email=email)
    except Profesor.DoesNotExist:
        return redirect("login")
    except Profesor.MultipleObjectsReturned:
        profesor = Profesor.objects.filter(email=email).first()

    print(f"DEBUG: Profesor encontrado: {profesor.nombre}")

    # 2. Obtener todos los horarios del profesor (teoría, práctica, laboratorio)
    horarios = (
        Hora.objects.select_related(
            "aula",
            "grupo_teoria__curso",
            "grupo_practica__grupo_teoria__curso",
            "grupo_laboratorio__grupo_teoria__curso",
        )
        .filter(
            Q(grupo_teoria__profesor=profesor)
            | Q(grupo_practica__profesor=profesor)
            | Q(grupo_laboratorio__profesor=profesor)
        )
        .order_by("dia", "hora_inicio")
    )

    print(f"DEBUG: Horarios encontrados para el profesor: {horarios.count()}")

    # Debug detallado de horarios
    for h in horarios:
        if h.grupo_teoria:
            tipo = "Teoría"
            curso_nombre = h.grupo_teoria.curso.nombre
            grupo_info = f"T-{h.grupo_teoria.turno}"
        elif h.grupo_practica:
            tipo = "Práctica"
            curso_nombre = h.grupo_practica.grupo_teoria.curso.nombre
            grupo_info = f"P-{h.grupo_practica.turno}"
        elif h.grupo_laboratorio:
            tipo = "Laboratorio"
            curso_nombre = h.grupo_laboratorio.grupo_teoria.curso.nombre
            grupo_info = f"L-{h.grupo_laboratorio.grupo}"
        else:
            tipo = "Otro"
            curso_nombre = "Desconocido"
            grupo_info = ""

        print(
            f"DEBUG Horario Profesor: {h.dia} {h.hora_inicio}-{h.hora_fin} - {tipo}: {curso_nombre} {grupo_info} - Aula: {h.aula.nombre if h.aula else 'Sin aula'}"
        )

    # 3. Construir estructura para mostrar
    dias_lista = [
        ("L", "Lunes"),
        ("M", "Martes"),
        ("X", "Miércoles"),
        ("J", "Jueves"),
        ("V", "Viernes"),
    ]

    # Crear estructura de datos
    tabla_horarios = {}
    for h in horarios:
        bloque = f"{h.hora_inicio.strftime('%H:%M')} - {h.hora_fin.strftime('%H:%M')}"
        dia = h.dia

        # Usar "Horario del Profesor" como clave única
        aula_key = "Horario del Profesor"

        if aula_key not in tabla_horarios:
            tabla_horarios[aula_key] = {}

        if bloque not in tabla_horarios[aula_key]:
            tabla_horarios[aula_key][bloque] = {d: "" for d, _ in dias_lista}

        # Construir información del curso
        if h.grupo_teoria:
            curso = h.grupo_teoria.curso.nombre
            grupo = f"T-{h.grupo_teoria.turno}"
            tipo_info = "Teoría"
        elif h.grupo_practica:
            curso = h.grupo_practica.grupo_teoria.curso.nombre
            grupo = f"P-{h.grupo_practica.turno}"
            tipo_info = "Práctica"
        elif h.grupo_laboratorio:
            curso = h.grupo_laboratorio.grupo_teoria.curso.nombre
            grupo = f"L-{h.grupo_laboratorio.grupo}"
            tipo_info = "Laboratorio"
        else:
            curso = "Sin asignar"
            grupo = ""
            tipo_info = ""

        aula_info = f" ({h.aula.nombre})" if h.aula else ""
        info_curso = f"{curso} {grupo} - {tipo_info}{aula_info}"

        tabla_horarios[aula_key][bloque][dia] = info_curso

    # Ordenar por hora
    for aula in tabla_horarios:
        tabla_horarios[aula] = dict(
            sorted(tabla_horarios[aula].items(), key=lambda x: x[0])
        )

    # 4. Obtener estadísticas del profesor
    estadisticas = {
        "total_horarios": horarios.count(),
        "total_teoria": horarios.filter(grupo_teoria__profesor=profesor).count(),
        "total_practica": horarios.filter(grupo_practica__profesor=profesor).count(),
        "total_laboratorio": horarios.filter(
            grupo_laboratorio__profesor=profesor
        ).count(),
        "cursos_unicos": len(
            set(
                [h.grupo_teoria.curso_id for h in horarios if h.grupo_teoria]
                + [
                    h.grupo_practica.grupo_teoria.curso_id
                    for h in horarios
                    if h.grupo_practica
                ]
                + [
                    h.grupo_laboratorio.grupo_teoria.curso_id
                    for h in horarios
                    if h.grupo_laboratorio
                ]
            )
        ),
        "reservas_disponibles": profesor.cantidad_reservas,
    }

    # 5. Crear la estructura final
    context = {
        "profesor": profesor,
        "dias_lista": dias_lista,
        "tabla_horarios": {
            aula: [
                {
                    "bloque": bloque,
                    "dias": [(dia, dias_data[dia]) for dia, _ in dias_lista],
                }
                for bloque, dias_data in bloques.items()
            ]
            for aula, bloques in tabla_horarios.items()
        },
        "estadisticas": estadisticas,
    }

    return render(request, "siscad/profesor/visualizar_horario_profesor.html", context)


from django.shortcuts import render, redirect
from django.db.models import Q
from datetime import datetime


def visualizar_asistencias_profesor(request):
    # 1. Obtener el profesor logueado
    if "email" not in request.session:
        return redirect("login")

    email = request.session["email"]

    try:
        profesor = Profesor.objects.get(email=email)
    except Profesor.DoesNotExist:
        return redirect("login")
    except Profesor.MultipleObjectsReturned:
        profesor = Profesor.objects.filter(email=email).first()

    # 2. Obtener cursos que enseña el profesor (teoría, práctica, laboratorio)
    cursos_ensenados = obtener_cursos_profesor(profesor)

    # 3. Procesar filtro por curso si se envió
    curso_seleccionado_id = request.GET.get("curso_id")
    curso_seleccionado = None
    asistencias_curso = []
    estadisticas_curso = {}

    if curso_seleccionado_id:
        try:
            curso_seleccionado = Curso.objects.get(id=curso_seleccionado_id)
            asistencias_curso = obtener_asistencias_curso_profesor(
                profesor, curso_seleccionado
            )
            estadisticas_curso = calcular_estadisticas_asistencias_profesor(
                asistencias_curso
            )
        except Curso.DoesNotExist:
            pass

    # 4. Preparar contexto
    context = {
        "profesor": profesor,
        "cursos_ensenados": cursos_ensenados,
        "curso_seleccionado": curso_seleccionado,
        "asistencias_curso": asistencias_curso,
        "estadisticas_curso": estadisticas_curso,
        "hoy": datetime.now().date(),
    }

    return render(
        request, "siscad/profesor/visualizar_asistencias_profesor.html", context
    )


def obtener_cursos_profesor(profesor):
    """
    Obtiene todos los cursos que enseña el profesor (teoría, práctica, laboratorio)
    """
    cursos = []

    # Cursos de teoría
    grupos_teoria = GrupoTeoria.objects.filter(profesor=profesor).select_related(
        "curso"
    )
    for grupo in grupos_teoria:
        cursos.append(
            {
                "id": grupo.curso.id,
                "nombre": grupo.curso.nombre,
                "tipo": "Teoría",
                "turno": grupo.turno,
                "grupo_id": grupo.id,
            }
        )

    # Cursos de práctica
    grupos_practica = GrupoPractica.objects.filter(profesor=profesor).select_related(
        "grupo_teoria__curso"
    )
    for grupo in grupos_practica:
        curso = grupo.grupo_teoria.curso
        # Solo agregar si no está ya en la lista
        if not any(c["id"] == curso.id and c["tipo"] == "Práctica" for c in cursos):
            cursos.append(
                {
                    "id": curso.id,
                    "nombre": curso.nombre,
                    "tipo": "Práctica",
                    "turno": grupo.turno,
                    "grupo_id": grupo.id,
                }
            )

    # Cursos de laboratorio
    grupos_lab = GrupoLaboratorio.objects.filter(profesor=profesor).select_related(
        "grupo_teoria__curso"
    )
    for grupo in grupos_lab:
        curso = grupo.grupo_teoria.curso
        # Solo agregar si no está ya en la lista
        if not any(c["id"] == curso.id and c["tipo"] == "Laboratorio" for c in cursos):
            cursos.append(
                {
                    "id": curso.id,
                    "nombre": curso.nombre,
                    "tipo": "Laboratorio",
                    "grupo_lab": grupo.grupo,
                    "grupo_id": grupo.id,
                }
            )

    return cursos


def obtener_asistencias_curso_profesor(profesor, curso):
    """
    Obtiene todas las asistencias del profesor para un curso específico
    """
    # Obtener asistencias relacionadas con este curso
    asistencias = (
        AsistenciaProfesor.objects.filter(profesor=profesor)
        .filter(
            Q(hora__grupo_teoria__curso=curso)
            | Q(hora__grupo_practica__grupo_teoria__curso=curso)
            | Q(hora__grupo_laboratorio__grupo_teoria__curso=curso)
        )
        .select_related(
            "hora__grupo_teoria__curso",
            "hora__grupo_practica__grupo_teoria__curso",
            "hora__grupo_laboratorio__grupo_teoria__curso",
        )
        .order_by("-fecha", "hora__hora_inicio")
    )

    # Formatear los datos para el template
    asistencias_formateadas = []
    for asistencia in asistencias:
        # Determinar tipo de clase y información
        tipo_clase = "Desconocido"
        detalle_clase = ""

        if asistencia.hora.grupo_teoria:
            tipo_clase = "Teoría"
            detalle_clase = f"T-{asistencia.hora.grupo_teoria.turno}"
        elif asistencia.hora.grupo_practica:
            tipo_clase = "Práctica"
            detalle_clase = f"P-{asistencia.hora.grupo_practica.turno}"
        elif asistencia.hora.grupo_laboratorio:
            tipo_clase = "Laboratorio"
            detalle_clase = f"L-{asistencia.hora.grupo_laboratorio.grupo}"

        asistencias_formateadas.append(
            {
                "fecha": asistencia.fecha,
                "dia_semana": asistencia.fecha.strftime("%A"),
                "hora_inicio": asistencia.hora.hora_inicio.strftime("%H:%M"),
                "hora_fin": asistencia.hora.hora_fin.strftime("%H:%M"),
                "tipo_clase": tipo_clase,
                "detalle_clase": detalle_clase,
                "estado": asistencia.estado,
                "estado_display": asistencia.get_estado_display(),
                "aula": asistencia.hora.aula.nombre
                if asistencia.hora.aula
                else "Sin aula",
                "es_pasado": asistencia.fecha < datetime.now().date(),
            }
        )

    return asistencias_formateadas


def calcular_estadisticas_asistencias_profesor(asistencias):
    """
    Calcula estadísticas de asistencias para un curso del profesor
    """
    if not asistencias:
        return {}

    total = len(asistencias)
    presentes = len([a for a in asistencias if a["estado"] == "P"])
    faltas = len([a for a in asistencias if a["estado"] == "F"])

    # Separar por tipo de clase
    teorias = [a for a in asistencias if a["tipo_clase"] == "Teoría"]
    practicas = [a for a in asistencias if a["tipo_clase"] == "Práctica"]
    laboratorios = [a for a in asistencias if a["tipo_clase"] == "Laboratorio"]

    # Calcular porcentajes
    porcentaje_asistencia = (presentes / total * 100) if total > 0 else 0

    return {
        "total": total,
        "presentes": presentes,
        "faltas": faltas,
        "porcentaje_asistencia": round(porcentaje_asistencia, 1),
        "teorias_total": len(teorias),
        "teorias_presentes": len([t for t in teorias if t["estado"] == "P"]),
        "practicas_total": len(practicas),
        "practicas_presentes": len([p for p in practicas if p["estado"] == "P"]),
        "laboratorios_total": len(laboratorios),
        "laboratorios_presentes": len([l for l in laboratorios if l["estado"] == "P"]),
    }


# =======================Vista de Admin====================================================


def inicio_admin(request):
    return render(request, "siscad/admin/menu.html")
