from __future__ import unicode_literals

import logging
from html2text import html2text as html2text_func

from django.db import (
    IntegrityError,
    models,
)
from django.utils.translation import (
    ugettext as _,
    ugettext_lazy as _lazy,
)
from django.conf import settings

logger = logging.getLogger(__name__)

# settings.LANGUAGE_CODE is 'en-us' by default, but settings.LANGUAGES
# only has 'en' 'en-gb' and 'en-au' keys. So, let's patch to ensure that
# the default en-us is used to select the 'English' template (if it's
# still the default)
_LANGUAGE_CODE = settings.LANGUAGE_CODE
if _LANGUAGE_CODE == 'en-us':
    _LANGUAGE_CODE = 'en'

# Also, make it clear that the default 'en' version of English
# is actually US English (given that UK and Aus are distinct)
_LANGUAGES = []
for lang in settings.LANGUAGES:
    if lang[0] == "en":
        lang = list(lang)
        lang[1] = "English (American)"

    _LANGUAGES.append(lang)


class InvalidLanguageCode(Exception):
    pass


class EmailTemplateDoesNotExist(Exception):
    pass


class EmailTemplateManager(models.Manager):

    def _clean_language_code_input(self, locale_code):
        """Cleans the given locale code, standardising syntax
        and converting it to the 'best fit' for any known language
        in settings.LANGUAGES, defaulting to settings.LANGUAGE.

        This exists because it's very easy to get 'foo_BAR' mixed up with
        'foo-bar' as a locale identifier.

        Args:
            locale_code (str): Description

        Returns:
            string: a cleaned locale code

        """

        # Clean up syntax for best chance at matching bad input
        cleaned_locale_code = locale_code.lower().replace('_', '-')

        if cleaned_locale_code in [x[0] for x in settings.LANGUAGES]:
            return cleaned_locale_code

        # Fallback: go with the core language, if not the region/dialect
        core_locale_code = locale_code[:2]
        if core_locale_code in [x[0] for x in settings.LANGUAGES]:
            log_level = getattr(
                settings,
                "APPMAIL_TEMPLATE_LOOKUP_LOGLEVEL",
                "WARNING"
            ).lower()

            log_args = (
                "appmail.EmailTemplate lookup: could not find exact "
                "match for locale code '%s'. Will try '%s' instead",
                locale_code,
                core_locale_code
            )

            getattr(logger, log_level)(*log_args)

            return core_locale_code

        return settings.LANGUAGE_CODE

    def get_by_name_then_locale(self, name, locale_code=settings.LANGUAGE_CODE):
        """Filters down EmailTemplates to only those that match
            the given template name.

            If there is more than one, get it for the given locale_code.
            If there is no match for the given locale_code, return the
            primary/main one for that name.

            If all this fails, raise EmailTemplateDoesNotExist

        Args:
            - name (string): template_name - case sensitive, ideally all lower
            - locale_code (string): locale from settings.LANGUAGES eg en-us

        Returns:
            an EmailTemplate or EmailTemplateTranslation instance

        Raises:
            EmailTemplateDoesNotExist if no good fit can be found for the name
            and locale AND the fallback of the default language for that name
            also fails

        """

        cleaned_locale_code = self._clean_language_code_input(locale_code)

        try:
            template = EmailTemplate.objects.get(
                name=name,
            )
        except EmailTemplate.DoesNotExist as e:
            # If the main template doesn't exist, no need to carry on
            raise EmailTemplateDoesNotExist(e)

        if template.locale != cleaned_locale_code:
            # template.locale is just the identifier string

            try:
                return template.translations.get(
                    locale=cleaned_locale_code
                )
            except EmailTemplateTranslation.DoesNotExist:

                log_level = getattr(
                    settings,
                    "APPMAIL_TEMPLATE_LOOKUP_LOGLEVEL",
                    "WARNING"
                ).lower()

                log_args = (
                    "appmail.EmailTemplate lookup: could not find exact "
                    "match for '%s'. Returned %s",
                    locale_code,
                    template.name
                )

                getattr(logger, log_level)(*log_args)

        return template


