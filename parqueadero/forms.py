from django import forms

from .models import TIPOS_VEHICULO, Apartamento, Espacio, Permiso, Usuario, Vehiculo


class BootstrapMixin:
    """Aplica las clases de Bootstrap a todos los campos."""

    def _estilizar(self):
        for campo in self.fields.values():
            w = campo.widget
            if isinstance(w, forms.CheckboxSelectMultiple):
                continue
            if isinstance(w, forms.CheckboxInput):
                w.attrs['class'] = 'form-check-input'
            elif isinstance(w, forms.Select):
                w.attrs['class'] = 'form-select'
            else:
                w.attrs['class'] = 'form-control'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estilizar()


class UsuarioForm(BootstrapMixin, forms.ModelForm):
    clave = forms.CharField(label='Contraseña', required=False, widget=forms.PasswordInput(render_value=False),
                            help_text='Obligatoria para usuarios nuevos. En edición, déjela vacía para no cambiarla.')
    desbloquear = forms.BooleanField(required=False, label='Desbloquear cuenta (reinicia los intentos fallidos)')

    class Meta:
        model = Usuario
        fields = ['nombre', 'cedula', 'telefono', 'correo', 'usuario', 'rol', 'apartamento', 'estado']

    def clean(self):
        datos = super().clean()
        if datos.get('rol') == 'RESIDENTE' and not datos.get('apartamento'):
            self.add_error('apartamento', 'Un residente debe pertenecer a un apartamento.')
        clave = datos.get('clave')
        if not self.instance.pk and not clave:
            self.add_error('clave', 'La contraseña es obligatoria para usuarios nuevos.')
        if clave and len(clave) < 8:
            self.add_error('clave', 'La contraseña debe tener al menos 8 caracteres.')
        return datos

    def save(self, commit=True):
        u = super().save(commit=False)
        if self.cleaned_data.get('clave'):
            u.set_password(self.cleaned_data['clave'])
        if self.cleaned_data.get('desbloquear'):
            u.intentos_fallidos = 0
            u.bloqueado_hasta = None
        if commit:
            u.save()
        return u


class ApartamentoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Apartamento
        fields = ['parqueadero', 'numero', 'propietario', 'max_vehiculos', 'estado']


class EspacioForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Espacio
        fields = ['parqueadero', 'apartamento', 'identificador', 'zona', 'tipo', 'estado']

    def clean(self):
        datos = super().clean()
        if self.instance.pk and datos.get('estado') != 'OCUPADO':
            if self.instance.esta_en_uso():
                raise forms.ValidationError('El espacio está ocupado en este momento; registre primero la salida.')
        return datos


class VehiculoForm(BootstrapMixin, forms.ModelForm):
    usuarios_autorizados = forms.ModelMultipleChoiceField(
        queryset=Usuario.objects.none(), required=False, widget=forms.CheckboxSelectMultiple,
        label='Usuarios autorizados para retirar el vehículo',
        help_text='Si no selecciona ninguno, se autorizan todos los residentes del apartamento.')

    class Meta:
        model = Vehiculo
        fields = ['apartamento', 'placa', 'marca', 'modelo', 'color', 'tipo', 'estado']

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        residentes = Usuario.objects.filter(rol='RESIDENTE', estado=True).select_related('apartamento')
        if usuario is not None and usuario.rol == 'RESIDENTE':
            self.fields['apartamento'].queryset = Apartamento.objects.filter(pk=usuario.apartamento_id)
            self.fields['apartamento'].empty_label = None
            self.fields['apartamento'].initial = usuario.apartamento_id
            residentes = residentes.filter(apartamento_id=usuario.apartamento_id)
        else:
            self.fields['apartamento'].queryset = Apartamento.objects.filter(estado=True)
        campo = self.fields['usuarios_autorizados']
        campo.queryset = residentes.order_by('apartamento__numero', 'nombre')
        campo.label_from_instance = lambda u: f'{u.nombre} (Apto {u.apartamento.numero})'
        if self.instance.pk:
            self.initial['usuarios_autorizados'] = list(
                self.instance.autorizados.values_list('pk', flat=True))

    def clean_placa(self):
        return Vehiculo.validar_placa(self.cleaned_data['placa'])

    def clean(self):
        datos = super().clean()
        apto = datos.get('apartamento')
        if apto:
            if datos.get('estado', True):
                if apto.cupo_disponible(excluir_pk=self.instance.pk) <= 0:      # RF-10
                    raise forms.ValidationError(
                        f'El apartamento {apto.numero} ya alcanzó su máximo de {apto.max_vehiculos} vehículo(s).')
            for u in datos.get('usuarios_autorizados') or []:
                if u.apartamento_id != apto.pk:
                    raise forms.ValidationError(f'{u.nombre} no pertenece al apartamento {apto.numero}.')
        return datos

    def save(self, commit=True):
        vehiculo = super().save(commit=True)
        vehiculo.autorizar_usuarios(self.cleaned_data.get('usuarios_autorizados') or [])
        return vehiculo


class VisitaForm(BootstrapMixin, forms.Form):
    apartamento = forms.ModelChoiceField(queryset=Apartamento.objects.none(), label='Apartamento visitado')
    nombre = forms.CharField(max_length=100, label='Nombre del visitante')
    documento = forms.CharField(max_length=20, label='Documento')
    placa = forms.CharField(max_length=10, required=False, label='Placa (si llega en vehículo)')
    tipo_vehiculo = forms.ChoiceField(choices=[('', '— Sin vehículo —')] + TIPOS_VEHICULO, required=False,
                                      label='Tipo de vehículo')
    tiempo_max_min = forms.IntegerField(min_value=15, initial=240, label='Tiempo máximo de permanencia (minutos)')

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None and usuario.rol == 'RESIDENTE':
            del self.fields['apartamento']
        else:
            self.fields['apartamento'].queryset = Apartamento.objects.filter(estado=True)

    def clean_placa(self):
        return Vehiculo.validar_placa(self.cleaned_data.get('placa'), obligatoria=False)

    def clean(self):
        datos = super().clean()
        if datos.get('placa') and not datos.get('tipo_vehiculo'):
            self.add_error('tipo_vehiculo', 'Indique el tipo de vehículo del visitante.')
        return datos


class PermisoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Permiso
        fields = ['usuario', 'fecha_inicio', 'fecha_vencimiento', 'motivo']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = Usuario.objects.filter(rol='RESIDENTE', estado=True).order_by('nombre')
        self.fields['fecha_vencimiento'].help_text = 'Déjela vacía para un permiso sin vencimiento.'


class FiltroForm(BootstrapMixin, forms.Form):
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    texto = forms.CharField(required=False, label='Placa / documento')
