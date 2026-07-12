from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from wagtail_review.forms import get_review_form_class


class TestReviewFormConfiguration(SimpleTestCase):
    @override_settings(WAGTAILREVIEW_REVIEW_FORM='missing.module.CreateReviewForm')
    def test_missing_review_form_class_raises_improperly_configured(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "WAGTAILREVIEW_REVIEW_FORM refers to a form 'missing.module.CreateReviewForm' that is not available",
        ):
            get_review_form_class()
