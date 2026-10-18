import re
from django import forms
from .models import Vehiculo, Apartamento


class VehiculoForm(forms.ModelForm):
    """Formulario de registro de vehículos (RF-11, RF-12)."""

    tipo = forms.ChoiceField(
        choices=[('CARRO', 'Carro'), ('MOTO', 'Moto'), ('BICICLETA', 'Bicicleta')]
    )

    class Meta:
        model = Vehiculo
        fields = ['id_apartamento', 'placa', 'marca', 'modelo', 'color', 'tipo']
        labels = {
            'id_apartamento': 'Apartamento',
            'placa': 'Placa',
            'marca': 'Marca',
            'modelo': 'Modelo',
            'color': 'Color',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Muestra "Apto 101 - Carlos Pérez" en lugar de "Apartamento object (1)"
        self.fields['id_apartamento'].queryset = Apartamento.objects.filter(estado=True).order_by('numero')
        self.fields['id_apartamento'].label_from_instance = (
            lambda a: f'Apto {a.numero} - {a.propietario}'
        )

    def clean_placa(self):
        # La base de datos exige placa en mayúsculas, de 5 a 10 caracteres alfanuméricos
        placa = self.cleaned_data['placa'].upper().strip()
        if not re.fullmatch(r'[A-Z0-9]{5,10}', placa):
            raise forms.ValidationError(
                'La placa debe tener entre 5 y 10 caracteres, solo letras y números.'
            )
        return placa
