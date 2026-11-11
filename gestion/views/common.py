from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render

def acceso(permiso):
    """Primero exige sesión; después comprueba el permiso en el servidor."""
    def decorar(vista):
        return login_required(permission_required(permiso, raise_exception=True)(vista))
    return decorar

def formulario(request, form, titulo, destino, antes_de_guardar=None):
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                objeto = form.save(commit=False)
                if antes_de_guardar:
                    antes_de_guardar(objeto)
                objeto.full_clean()
                # Una edición no debe sobrescribir contadores ni campos internos.
                if objeto.pk:
                    objeto.save(update_fields=form._meta.fields)
                else:
                    objeto.save()
        except ValidationError as error:
            form.add_error(None, "; ".join(error.messages))
        except IntegrityError:
            form.add_error(None, "Los datos han cambiado o ya existe este registro. Revisa y vuelve a intentarlo.")
        else:
            messages.success(request, "Datos guardados correctamente.")
            return redirect(destino)
    return render(request, "gestion/formulario.html", {"form": form, "titulo": titulo, "destino": destino})
