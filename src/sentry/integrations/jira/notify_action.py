from __future__ import absolute_import

import logging

from django import forms
from django.utils.translation import ugettext_lazy as _

from sentry.integrations.jira.utils import (
    get_name_for_jira,
    transform_jira_fields_to_form_fields,
    transform_jira_choices_to_strings,
)
from sentry.models.integration import Integration
from sentry.rules.actions.base import TicketEventAction
from sentry.shared_integrations.exceptions import IntegrationError
from sentry.utils.http import absolute_uri
from sentry.web.decorators import transaction_start


logger = logging.getLogger("sentry.rules")

INTEGRATION_KEY = "integration"


class JiraNotifyServiceForm(forms.Form):
    integration = forms.ChoiceField(choices=(), widget=forms.Select())

    def __init__(self, *args, **kwargs):
        integrations = [(i.id, i.name) for i in kwargs.pop("integrations")]
        super(JiraNotifyServiceForm, self).__init__(*args, **kwargs)
        if integrations:
            self.fields[INTEGRATION_KEY].initial = integrations[0][0]

        self.fields[INTEGRATION_KEY].choices = integrations
        self.fields[INTEGRATION_KEY].widget.choices = self.fields[INTEGRATION_KEY].choices


class JiraCreateTicketAction(TicketEventAction):
    form_cls = JiraNotifyServiceForm
    label = u"""Create a Jira issue in {integration} with these """
    ticket_type = "a Jira issue"
    link = "https://docs.sentry.io/product/integrations/jira/#issue-sync"
    provider = "jira"
    issue_key_path = "key"
    integration_key = INTEGRATION_KEY

    def render_label(self):
        # Make a copy of data.
        kwargs = transform_jira_choices_to_strings(self.form_fields, self.data)

        # Replace with "removed" if the integration was uninstalled.
        kwargs.update({self.integration_key: self.get_integration_name()})

        # Only add values when they exist.
        return self.label.format(**kwargs)

    def get_dynamic_form_fields(self):
        """
        Either get the dynamic form fields cached on the DB return `None`.

        :return: (Option) Django form fields dictionary
        """
        fields_list = self.data.get("dynamic_form_fields")
        if not fields_list:
            return None

        # Although this can be done with dict comprehension, looping for clarity.
        fields = {}
        for field in fields_list:
            if "name" in field:
                fields[field["name"]] = field
        return fields
        # if "dynamic_form_fields" in self.data:
        #     return self.data["dynamic_form_fields"]

        # try:
        #     integration = self.get_integration()
        # except Integration.DoesNotExist:
        #     pass
        # else:
        #     installation = integration.get_installation(self.project.organization.id)
        #     if installation:
        #         try:
        #             fields = installation.get_create_issue_config_no_params()
        #         except IntegrationError as e:
        #             # TODO log when the API call fails.
        #             logger.info(e)
        #         else:
        #             dynamic_form_fields = transform_jira_fields_to_form_fields(fields)
        #             print("jira form fields: ", dynamic_form_fields)
        #             self.data["dynamic_form_fields"] = dynamic_form_fields
        #             # TODO should I wipe out the rest of the data?
        #             return dynamic_form_fields
        # return None
        if "dynamic_form_fields" in self.data:
            return self.data["dynamic_form_fields"]

        try:
            integration = self.get_integration()
        except Integration.DoesNotExist:
            pass
        else:
            installation = integration.get_installation(self.project.organization.id)
            if installation:
                try:
                    fields = installation.get_create_issue_config_no_params()
                except IntegrationError as e:
                    # TODO log when the API call fails.
                    logger.info(e)
                else:
                    dynamic_form_fields = transform_jira_fields_to_form_fields(fields)
                    self.data["dynamic_form_fields"] = dynamic_form_fields
                    # TODO should I wipe out the rest of the data?
                    return dynamic_form_fields
        return None
>>>>>>> okay it works again

    def clean(self):
        cleaned_data = super(JiraCreateTicketAction, self).clean()

        integration = cleaned_data.get(self.integration_key)
        try:
            Integration.objects.get(id=integration)
        except Integration.DoesNotExist:
            raise forms.ValidationError(
                _("Jira integration is a required field.",), code="invalid",
            )

    def generate_footer(self, rule_url):
        return u"This ticket was automatically created by Sentry via [{}|{}]".format(
            self.rule.label, absolute_uri(rule_url),
        )

    def fix_data_for_issue(self):
        # HACK to get fixVersion in the correct format
        if self.data.get("fixVersions"):
            if not isinstance(self.data["fixVersions"], list):
                self.data["fixVersions"] = [self.data["fixVersions"]]
        return self.data

    def translate_integration(self, integration):
        name = integration.metadata.get("domain_name", integration.name)
        return name.replace(".atlassian.net", "")

    @transaction_start("JiraCreateTicketAction.after")
    def after(self, event, state):
        self.fix_data_for_issue()
        yield super(JiraCreateTicketAction, self).after(event, state)
