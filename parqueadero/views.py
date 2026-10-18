from django.shortcuts import render, redirect
from .forms import VehiculoForm
from .models import Vehiculo


def vehiculos(request):
    """Lista los vehículos y permite registrar uno nuevo (RF-11)."""
    if request.method == 'POST':
        form = VehiculoForm(request.POST)
        if form.is_valid():
            vehiculo = form.save(commit=False)
            vehiculo.estado = True
            vehiculo.save()
            return redirect('vehiculos')
    else:
        form = VehiculoForm()

    lista = Vehiculo.objects.select_related('id_apartamento').order_by('placa')
    return render(request, 'parqueadero/vehiculos.html', {'form': form, 'vehiculos': lista})
