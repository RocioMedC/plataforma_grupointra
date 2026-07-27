from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model

from .duplicados import existe_duplicado
from .models import (
    CategoriaEgreso, ConceptoIngreso, ConceptoNominaAcademia, Donativo, Egreso,
    Honorario, Ingreso, LineaNominaSemanal, Maestro, NominaAcademia, Tabulador,
    TabuladorAcademia,
)

User = get_user_model()

_ATTRS = {'class': 'fin-input'}


def _opciones_concepto_ingreso():
    """Conceptos fijos de Ingreso + los agregados desde Configuración."""
    return list(Ingreso.Concepto.choices) + [
        (c.nombre, c.nombre) for c in ConceptoIngreso.objects.filter(activo=True)
    ]


def _opciones_categoria_egreso():
    """Categorías fijas de Egreso + las agregadas desde Configuración."""
    return list(Egreso.Categoria.choices) + [
        (c.nombre, c.nombre) for c in CategoriaEgreso.objects.filter(activo=True)
    ]


class IngresoForm(forms.ModelForm):
    class Meta:
        model = Ingreso
        fields = ['concepto', 'terapeuta', 'persona', 'monto', 'monto_pagado', 'estatus', 'fecha']
        widgets = {
            'concepto': forms.Select(attrs=_ATTRS),
            'terapeuta': forms.Select(attrs=_ATTRS),
            'persona': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Nombre del alumno o paciente'}),
            'monto': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0.01'}),
            'monto_pagado': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0'}),
            'estatus': forms.Select(attrs=_ATTRS),
            'fecha': forms.DateInput(attrs={**_ATTRS, 'type': 'date'}),
        }
        labels = {'monto_pagado': 'Cuánto se ha cobrado ya (solo si es Parcial)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['concepto'].choices = _opciones_concepto_ingreso()
        self.fields['terapeuta'].queryset = User.objects.filter(
            groups__name='Terapeutas'
        ).order_by('first_name', 'username')
        self.fields['terapeuta'].required = False
        self.fields['monto_pagado'].required = False

    def _get_validation_exclusions(self):
        # Sin esto, Django revalida 'concepto' en Model.full_clean() contra
        # las choices FIJAS del modelo (Ingreso.Concepto), ignorando las
        # opciones agregadas desde Configuración que sí acabamos de aceptar
        # arriba — el resultado era que un concepto agregado en Configuración
        # aparecía en el selector pero el formulario lo rechazaba igual con
        # "Select a valid choice" al intentar guardarlo.
        return super()._get_validation_exclusions() | {'concepto'}

    def clean_monto(self):
        monto = self.cleaned_data['monto']
        if monto <= Decimal('0'):
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return monto

    def clean(self):
        datos = super().clean()
        monto, monto_pagado = datos.get('monto'), datos.get('monto_pagado') or Decimal('0')
        if monto is not None and monto_pagado > monto:
            raise forms.ValidationError('Lo cobrado no puede ser mayor que el monto total.')
        datos['monto_pagado'] = monto_pagado
        return datos


class TabuladorForm(forms.ModelForm):
    class Meta:
        model = Tabulador
        fields = ['categoria', 'pago_base', 'umbral_pacientes_semana', 'monto_bono', 'vigente_desde']
        widgets = {
            'categoria': forms.Select(attrs=_ATTRS),
            'pago_base': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0.01'}),
            'umbral_pacientes_semana': forms.NumberInput(attrs={**_ATTRS, 'min': '0'}),
            'monto_bono': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0'}),
            'vigente_desde': forms.DateInput(attrs={**_ATTRS, 'type': 'date'}),
        }


class HonorarioForm(forms.ModelForm):
    class Meta:
        model = Honorario
        fields = ['terapeuta', 'tabulador', 'periodo_mes', 'periodo_anio', 'num_pacientes', 'estatus']
        widgets = {
            'terapeuta': forms.Select(attrs=_ATTRS),
            'tabulador': forms.Select(attrs=_ATTRS),
            'periodo_mes': forms.Select(choices=[(m, n) for m, n in [
                (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'), (5, 'Mayo'), (6, 'Junio'),
                (7, 'Julio'), (8, 'Agosto'), (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
            ]], attrs=_ATTRS),
            'periodo_anio': forms.NumberInput(attrs={**_ATTRS, 'min': '2020'}),
            'num_pacientes': forms.NumberInput(attrs={**_ATTRS, 'min': '0'}),
            'estatus': forms.Select(attrs=_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['terapeuta'].queryset = User.objects.filter(
            groups__name='Terapeutas'
        ).order_by('first_name', 'username')

    def clean(self):
        datos = super().clean()
        terapeuta, mes, anio = datos.get('terapeuta'), datos.get('periodo_mes'), datos.get('periodo_anio')
        if terapeuta and mes and anio and existe_duplicado(Honorario, terapeuta=terapeuta, periodo_mes=mes, periodo_anio=anio):
            raise forms.ValidationError(
                f'Ya existe un honorario de {terapeuta} para {mes}/{anio}. Si necesitas corregirlo, usa un Ajuste.'
            )
        return datos


class DonativoForm(forms.ModelForm):
    class Meta:
        model = Donativo
        fields = [
            'donante_nombre', 'donante_rfc', 'tipo', 'monto', 'folio_cfdi',
            'estatus_cfdi', 'archivo_xml', 'archivo_pdf', 'fecha',
        ]
        widgets = {
            'donante_nombre': forms.TextInput(attrs=_ATTRS),
            'donante_rfc': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'RFC (opcional)'}),
            'tipo': forms.Select(attrs=_ATTRS),
            'monto': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0.01'}),
            'folio_cfdi': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Folio CFDI (opcional)'}),
            'estatus_cfdi': forms.Select(attrs=_ATTRS),
            'archivo_xml': forms.ClearableFileInput(attrs=_ATTRS),
            'archivo_pdf': forms.ClearableFileInput(attrs=_ATTRS),
            'fecha': forms.DateInput(attrs={**_ATTRS, 'type': 'date'}),
        }

    def clean_monto(self):
        monto = self.cleaned_data['monto']
        if monto <= Decimal('0'):
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return monto


class ReporteRecepcionUploadForm(forms.Form):
    archivo = forms.FileField(
        label='Reporte General (Excel)',
        widget=forms.ClearableFileInput(attrs={**_ATTRS, 'accept': '.xlsx'}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('El archivo debe ser un Excel (.xlsx) exportado del Reporte General.')
        return archivo


_MESES = [
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'), (5, 'Mayo'), (6, 'Junio'),
    (7, 'Julio'), (8, 'Agosto'), (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]


class NominaAcademiaCaptureForm(forms.Form):
    maestro = forms.ModelChoiceField(
        queryset=Maestro.objects.filter(activo=True), widget=forms.Select(attrs=_ATTRS),
    )
    periodo_mes = forms.ChoiceField(choices=_MESES, widget=forms.Select(attrs=_ATTRS))
    periodo_anio = forms.IntegerField(widget=forms.NumberInput(attrs={**_ATTRS, 'min': '2020'}))
    metodo_pago = forms.ChoiceField(
        choices=[('', 'Pendiente de asignar')] + list(NominaAcademia.MetodoPago.choices),
        required=False, widget=forms.Select(attrs=_ATTRS),
    )
    cantidad_horas_clase = forms.DecimalField(
        label='Horas clase', required=False, min_value=Decimal('0'),
        widget=forms.NumberInput(attrs={**_ATTRS, 'step': '0.5', 'placeholder': '0'}),
    )
    cantidad_supervision = forms.DecimalField(
        label='Supervisión', required=False, min_value=Decimal('0'),
        widget=forms.NumberInput(attrs={**_ATTRS, 'step': '0.5', 'placeholder': '0'}),
    )
    cantidad_mesa_trabajo = forms.DecimalField(
        label='Mesa de trabajo', required=False, min_value=Decimal('0'),
        widget=forms.NumberInput(attrs={**_ATTRS, 'step': '0.5', 'placeholder': '0'}),
    )
    concepto_manual_descripcion = forms.CharField(
        label='Concepto manual autorizado', required=False,
        widget=forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Descripción (opcional)'}),
    )
    concepto_manual_monto = forms.DecimalField(
        label='Monto del concepto manual', required=False, min_value=Decimal('0'),
        widget=forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'placeholder': '0.00'}),
    )

    def clean(self):
        datos = super().clean()
        cantidades = [
            datos.get('cantidad_horas_clase'), datos.get('cantidad_supervision'), datos.get('cantidad_mesa_trabajo'),
        ]
        manual_desc = datos.get('concepto_manual_descripcion')
        manual_monto = datos.get('concepto_manual_monto')
        if not any(cantidades) and not (manual_desc and manual_monto):
            raise forms.ValidationError(
                'Captura al menos un concepto (horas clase, supervisión, mesa de trabajo, o un concepto manual con descripción y monto).'
            )
        if bool(manual_desc) != bool(manual_monto):
            raise forms.ValidationError(
                'El concepto manual autorizado y el monto del concepto manual deben contar con una descripción.'
            )
        return datos

    def cantidades(self):
        return {
            ConceptoNominaAcademia.Concepto.HORAS_CLASE: self.cleaned_data.get('cantidad_horas_clase'),
            ConceptoNominaAcademia.Concepto.SUPERVISION: self.cleaned_data.get('cantidad_supervision'),
            ConceptoNominaAcademia.Concepto.MESA_TRABAJO: self.cleaned_data.get('cantidad_mesa_trabajo'),
        }


class MaestroForm(forms.ModelForm):
    class Meta:
        model = Maestro
        fields = ['nombre', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Nombre del maestro'}),
        }


class TabuladorAcademiaForm(forms.ModelForm):
    class Meta:
        model = TabuladorAcademia
        fields = ['concepto', 'monto_unidad', 'vigente_desde']
        widgets = {
            'concepto': forms.Select(attrs=_ATTRS),
            'monto_unidad': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0.01'}),
            'vigente_desde': forms.DateInput(attrs={**_ATTRS, 'type': 'date'}),
        }


class AjusteForm(forms.Form):
    # Sin slice: ModelChoiceField valida la selección con queryset.get(pk=...),
    # y Django no permite filtrar/get sobre un queryset ya recortado con [:n].
    honorario = forms.ModelChoiceField(
        queryset=Honorario.objects.select_related('terapeuta').order_by('-periodo_anio', '-periodo_mes'),
        required=False, label='Honorario a corregir', widget=forms.Select(attrs=_ATTRS),
    )
    nomina_academia = forms.ModelChoiceField(
        queryset=NominaAcademia.objects.select_related('maestro').order_by('-periodo_anio', '-periodo_mes'),
        required=False, label='Nómina Academia a corregir', widget=forms.Select(attrs=_ATTRS),
    )
    egreso = forms.ModelChoiceField(
        queryset=Egreso.objects.order_by('-fecha'),
        required=False, label='Egreso a corregir', widget=forms.Select(attrs=_ATTRS),
    )
    motivo = forms.CharField(widget=forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Motivo del ajuste'}))
    diferencia = forms.DecimalField(
        help_text='Positiva si se debe un monto adicional; negativa solo queda registrada, sin generar egreso.',
        widget=forms.NumberInput(attrs={**_ATTRS, 'step': '0.01'}),
    )

    def clean(self):
        datos = super().clean()
        elegidos = [v for v in (datos.get('honorario'), datos.get('nomina_academia'), datos.get('egreso')) if v]
        if len(elegidos) != 1:
            raise forms.ValidationError(
                'Selecciona exactamente un registro (Honorario, Nómina Academia o Egreso) para ajustar.'
            )
        return datos

    def registro_elegido(self):
        for campo, modelo in (('honorario', Honorario), ('nomina_academia', NominaAcademia), ('egreso', Egreso)):
            valor = self.cleaned_data.get(campo)
            if valor:
                return modelo, valor.pk
        return None, None


class ConceptoIngresoForm(forms.ModelForm):
    class Meta:
        model = ConceptoIngreso
        fields = ['nombre', 'activo']
        widgets = {'nombre': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Nombre del concepto'})}


class CategoriaEgresoForm(forms.ModelForm):
    class Meta:
        model = CategoriaEgreso
        fields = ['nombre', 'activo']
        widgets = {'nombre': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Nombre de la categoría'})}


class EgresoForm(forms.ModelForm):
    class Meta:
        model = Egreso
        fields = ['concepto', 'categoria', 'persona', 'monto', 'metodo_pago', 'estatus', 'fecha']
        widgets = {
            'concepto': forms.TextInput(attrs=_ATTRS),
            'categoria': forms.Select(attrs=_ATTRS),
            'persona': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Terapeuta o proveedor'}),
            'monto': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0.01'}),
            'metodo_pago': forms.Select(attrs=_ATTRS),
            'estatus': forms.Select(attrs=_ATTRS),
            'fecha': forms.DateInput(attrs={**_ATTRS, 'type': 'date'}),
        }

    # La regla general de la sección 2 del documento pide impedir duplicidad
    # por periodo/persona/concepto. Para un egreso capturado a mano no se
    # puede bloquear en seco (dos gastos idénticos el mismo día existen), así
    # que se usa la otra salida que el propio documento contempla: "bloquear
    # o pedir confirmacion".
    confirmar_duplicado = forms.BooleanField(
        required=False, label='Sí, es un movimiento distinto al que ya está capturado',
        widget=forms.CheckboxInput(attrs={'class': 'fin-check'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].choices = _opciones_categoria_egreso()

    def _get_validation_exclusions(self):
        # Mismo problema y misma razón que IngresoForm._get_validation_exclusions:
        # sin esto, una categoría agregada desde Configuración aparecía en el
        # selector pero el formulario la rechazaba con "Select a valid choice"
        # porque Model.full_clean() revalidaba contra las choices fijas de
        # Egreso.Categoria.
        return super()._get_validation_exclusions() | {'categoria'}

    def clean_monto(self):
        monto = self.cleaned_data['monto']
        if monto <= Decimal('0'):
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return monto

    def clean(self):
        datos = super().clean()
        if datos.get('confirmar_duplicado'):
            return datos
        persona, concepto = datos.get('persona'), datos.get('concepto')
        monto, fecha = datos.get('monto'), datos.get('fecha')
        if all([concepto, monto, fecha]) and existe_duplicado(
            Egreso, persona=persona or '', concepto=concepto, monto=monto, fecha=fecha,
        ):
            raise forms.ValidationError(
                f'Ya hay un egreso idéntico capturado el {fecha:%d/%m/%Y} '
                f'({concepto}, {monto}). Si de verdad es otro movimiento, marca la casilla '
                'de confirmación; si es una corrección del anterior, regístrala como Ajuste.'
            )
        return datos


class LineaNominaManualForm(forms.ModelForm):
    """Captura de una persona en una nómina quincenal o administrativa, que
    no viene de ConsultorioWeb (sección 4 del documento: la descarga debe
    poder ser semanal, quincenal, administrativa o de Academia)."""

    class Meta:
        model = LineaNominaSemanal
        fields = [
            'persona', 'tipo_persona', 'concepto', 'pago_base', 'vale_gasolina',
            'extras', 'metodo_pago', 'estatus_pago', 'observaciones',
        ]
        widgets = {
            'persona': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Nombre completo'}),
            'tipo_persona': forms.Select(attrs=_ATTRS),
            'concepto': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Pago a terapeuta, Prenómina quincenal, Pago administrativo...'}),
            'pago_base': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0'}),
            'vale_gasolina': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0'}),
            'extras': forms.NumberInput(attrs={**_ATTRS, 'step': '0.01', 'min': '0'}),
            'metodo_pago': forms.Select(attrs=_ATTRS),
            'estatus_pago': forms.Select(attrs=_ATTRS),
            'observaciones': forms.TextInput(attrs={**_ATTRS, 'placeholder': 'Opcional'}),
        }

    def __init__(self, *args, nomina=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.nomina = nomina

    def clean(self):
        datos = super().clean()
        total = (
            (datos.get('pago_base') or Decimal('0'))
            + (datos.get('vale_gasolina') or Decimal('0'))
            + (datos.get('extras') or Decimal('0'))
        )
        if total <= Decimal('0'):
            raise forms.ValidationError('Captura al menos un monto mayor a cero (pago base, vale o extra).')
        persona = datos.get('persona')
        if self.nomina and persona and existe_duplicado(
            LineaNominaSemanal, nomina=self.nomina, persona=persona,
        ):
            raise forms.ValidationError(
                f'{persona} ya está capturado en esta nómina. Edita su línea, o registra la '
                'diferencia como Ajuste si ya fue sellada.'
            )
        return datos
