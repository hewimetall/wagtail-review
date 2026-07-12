import json

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page

from wagtail_review.models import Annotation, Review, Reviewer
from wagtail_review.views.annotations_api import _check_reviewer_credentials


class TestAnnotationAPI(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.homepage = Page.objects.get(url_path='/home/').specific
        self.revision = self.homepage.save_revision()
        self.review = Review.objects.create(page_revision=self.revision, submitter=User.objects.first())
        self.reviewer = Reviewer.objects.create(review=self.review, email='reviewer@example.com')
        self.annotation = self.reviewer.annotations.create(quote='quoted text', text='Looks good')
        self.annotation.ranges.create(
            start='/p[1]',
            start_offset=0,
            end='/p[1]',
            end_offset=11,
        )

    def credentials(self, mode='respond', reviewer=None, token=None):
        reviewer = reviewer or self.reviewer
        if token is None:
            token = reviewer.view_token if mode == 'view' else reviewer.response_token
        return {
            'HTTP_X_WAGTAILREVIEW_MODE': mode,
            'HTTP_X_WAGTAILREVIEW_REVIEWER': str(reviewer.id),
            'HTTP_X_WAGTAILREVIEW_TOKEN': token,
        }

    def test_root(self):
        response = self.client.get(reverse('wagtail_review:annotations_api_root'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'name': 'Annotator Store API',
            'version': '2.0.0',
        })

    def test_credentials_accept_query_parameters(self):
        request = self.client.get(
            reverse('wagtail_review:annotations_api_index'),
            {
                'mode': 'view',
                'reviewer': self.reviewer.id,
                'token': self.reviewer.view_token,
            },
        ).wsgi_request

        reviewer, mode = _check_reviewer_credentials(request)

        self.assertEqual(reviewer, self.reviewer)
        self.assertEqual(mode, 'view')

    def test_credentials_reject_missing_or_wrong_token(self):
        request = self.client.get(reverse('wagtail_review:annotations_api_index')).wsgi_request
        with self.assertRaises(PermissionDenied):
            _check_reviewer_credentials(request)

        request = self.client.get(
            reverse('wagtail_review:annotations_api_index'),
            **self.credentials(token='wrong-token')
        ).wsgi_request
        with self.assertRaises(PermissionDenied):
            _check_reviewer_credentials(request)

    def test_index_lists_annotations_for_review(self):
        response = self.client.get(
            reverse('wagtail_review:annotations_api_index'),
            **self.credentials(mode='view'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['id'], self.annotation.id)
        self.assertEqual(response.json()[0]['ranges'][0]['start'], '/p[1]')

    def test_create_annotation(self):
        response = self.client.post(
            reverse('wagtail_review:annotations_api_index'),
            data=json.dumps({
                'quote': 'new quote',
                'text': 'Needs a citation',
                'ranges': [
                    {
                        'start': '/p[2]',
                        'startOffset': 3,
                        'end': '/p[2]',
                        'endOffset': 9,
                    }
                ],
            }),
            content_type='application/json',
            **self.credentials(),
        )

        annotation = Annotation.objects.get(text='Needs a citation')
        self.assertRedirects(
            response,
            reverse('wagtail_review:annotations_api_item', args=[annotation.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(annotation.quote, 'new quote')
        self.assertEqual(annotation.ranges.get().start_offset, 3)

    def test_view_mode_cannot_create_annotation(self):
        response = self.client.post(
            reverse('wagtail_review:annotations_api_index'),
            data=json.dumps({'quote': 'quote', 'text': 'text', 'ranges': []}),
            content_type='application/json',
            **self.credentials(mode='view'),
        )

        self.assertEqual(response.status_code, 403)

    def test_closed_review_cannot_create_annotation(self):
        self.review.status = 'closed'
        self.review.save()

        response = self.client.post(
            reverse('wagtail_review:annotations_api_index'),
            data=json.dumps({'quote': 'quote', 'text': 'text', 'ranges': []}),
            content_type='application/json',
            **self.credentials(),
        )

        self.assertEqual(response.status_code, 403)

    def test_item_rejects_annotation_from_another_review(self):
        other_review = Review.objects.create(page_revision=self.revision, submitter=User.objects.first())
        other_reviewer = Reviewer.objects.create(review=other_review, email='other@example.com')
        other_annotation = other_reviewer.annotations.create(quote='other', text='other')

        response = self.client.get(
            reverse('wagtail_review:annotations_api_item', args=[other_annotation.id]),
            **self.credentials(mode='view'),
        )

        self.assertEqual(response.status_code, 403)

    def test_item_and_search(self):
        item_response = self.client.get(
            reverse('wagtail_review:annotations_api_item', args=[self.annotation.id]),
            **self.credentials(mode='view'),
        )
        search_response = self.client.get(
            reverse('wagtail_review:annotations_api_search'),
            **self.credentials(mode='view'),
        )

        self.assertEqual(item_response.status_code, 200)
        self.assertEqual(item_response.json()['text'], 'Looks good')
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json()['total'], 1)

    def test_unsupported_methods(self):
        response = self.client.delete(
            reverse('wagtail_review:annotations_api_index'),
            **self.credentials(),
        )
        item_response = self.client.post(
            reverse('wagtail_review:annotations_api_item', args=[self.annotation.id]),
            **self.credentials(),
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(item_response.status_code, 405)
