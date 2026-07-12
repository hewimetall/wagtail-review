import json

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from wagtail.models import Page

from tests.models import SimplePage
from wagtail_review.models import Review


class TestAdminViews(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )
        self.homepage = Page.objects.get(url_path='/home/').specific

    def create_homepage_review(self):
        revision = self.homepage.save_revision()
        review = Review.objects.create(page_revision=revision, submitter=self.admin_user)
        review.reviewers.create(user=self.admin_user)
        review.reviewers.create(user=User.objects.get(username='spongebob'))
        return review

    def test_submit_for_review_action(self):
        """Test that 'submit for review' appears in the page action menu"""
        response = self.client.get('/admin/pages/%d/edit/' % self.homepage.pk)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Submit for review")
        # check that JS is imported
        self.assertContains(response, "wagtail_review/js/submit.js")

    def test_submit_for_review_action_on_create(self):
        """Test that 'submit for review' appears in the page action menu"""
        response = self.client.get('/admin/pages/add/tests/simplepage/%d/' % self.homepage.pk)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Submit for review")
        # check that JS is imported
        self.assertContains(response, "wagtail_review/js/submit.js")

    def test_create_review(self):
        response = self.client.get('/admin/wagtail_review/create_review/')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'form')

    def test_user_autocomplete(self):
        response = self.client.get('/admin/wagtail_review/autocomplete_users/?q=homer')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['results'], [
            {'id': 2, 'full_name': 'Homer Simpson', 'username': 'homer'}
        ])

        response = self.client.get('/admin/wagtail_review/autocomplete_users/?q=pants')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['results'], [
            {'id': 1, 'full_name': 'Spongebob Squarepants', 'username': 'spongebob'}
        ])

    def test_user_autocomplete_empty_query(self):
        response = self.client.get('/admin/wagtail_review/autocomplete_users/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'results': []})

    def test_dashboard_and_audit_trail(self):
        review = self.create_homepage_review()

        dashboard_response = self.client.get('/admin/wagtail_review/reviews/?ordering=page')
        audit_response = self.client.get('/admin/wagtail_review/reviews/%d/' % self.homepage.pk)

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Home')
        self.assertEqual(audit_response.status_code, 200)
        self.assertContains(audit_response, review.get_status_display())
        self.assertContains(audit_response, 'Awaiting response')

    def test_view_review_page_from_admin(self):
        page = SimplePage(title="Review page", slug="review-page")
        self.homepage.add_child(instance=page)
        review = Review.objects.create(page_revision=page.save_revision(), submitter=self.admin_user)
        review.reviewers.create(user=self.admin_user)

        response = self.client.get('/admin/wagtail_review/reviews/%d/view/' % review.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "var app = new annotator.App();")
        self.assertContains(response, "app.include(annotator.ui.main,")

    def test_close_reopen_and_publish_review(self):
        review = self.create_homepage_review()

        close_response = self.client.post('/admin/wagtail_review/reviews/%d/close/' % review.pk)
        review.refresh_from_db()
        self.assertRedirects(close_response, '/admin/wagtail_review/reviews/%d/' % self.homepage.pk)
        self.assertEqual(review.status, 'closed')

        reopen_response = self.client.post('/admin/wagtail_review/reviews/%d/reopen/' % review.pk)
        review.refresh_from_db()
        self.assertRedirects(reopen_response, '/admin/wagtail_review/reviews/%d/' % self.homepage.pk)
        self.assertEqual(review.status, 'open')

        publish_response = self.client.post('/admin/wagtail_review/reviews/%d/close_and_publish/' % review.pk)
        review.refresh_from_db()
        self.assertRedirects(publish_response, '/admin/wagtail_review/reviews/%d/' % self.homepage.pk)
        self.assertEqual(review.status, 'closed')

    def test_validate_reviewers_required(self):
        # reject a completely empty formset
        response = self.client.post('/admin/wagtail_review/create_review/', {
            'create_review_reviewers-TOTAL_FORMS': 0,
            'create_review_reviewers-INITIAL_FORMS': 0,
            'create_review_reviewers-MIN_NUM_FORMS': 0,
            'create_review_reviewers-MAX_NUM_FORMS': 1000,
        })
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'form')
        self.assertIn("Please select one or more reviewers.", response_json['html'])

        # reject a formset with only deleted items
        response = self.client.post('/admin/wagtail_review/create_review/', {
            'create_review_reviewers-TOTAL_FORMS': 1,
            'create_review_reviewers-INITIAL_FORMS': 0,
            'create_review_reviewers-MIN_NUM_FORMS': 0,
            'create_review_reviewers-MAX_NUM_FORMS': 1000,

            'create_review_reviewers-0-user': '',
            'create_review_reviewers-0-email': 'someone@example.com',
            'create_review_reviewers-0-DELETE': '1',
        })
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'form')
        self.assertIn("Please select one or more reviewers.", response_json['html'])

    def test_validate_ok(self):
        response = self.client.post('/admin/wagtail_review/create_review/', {
            'create_review_reviewers-TOTAL_FORMS': 1,
            'create_review_reviewers-INITIAL_FORMS': 0,
            'create_review_reviewers-MIN_NUM_FORMS': 0,
            'create_review_reviewers-MAX_NUM_FORMS': 1000,

            'create_review_reviewers-0-user': '',
            'create_review_reviewers-0-email': 'someone@example.com',
            'create_review_reviewers-0-DELETE': '',
        })
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'done')

    def test_post_edit_form(self):
        response = self.client.post('/admin/pages/2/edit/', {
            'title': "Home submitted",
            'slug': 'title',

            'create_review_reviewers-TOTAL_FORMS': 2,
            'create_review_reviewers-INITIAL_FORMS': 0,
            'create_review_reviewers-MIN_NUM_FORMS': 0,
            'create_review_reviewers-MAX_NUM_FORMS': 1000,

            'create_review_reviewers-0-user': '',
            'create_review_reviewers-0-email': 'someone@example.com',
            'create_review_reviewers-0-DELETE': '',

            'create_review_reviewers-1-user': User.objects.get(username='spongebob').pk,
            'create_review_reviewers-1-email': '',
            'create_review_reviewers-1-DELETE': '',

            'action-submit-for-review': '1',
        })

        self.assertRedirects(response, '/admin/pages/1/')

        self.homepage.refresh_from_db()
        revision = self.homepage.get_latest_revision()
        review = Review.objects.get(page_revision=revision)
        self.assertEqual(review.reviewers.count(), 3)

        reviewer_emails = set(reviewer.get_email_address() for reviewer in review.reviewers.all())
        self.assertEqual(reviewer_emails, {'admin@example.com', 'someone@example.com', 'spongebob@example.com'})

        self.assertEqual(len(mail.outbox), 2)
        email_recipients = set(email.to[0] for email in mail.outbox)
        self.assertEqual(email_recipients, {'someone@example.com', 'spongebob@example.com'})

    def test_post_create_form(self):
        response = self.client.post('/admin/pages/add/tests/simplepage/2/', {
            'title': "Subpage submitted",
            'slug': 'subpage-submitted',

            'create_review_reviewers-TOTAL_FORMS': 2,
            'create_review_reviewers-INITIAL_FORMS': 0,
            'create_review_reviewers-MIN_NUM_FORMS': 0,
            'create_review_reviewers-MAX_NUM_FORMS': 1000,

            'create_review_reviewers-0-user': '',
            'create_review_reviewers-0-email': 'someone@example.com',
            'create_review_reviewers-0-DELETE': '',

            'create_review_reviewers-1-user': User.objects.get(username='spongebob').pk,
            'create_review_reviewers-1-email': '',
            'create_review_reviewers-1-DELETE': '',

            'action-submit-for-review': '1',
        })

        self.assertRedirects(response, '/admin/pages/2/')

        revision = Page.objects.get(slug='subpage-submitted').get_latest_revision()
        review = Review.objects.get(page_revision=revision)
        self.assertEqual(review.reviewers.count(), 3)

        reviewer_emails = set(reviewer.get_email_address() for reviewer in review.reviewers.all())
        self.assertEqual(reviewer_emails, {'admin@example.com', 'someone@example.com', 'spongebob@example.com'})

        self.assertEqual(len(mail.outbox), 2)
        email_recipients = set(email.to[0] for email in mail.outbox)
        self.assertEqual(email_recipients, {'someone@example.com', 'spongebob@example.com'})
