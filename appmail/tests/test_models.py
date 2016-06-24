from __future__ import unicode_literals

import mock

from django.conf import settings
from django.db import IntegrityError

from django.utils.translation import ugettext as _

from django.test import (
    override_settings,
    TransactionTestCase,
)

from appmail.models import (
    EmailTemplate,
    EmailTemplateDoesNotExist,
    EmailTemplateTranslation,
    InvalidLanguageCode,
)

HTML_LOREM = """
<html>
<body>
    <h1>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit.
    </h1>
    <p>
        Sint modo partes vitae beatae. Duo Reges: constructio interrete.
        Cum salvum esse flentes sui respondissent, rogavit essentne fusi hostes.
    </p>

    <ul>
        <li>
            Te enim iudicem aequum puto, modo quae dicat ille bene noris.
        </li>
        <li>
        In eo enim positum est id, quod dicimus esse expetendum.
        </li>
    </ul>
</body>
</html>
"""


TEXT_LOREM = """#  Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n\nSint modo partes vitae beatae. Duo Reges: constructio interrete. Cum salvum\nesse flentes sui respondissent, rogavit essentne fusi hostes.\n\n  * Te enim iudicem aequum puto, modo quae dicat ille bene noris. \n  * In eo enim positum est id, quod dicimus esse expetendum. \n\n"""  # noqa


