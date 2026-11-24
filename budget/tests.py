from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import BudgetEntry, Category


class BudgetTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('alice', password='pw')
        cls.bob = User.objects.create_user('bob', password='pw')
        cls.income = Category.objects.create(name='給与', category_type='income')
        cls.expense = Category.objects.create(name='食費', category_type='expense')

    def add(self, user, d, category, amount, description=''):
        return BudgetEntry.objects.create(
            user=user, date=d, category=category, amount=amount, description=description
        )


class LoginTests(BudgetTestBase):
    def test_anonymous_is_redirected_to_existing_login_page(self):
        r = self.client.get(reverse('budget:dashboard'))
        self.assertEqual(r.status_code, 302)
        # 転送先が 404 にならず、実際にログイン画面が開く
        self.assertEqual(self.client.get(r['Location']).status_code, 200)

    def test_login_redirects_to_dashboard(self):
        r = self.client.post(reverse('login'), {'username': 'alice', 'password': 'pw'})
        self.assertRedirects(r, reverse('budget:dashboard'))


class UserIsolationTests(BudgetTestBase):
    def setUp(self):
        self.entry = self.add(self.alice, date(2026, 11, 1), self.expense, 777, 'aliceのみ')
        self.client.login(username='bob', password='pw')

    def test_dashboard_does_not_show_other_users_data(self):
        self.add(self.alice, date.today(), self.income, 300000)
        r = self.client.get(reverse('budget:dashboard'))
        self.assertEqual(r.context['monthly_income'], 0)
        self.assertEqual(len(r.context['recent_entries']), 0)

    def test_monthly_view_does_not_show_other_users_data(self):
        r = self.client.get(reverse('budget:monthly_view'), {'year': 2026, 'month': 11})
        self.assertEqual(len(r.context['page_obj']), 0)
        self.assertEqual(r.context['total_expense'], 0)

    def test_cannot_edit_other_users_entry(self):
        r = self.client.get(reverse('budget:edit_entry', args=[self.entry.pk]))
        self.assertEqual(r.status_code, 404)

    def test_cannot_delete_other_users_entry(self):
        r = self.client.post(reverse('budget:delete_entry', args=[self.entry.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(BudgetEntry.objects.filter(pk=self.entry.pk).exists())

    def test_delete_requires_post(self):
        self.client.login(username='alice', password='pw')
        r = self.client.get(reverse('budget:delete_entry', args=[self.entry.pk]))
        self.assertEqual(r.status_code, 405)
        self.assertTrue(BudgetEntry.objects.filter(pk=self.entry.pk).exists())


class EntryCrudTests(BudgetTestBase):
    def setUp(self):
        self.client.login(username='alice', password='pw')

    def test_add_sets_user(self):
        r = self.client.post(reverse('budget:add_entry'), {
            'date': '2026-11-05', 'category': self.expense.pk,
            'amount': '1200', 'description': 'ランチ',
        })
        self.assertRedirects(r, reverse('budget:dashboard'))
        self.assertEqual(BudgetEntry.objects.get().user, self.alice)

    def test_edit_form_shows_date_in_iso_format(self):
        e = self.add(self.alice, date(2026, 11, 5), self.expense, 100)
        r = self.client.get(reverse('budget:edit_entry', args=[e.pk]))
        self.assertContains(r, 'value="2026-11-05"')

    def test_edit_keeps_inactive_category_selectable(self):
        e = self.add(self.alice, date(2026, 11, 5), self.expense, 100)
        self.expense.is_active = False
        self.expense.save()
        r = self.client.post(reverse('budget:edit_entry', args=[e.pk]), {
            'date': '2026-11-05', 'category': self.expense.pk, 'amount': '250',
        })
        self.assertEqual(r.status_code, 302)
        e.refresh_from_db()
        self.assertEqual(e.amount, 250)

    def test_next_param_returns_to_previous_page_but_rejects_external_urls(self):
        e = self.add(self.alice, date(2026, 11, 5), self.expense, 100)
        url = reverse('budget:delete_entry', args=[e.pk])
        r = self.client.post(url, {'next': '/budget/monthly/?year=2026&month=11'})
        self.assertRedirects(r, '/budget/monthly/?year=2026&month=11')
        e2 = self.add(self.alice, date(2026, 11, 6), self.expense, 100)
        r = self.client.post(reverse('budget:delete_entry', args=[e2.pk]),
                             {'next': 'https://evil.example/'})
        self.assertRedirects(r, reverse('budget:dashboard'))


class GraphTests(BudgetTestBase):
    def test_months_income_and_expense_stay_aligned(self):
        """旧バグ: 収入のない月に支出だけあると、棒が別の月にズレて描かれた"""
        self.add(self.alice, date(2026, 10, 10), self.expense, 5000)   # 10月は支出のみ
        self.add(self.alice, date(2026, 11, 1), self.income, 300000)
        self.add(self.alice, date(2026, 11, 2), self.expense, 1000)
        self.client.login(username='alice', password='pw')
        r = self.client.get(reverse('budget:graph'), {'year': 2026})
        ctx = r.context
        self.assertEqual(len(ctx['months']), 12)
        self.assertEqual(len(ctx['income_data']), 12)
        self.assertEqual(len(ctx['expense_data']), 12)
        self.assertEqual(ctx['expense_data'][9], 5000)    # 10月
        self.assertEqual(ctx['income_data'][9], 0)
        self.assertEqual(ctx['income_data'][10], 300000)  # 11月
        self.assertEqual(ctx['expense_data'][10], 1000)
        self.assertEqual(ctx['total_balance'], 300000 - 6000)

    def test_graph_only_counts_own_data_and_bad_year_is_safe(self):
        self.add(self.alice, date(2026, 11, 1), self.income, 300000)
        self.client.login(username='bob', password='pw')
        r = self.client.get(reverse('budget:graph'), {'year': 'abc'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_income'], 0)


class MonthlyViewTests(BudgetTestBase):
    def setUp(self):
        for i in range(25):
            self.add(self.alice, date(2026, 1, 5), self.expense, 100)
        self.add(self.alice, date(2026, 1, 6), self.income, 1000)
        self.client.login(username='alice', password='pw')

    def test_page_link_keeps_year_and_month(self):
        r = self.client.get(reverse('budget:monthly_view'), {'year': 2026, 'month': 1})
        self.assertContains(r, '?year=2026&amp;month=1&amp;page=2')

    def test_page_param_alone_does_not_crash_and_shows_current_month(self):
        r = self.client.get(reverse('budget:monthly_view'), {'page': 2})
        self.assertEqual(r.status_code, 200)

    def test_totals_and_second_page(self):
        r = self.client.get(reverse('budget:monthly_view'),
                            {'year': 2026, 'month': 1, 'page': 2})
        self.assertEqual(len(r.context['page_obj']), 6)  # 26件 - 20件
        self.assertEqual(r.context['total_expense'], 2500)
        self.assertEqual(r.context['total_income'], 1000)
        self.assertEqual(r.context['balance'], -1500)

    def test_invalid_month_falls_back_with_warning(self):
        r = self.client.get(reverse('budget:monthly_view'), {'year': 2026, 'month': 13})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([m.level_tag for m in r.context['messages']], ['warning'])

    def test_december_navigation(self):
        r = self.client.get(reverse('budget:monthly_view'), {'year': 2026, 'month': 12})
        self.assertEqual((r.context['next_month'].year, r.context['next_month'].month), (2027, 1))
        self.assertEqual((r.context['prev_month'].year, r.context['prev_month'].month), (2026, 11))


class YearlyGoalTests(BudgetTestBase):
    def test_goal_is_per_user(self):
        from datetime import date as _d
        from django.db import IntegrityError, transaction
        from .models import YearlyGoal
        year = _d.today().year
        YearlyGoal.objects.create(user=self.alice, year=year, savings_goal=200000)
        YearlyGoal.objects.create(user=self.bob, year=year, savings_goal=500000)  # 同じ年でも別ユーザーならOK
        with self.assertRaises(IntegrityError), transaction.atomic():
            YearlyGoal.objects.create(user=self.alice, year=year, savings_goal=1)  # 同一ユーザー・同一年はNG

        self.client.login(username='bob', password='pw')
        r = self.client.get(reverse('budget:dashboard'))
        self.assertEqual(r.context['yearly_goal'].savings_goal, 500000)


class GoalScreenTests(BudgetTestBase):
    def setUp(self):
        from .models import YearlyGoal
        self.YearlyGoal = YearlyGoal
        self.client.login(username='alice', password='pw')

    def test_add_goal_sets_user_and_shows_progress(self):
        self.add(self.alice, date(2026, 3, 1), self.income, 100000)
        self.add(self.alice, date(2026, 3, 2), self.expense, 40000)
        r = self.client.post(reverse('budget:goal_list'), {'year': 2026, 'savings_goal': 120000})
        self.assertRedirects(r, reverse('budget:goal_list'))
        goal = self.YearlyGoal.objects.get()
        self.assertEqual(goal.user, self.alice)
        r = self.client.get(reverse('budget:goal_list'))
        self.assertEqual(r.context['rows'][0]['savings'], 60000)
        self.assertEqual(r.context['rows'][0]['rate'], 50.0)

    def test_duplicate_year_is_rejected_with_message(self):
        self.YearlyGoal.objects.create(user=self.alice, year=2026, savings_goal=1)
        r = self.client.post(reverse('budget:goal_list'), {'year': 2026, 'savings_goal': 5})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'すでに登録されています')
        self.assertEqual(self.YearlyGoal.objects.count(), 1)

    def test_edit_can_keep_same_year(self):
        g = self.YearlyGoal.objects.create(user=self.alice, year=2026, savings_goal=1)
        r = self.client.post(reverse('budget:goal_edit', args=[g.pk]), {'year': 2026, 'savings_goal': 777})
        self.assertRedirects(r, reverse('budget:goal_list'))
        g.refresh_from_db()
        self.assertEqual(g.savings_goal, 777)

    def test_other_users_goal_is_404_for_edit_and_delete(self):
        g = self.YearlyGoal.objects.create(user=self.bob, year=2026, savings_goal=1)
        self.assertEqual(self.client.get(reverse('budget:goal_edit', args=[g.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('budget:goal_delete', args=[g.pk])).status_code, 404)
        self.assertTrue(self.YearlyGoal.objects.filter(pk=g.pk).exists())

    def test_negative_goal_and_bad_year_rejected(self):
        r = self.client.post(reverse('budget:goal_list'), {'year': 1999, 'savings_goal': -5})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.YearlyGoal.objects.count(), 0)


from django.core.management import call_command
from django.test import override_settings


class SignUpTests(BudgetTestBase):
    def test_signup_creates_user_logs_in_and_goes_to_goal_screen(self):
        r = self.client.post(reverse('signup'), {
            'username': 'carol', 'password1': 'S3cure-pass-phrase', 'password2': 'S3cure-pass-phrase',
        })
        self.assertRedirects(r, reverse('budget:goal_list'))
        self.assertTrue(User.objects.filter(username='carol').exists())
        # そのままログイン状態になっている
        self.assertEqual(self.client.get(reverse('budget:dashboard')).status_code, 200)

    def test_weak_or_mismatched_password_and_duplicate_username_are_rejected(self):
        for data in [
            {'username': 'dave', 'password1': '12345678', 'password2': '12345678'},         # 数字のみ・よくあるパスワード
            {'username': 'dave', 'password1': 'S3cure-pass-phrase', 'password2': 'different'},
            {'username': 'alice', 'password1': 'S3cure-pass-phrase', 'password2': 'S3cure-pass-phrase'},  # 既存名
        ]:
            r = self.client.post(reverse('signup'), data)
            self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='dave').exists())
        self.assertEqual(User.objects.filter(username='alice').count(), 1)

    def test_login_page_shows_signup_link_only_when_enabled(self):
        self.assertContains(self.client.get(reverse('login')), reverse('signup'))
        with override_settings(ALLOW_SIGNUP=False):
            self.assertNotContains(self.client.get(reverse('login')), reverse('signup'))

    def test_signup_is_404_when_disabled(self):
        with override_settings(ALLOW_SIGNUP=False):
            self.assertEqual(self.client.get(reverse('signup')).status_code, 404)
            r = self.client.post(reverse('signup'), {
                'username': 'eve', 'password1': 'S3cure-pass-phrase', 'password2': 'S3cure-pass-phrase'})
            self.assertEqual(r.status_code, 404)
        self.assertFalse(User.objects.filter(username='eve').exists())

    def test_logged_in_user_is_redirected_away_from_signup(self):
        self.client.login(username='alice', password='pw')
        self.assertRedirects(self.client.get(reverse('signup')), reverse('budget:dashboard'))


class SetupCategoriesCommandTests(TestCase):
    def test_runs_on_empty_db_without_user(self):
        call_command('setup_categories', verbosity=0)
        self.assertEqual(Category.objects.count(), 12)

    def test_creates_goal_for_given_user(self):
        from .models import YearlyGoal
        u = User.objects.create_user('hiroppy', password='pw')
        call_command('setup_categories', user='hiroppy', goal=300000, verbosity=0)
        self.assertEqual(YearlyGoal.objects.get(user=u).savings_goal, 300000)

    def test_unknown_user_aborts_before_creating_anything(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command('setup_categories', user='nobody', verbosity=0)
        self.assertEqual(Category.objects.count(), 0)
