from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
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
        print(f"DEBUG - Curso: {curso.nombre}")
        print(f"DEBUG - Promedio parcial: {promedio_parcial}")
        print(f"DEBUG - Promedio continua: {promedio_continua}")
        print(f"DEBUG - Promedio final: {promedio_final}")
        print(f"DEBUG - Notas parciales: {len(notas_parciales)}")
        print(f"DEBUG - Notas continuas: {len(notas_continuas)}")

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


# =======================Vista de Profesor====================================================
def inicio_profesor(request):
    return render(request, "siscad/profesor/menu.html")


# =======================Vista de Admin====================================================
def inicio_admin(request):
    return render(request, "siscad/admin/menu.html")
