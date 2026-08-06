from django.urls import reverse


def es_usuario_exclusivo_intera(user):
    """Indica si el usuario operativo sólo tiene acceso a Certificación."""

    if user.is_superuser:
        return False

    return set(
        user.groups.values_list(
            'name',
            flat=True,
        )
    ) == {'Certificación'}


def get_user_home_url(user):
    if es_usuario_exclusivo_intera(user):
        return reverse(
            'certificacion_intera:dashboard'
        )

    return reverse('dashboard')