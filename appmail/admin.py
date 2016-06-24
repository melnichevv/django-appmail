from django import forms
from django.contrib import admin

from ace_overlay.widgets import AceOverlayWidget

from appmail.models import (
    EmailTemplate,
    EmailTemplateTranslation,
)


class EmailTemplateFormBase(forms.ModelForm):

    def __init__(self, *args, **kwargs):

        super(EmailTemplateFormBase, self).__init__(*args, **kwargs)

        self.fields['html_template'].widget = AceOverlayWidget(
            height="800px",
            mode='html',
            showprintmargin=True,
            theme='twilight',
            width="850px",
            wordwrap=False,
        )

        self.fields['text_template'].widget = AceOverlayWidget(
            height="800px",
            mode='text',
            showprintmargin=True,
            theme='twilight',
            width="850px",
            wordwrap=False,
        )


class EmailTemplateForm(EmailTemplateFormBase):

    class Meta:
        model = EmailTemplate
        exclude = ()


class EmailTemplateTranslationForm(EmailTemplateFormBase):

    class Meta:
        model = EmailTemplateTranslation
        exclude = ()


class EmailTemplateTranslationInline(admin.StackedInline):
    model = EmailTemplateTranslation
    extra = 0

    form = EmailTemplateTranslationForm


class EmailTemplateAdmin(admin.ModelAdmin):
    model = EmailTemplate
    inlines = [
        EmailTemplateTranslationInline,
    ]

    form = EmailTemplateForm


admin.site.register(EmailTemplate, EmailTemplateAdmin)