class EmailTemplateManagerTestCase(TransactionTestCase):

    def _bootstrap_template(
        self,
        name,
        locale_code,
        html_content=None,
        text_content=None,
    ):
        template = EmailTemplate(
            name=name,
            locale=locale_code,
            html_template=html_content or HTML_LOREM
        )
        template.save()

        return template

    def _bootstrap_template_translation(
        self,
        name,
        locale_code,
        html_content=None,
        text_content=None,
    ):

        parent_template = EmailTemplate.objects.get(name=name)

        trans_template = EmailTemplateTranslation(
            parent_template=parent_template,
            locale=locale_code,
            html_template=html_content or HTML_LOREM
        )

        trans_template.save()

        return trans_template

    def test_unique_constraints_for_templates_and_translations(self):
        # Belt-and-braces

        self._bootstrap_template(
            name='test_template_1',
            locale_code='cn'
        )

        with self.assertRaises(IntegrityError):
            # One main/parent template only, regardless of locale
            self._bootstrap_template(
                name='test_template_1',
                locale_code='en'
            )

        # But multiple translations for the same parent are ok
        # as long as the locales are different
        self._bootstrap_template_translation(
            name='test_template_1',
            locale_code='es-ar'
        )
        self._bootstrap_template_translation(
            name='test_template_1',
            locale_code='es'
        )
        mx_trans = self._bootstrap_template_translation(
            name='test_template_1',
            locale_code='es-mx'
        )
        with self.assertRaises(IntegrityError) as ctx:
            self._bootstrap_template_translation(
                name='test_template_1',
                locale_code='es-mx'
            )

        expected_message = _(
            "An EmailTemplateTranslation already exists for %(name)s:%(locale)s"
        ) % {
            'name': 'test_template_1',
            'locale': 'es-mx'
        }

        self.assertEqual(
            str(ctx.exception),
            expected_message
        )

        # but can still re-save a unique one:
        try:
            mx_trans.save()
        except IntegrityError:
            self.fail("Should be able to re-save a translation")

        # Also check that you can't have a translation in the same
        # language as the parent template
        with self.assertRaises(IntegrityError) as ctx:
            self._bootstrap_template_translation(
                name='test_template_1',
                locale_code='cn'   # same as parent template
            )

        expected_message = _(
            "An EmailTemplateTranslation cannot be for the same "
            "language as its parent - %(name)s:%(locale)s"
        ) % {
            'name': 'test_template_1',
            'locale': 'cn',
        }

        self.assertEqual(
            str(ctx.exception),
            expected_message
        )

    @override_settings(LANGUAGE_CODE='en-us')
    def test_get_by_name_then_locale(self):
        # .test_get_by_name_then_locale('en-us', 'my_test_template')
        # .test_get_by_name_then_locale('en-gb', 'my_test_template')
        # .test_get_by_name_then_locale('de', 'my_test_template')

        self._bootstrap_template(
            name='test_template_1',
            locale_code='en'
        )

        template_1_en_gb = self._bootstrap_template_translation(
            name='test_template_1',
            locale_code='en-gb'
        )

        self._bootstrap_template_translation(
            name='test_template_1',
            locale_code='de'
        )

        template_2_en_us = self._bootstrap_template(
            name='test_template_2',
            locale_code='en'
        )

        self._bootstrap_template_translation(
            name='test_template_2',
            locale_code='en-gb'
        )

        template_2_de = self._bootstrap_template_translation(
            name='test_template_2',
            locale_code='de'
        )

        assert EmailTemplate.objects.count() == 2
        assert EmailTemplateTranslation.objects.count() == 4

        # Getting specific template in appropriate language
        self.assertEqual(
            EmailTemplate.objects.get_by_name_then_locale(
                name='test_template_2',
                locale_code='de'
            ),
            template_2_de
        )

        self.assertEqual(
            EmailTemplate.objects.get_by_name_then_locale(
                name='test_template_1',
                locale_code='en-gb'
            ),
            template_1_en_gb
        )

        # Also show fallback to nearest-fit language, if possible

        self.assertEqual(
            EmailTemplate.objects.get_by_name_then_locale(
                name='test_template_2',
                locale_code='de-xx'  # fake code
            ),
            template_2_de
        )

        self.assertEqual(
            EmailTemplate.objects.get_by_name_then_locale(
                name='test_template_2',
                locale_code='en-us'  # doesn't exist
            ),
            template_2_en_us
        )

        # Show no locale_code uses the default language as a lookup
        assert settings.LANGUAGE_CODE == 'en-us'
        self.assertEqual(
            EmailTemplate.objects.get_by_name_then_locale(
                name='test_template_2',
            ),
            template_2_en_us
        )

        # Show a complete miss
        with self.assertRaises(EmailTemplateDoesNotExist):
            EmailTemplate.objects.get_by_name_then_locale(
                name='test_template_WHICH_DOES_NOT_EXIST',
                locale_code='de-xx'  # fake code
            ),

    @mock.patch('appmail.models.logger')
    def test_get_by_name_then_locale__logs_fallback_appropriately(self, mock_logger):

        # by default, the logger logs as ERROR, if not configured otherwise

        # We can't use override_settings here as we want to fake it not being
        # configured at all
        _log_level = getattr(settings, 'APPMAIL_TEMPLATE_LOOKUP_LOGLEVEL', None)

        try:
            delattr(settings, 'APPMAIL_TEMPLATE_LOOKUP_LOGLEVEL')
        except AttributeError:
            pass

        assert not mock_logger.debug.called
        assert not mock_logger.info.called
        assert not mock_logger.warning.called
        assert not mock_logger.error.called
        assert not mock_logger.exception.called

        self.assertEqual(
            EmailTemplate.objects._clean_language_code_input(
                locale_code='de-xx'  # fake code
            ),
            'de'
        )

        assert not mock_logger.debug.called
        assert not mock_logger.info.called
        assert mock_logger.warning.called
        assert not mock_logger.error.called
        assert not mock_logger.exception.called

        expected_call_args = (
            "appmail.EmailTemplate lookup: could not find exact "
            "match for locale code '%s'. Will try '%s' instead",
            'de-xx',
            'de'
        )

        self.assertEqual(mock_logger.warning.call_count, 1)
        self.assertEqual(
            mock_logger.warning.call_args[0],
            expected_call_args
        )

        # Confirm custom log levels work
        setattr(settings, 'APPMAIL_TEMPLATE_LOOKUP_LOGLEVEL', 'ERROR')

        self.assertEqual(
            EmailTemplate.objects._clean_language_code_input(
                locale_code='de-xx'  # fake code
            ),
            'de'
        )

        self.assertEqual(mock_logger.error.call_count, 1)
        self.assertEqual(
            mock_logger.error.call_args[0],
            expected_call_args
        )
        mock_logger.warning.reset_mock()

        # reinstate the old log level
        setattr(settings, 'APPMAIL_TEMPLATE_LOOKUP_LOGLEVEL', _log_level)

    @override_settings(LANGUAGE_CODE='es-mx')
    def test_get_by_name_then_locale__cleans_locale_input(self):

        assert "XX-yy" not in [x[0] for x in settings.LANGUAGES]

        for _code, expected_output in [
            ('en_GB', 'en-gb'),
            ('en-GB', 'en-gb'),
            ('en-gb', 'en-gb'),

            # show that US-centric core settings are mitigated
            ('en-US', 'en'),
            ('en_US', 'en'),
            ('en-us', 'en'),

            ('en', 'en'),
        ]:

            self.assertEqual(
                EmailTemplate.objects._clean_language_code_input(_code),
                expected_output
            )


class EmailTemplateTestCase(TransactionTestCase):

    maxDiff = None

    def test_plaintext_prepopulation_on_first_save_only(self):

        template = EmailTemplate(
            name='test_template',
            locale='es-mx',
            html_template=HTML_LOREM,
            text_template=''  # ie, empty string; won't save if None/NULL
        )
        template.save()

        self.assertEqual(
            template.html_template.strip(),
            HTML_LOREM.strip(),
        )
        self.assertEqual(
            template.text_template.strip(),
            TEXT_LOREM.strip(),
        )

        template.text_template = TEXT_LOREM[::-1].strip()
        template.save()

        template_1_refreshed = EmailTemplate.objects.get(pk=template.pk)
        self.assertEqual(
            template_1_refreshed.text_template.strip(),
            TEXT_LOREM[::-1].strip()
        )
