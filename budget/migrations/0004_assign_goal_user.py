from django.db import migrations


def assign_goals(apps, schema_editor):
    """既存の年間目標を持ち主に割り当てる。

    持ち主の決め方: 家計簿エントリを最も多く持つユーザー →
    いなければ最初のスーパーユーザー → それもいなければ最初のユーザー。
    ユーザーが1人もいなければ、孤立した目標は削除する。
    """
    YearlyGoal = apps.get_model('budget', 'YearlyGoal')
    BudgetEntry = apps.get_model('budget', 'BudgetEntry')
    User = apps.get_model('auth', 'User')

    orphans = YearlyGoal.objects.filter(user__isnull=True)
    if not orphans.exists():
        return

    from django.db.models import Count
    top = (BudgetEntry.objects.values('user').annotate(n=Count('id')).order_by('-n').first())
    owner = None
    if top:
        owner = User.objects.filter(pk=top['user']).first()
    if owner is None:
        owner = (User.objects.filter(is_superuser=True).order_by('id').first()
                 or User.objects.order_by('id').first())
    if owner is None:
        orphans.delete()
    else:
        orphans.update(user=owner)


class Migration(migrations.Migration):
    """手順2/3: データの移行（スキーマ変更とは別ファイルにするのが定石）。"""

    dependencies = [('budget', '0003_yearlygoal_user')]

    operations = [migrations.RunPython(assign_goals, migrations.RunPython.noop)]
