from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    STORAGES={
        'staticfiles': {
            'BACKEND': (
                'django.contrib.staticfiles.storage.'
                'StaticFilesStorage'
            ),
        },
    }
)
class InteraAccessTests(TestCase):
    def setUp(self):
        self.certificacion = Group.objects.get_or_create(
            name='Certificación'
        )[0]

        self.user = get_user_model().objects.create_user(
            username='coordinacion_prueba',
            password='clave-de-prueba-segura',
        )

        self.user.groups.add(self.certificacion)

    def test_usuario_exclusivo_entra_directamente_a_intera(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': self.user.username,
                'password': 'clave-de-prueba-segura',
            },
        )

        self.assertRedirects(
            response,
            reverse('certificacion_intera:dashboard'),
            fetch_redirect_response=False,
        )

    def test_usuario_exclusivo_no_puede_abrir_portal(self):
        self.client.force_login(self.user)

        self.assertEqual(
            self.client.get(
                reverse('dashboard')
            ).status_code,
            403,
        )

    def test_menu_y_destinos_de_intera_son_accesibles(self):
        self.client.force_login(self.user)

        for name in (
            'dashboard',
            'escuelas',
            'procesos',
            'participantes',
            'entrevistas',
            'seguimiento',
            'configuracion_general',
        ):
            response = self.client.get(
                reverse(
                    f'certificacion_intera:{name}'
                )
            )

            self.assertEqual(
                response.status_code,
                200,
            )

        content = self.client.get(
            reverse('certificacion_intera:dashboard')
        ).content.decode()

        for label in (
            'Panel',
            'Escuelas',
            'Procesos',
            'Participantes',
            'Entrevistas',
            'Seguimiento',
            'Configuración',
            'Cerrar sesión',
        ):
            self.assertIn(
                label,
                content,
            )

        self.assertIn(
            'aria-controls="intera-sidebar"',
            content,
        )

        self.assertNotIn(
            'Portal general',
            content,
        )

    def test_logout_post_invalida_sesion(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('logout')
        )

        self.assertRedirects(
            response,
            reverse('login'),
            fetch_redirect_response=False,
        )

        response = self.client.get(
            reverse('certificacion_intera:dashboard')
        )

        self.assertRedirects(
            response,
            (
                f"{reverse('login')}?next="
                f"{reverse('certificacion_intera:dashboard')}"
            ),
            fetch_redirect_response=False,
        )

    def test_direccion_y_sistemas_conservan_portal_general(self):
        for group_name in (
            'Dirección',
            'Sistemas',
        ):
            group = Group.objects.get_or_create(
                name=group_name
            )[0]

            user = get_user_model().objects.create_user(
                username=group_name,
                password='clave-de-prueba-segura',
            )

            user.groups.add(group)

            response = self.client.post(
                reverse('login'),
                {
                    'username': user.username,
                    'password': 'clave-de-prueba-segura',
                },
            )

            self.assertRedirects(
                response,
                reverse('dashboard'),
                fetch_redirect_response=False,
            )

            self.client.logout()
