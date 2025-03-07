from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, modelformset_factory

from common.utils.groklinks import ARCHIVED_LINK_TYPES
from common.utils.text import slugify_tag
from demoscene.models import BlacklistedTag, Edit
from productions.models import Credit


class ExternalLinkForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["url"] = forms.CharField(label="URL", initial=self.instance.url, max_length=4096)

    def clean_url(self):
        data = self.cleaned_data["url"]
        try:
            data.encode("ascii")
        except UnicodeEncodeError:
            raise ValidationError("URL must be pure ASCII - try copying it from your browser location bar")

        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.url = self.cleaned_data["url"]
        if commit:
            instance.validate_unique()
            instance.save()
        return instance

    class Meta:
        # no actual fields from the model are saved (only 'url', which is a property masquerading
        # as a model and has to be handled as a special case above)
        fields = []


class BaseExternalLinkFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.exclude(link_class__in=ARCHIVED_LINK_TYPES)

    def log_edit(self, user, action_type):
        descriptions = []

        if self.new_objects:
            added_urls = [link.url for link in self.new_objects]
            if len(added_urls) > 1:
                descriptions.append("Added links: %s" % ", ".join(added_urls))
            else:
                descriptions.append("Added link %s" % ", ".join(added_urls))

        if self.changed_objects:
            updated_urls = [link.url for (link, fields) in self.changed_objects]
            if len(updated_urls) > 1:
                descriptions.append("Updated links: %s" % ", ".join(updated_urls))
            else:
                descriptions.append("Updated link %s" % ", ".join(updated_urls))

        if self.deleted_objects:
            deleted_urls = [link.url for link in self.deleted_objects]
            if len(deleted_urls) > 1:
                descriptions.append("Deleted links: %s" % ", ".join(deleted_urls))
            else:
                descriptions.append("Deleted link %s" % ", ".join(deleted_urls))

        if descriptions:
            Edit.objects.create(
                action_type=action_type, focus=self.instance, description=("; ".join(descriptions)), user=user
            )

    def save_ignoring_uniqueness(self):
        links = self.save(commit=False)
        for link in links:
            try:
                link.validate_unique()
                link.save()
            except ValidationError:
                pass  # skip over any links that fail uniqueness
        # 1.7 changed the handling of deleted_objects if commit=False
        for link in self.deleted_objects:
            link.delete()


class CreditForm(forms.ModelForm):
    category = forms.ChoiceField(
        choices=[("", "--------")] + Credit.CATEGORIES,
        required=True,
        error_messages={"required": "Category must be specified"},
    )

    class Meta:
        model = Credit
        fields = ("category", "role")


CreditFormSet = modelformset_factory(Credit, fields=("category", "role"), can_delete=True, form=CreditForm)


class BaseTagsForm(forms.ModelForm):
    def clean_tags(self):
        clean_tags = []
        for name in self.cleaned_data["tags"]:
            name = slugify_tag(name)
            try:
                blacklisted_tag = BlacklistedTag.objects.get(tag=name)
                name = slugify_tag(blacklisted_tag.replacement)
            except BlacklistedTag.DoesNotExist:
                pass
            if name:
                clean_tags.append(name)

        return clean_tags

    class Meta:
        fields = ["tags"]