class EmailTemplateContentBase(models.Model):
    """Abstract class that defines the editable content in an email template"""

    subject = models.CharField(
        verbose_name=_lazy("Subject"),
        max_length=255,
        blank=True,
        help_text=_lazy(
            "Subject line template for this email. Remember, you can "
            "use any template vars available to the message body. "
            "Try to keep it below 78 characters; 255 is our max."
            # See http://www.faqs.org/rfcs/rfc2822.html
            # for 78 and 998-char limits
        )
    )

    html_template = models.TextField(
        verbose_name=_lazy("HTML template"),
        blank=True,
        help_text=_lazy(
            "HTML EMAIL TEMPLATE. Write this like a regular Django template, "
            "with variables and even template tags. If you extend another "
            "template, that template needs to be available via "
            "settings.TEMPLATE_DIRS"
        )
    )

    text_template = models.TextField(
        verbose_name=_lazy("Plain-text template"),
        blank=True,
        help_text=_lazy(
            "PLAINTEXT version of the HTML template. If left blank, this "
            "will be autogenerated the first time the HTML version is saved, "
            "but once only."
        )
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):

        if not self.pk and not self.text_template:
            self.text_template = html2text_func(self.html_template)

        return super(EmailTemplateContentBase, self).save(*args, **kwargs)


class EmailTemplate(EmailTemplateContentBase):
    """Database-stored content template (subject, HTML, plaintext)
    for a transactional email, in default translation."""

    name = models.SlugField(
        verbose_name=_lazy("Template name"),
        max_length=255,
        unique=True,
        help_text=_lazy(
            "Unique identifier for this template. "
            "Used when specifying which email to send. "
            "NB: this is case sensitive."
        )
        # Note, we could make this unique yet case insensitive
        # using a functional index in postgres:
        # www.postgresql.org/docs/current/static/indexes-expressional.html
        # but that will break on other DBs
    )

    locale = models.CharField(
        verbose_name=_lazy("Locale/language"),
        choices=_LANGUAGES,
        default=_LANGUAGE_CODE,
        max_length=50
    )

    # Plus fields inherited from base class

    objects = EmailTemplateManager()

    class Meta:
        app_label = "appmail"

    def __unicode__(self):
        return _lazy(
            "EmailTemplate: %(name)s (%(locale)s)"
        ) % {
            'name': self.name,
            'locale': self.locale
        }

    def __repr__(self):
        return (
            "<EmailTemplate id=%s, name=%s locale=%s>" % (
                self.id,
                self.name,
                self.locale,
            )
        )


class EmailTemplateTranslation(EmailTemplateContentBase):
    """Language-specific (ie, translated) content of an EmailTemplate.
    Designed to work as a child of that parent, and edited via an Inline
    in the Django Admin"""

    parent_template = models.ForeignKey(
        'EmailTemplate',
        related_name="translations",
        verbose_name=_lazy("Parent template")
    )

    locale = models.CharField(
        verbose_name=_lazy("Locale/language"),
        choices=_LANGUAGES,
        default=_LANGUAGE_CODE,
        max_length=50
    )

    # Plus fields inherited from base class

    class Meta:
        app_label = "appmail"

    def __unicode__(self):
        return _lazy(
            "EmailTemplateTranslation: %(name)s (%(locale)s)"
        ) % {
            'name': self.parent_templates.name,
            'locale': self.locale
        }

    def __repr__(self):
        return (
            "<EmailTemplateTranslation id=%s, name=%s locale=%s>" % (
                self.id,
                self.parent_template.name,
                self.locale,
            )
        )

    def _enforce_integrity(self):
        """Custom integrity checks because unique_together doesn't seem to
            work with FKs.

            While odd, we can at least implement the equivalent of this:

            unique_together = (
                ('parent_template_id', 'locale'),
            )

            We'll also check that a translation is not being saved in the
            same language as its parent template.

        """

        if self.parent_template and self.locale:

            base_qs = EmailTemplateTranslation.objects.filter(
                parent_template__id=self.parent_template_id,
                locale=self.locale
            )
            if self.pk:
                # It may not be saved yet, after all
                base_qs = base_qs.exclude(pk=self.pk)

            if base_qs.exists():
                raise IntegrityError(
                    _(
                        "An EmailTemplateTranslation already exists "
                        "for %(name)s:%(locale)s"
                    ) % {
                        'name': self.parent_template.name,
                        'locale': self.locale
                    }
                )

            if self.locale == self.parent_template.locale:
                raise IntegrityError(
                    _(
                        "An EmailTemplateTranslation cannot be for the same "
                        "language as its parent - %(name)s:%(locale)s"
                    ) % {
                        'name': self.parent_template.name,
                        'locale': self.locale
                    }
                )

    def save(self, *args, **kwargs):

        self._enforce_integrity()

        return super(EmailTemplateTranslation, self).save(*args, **kwargs)
