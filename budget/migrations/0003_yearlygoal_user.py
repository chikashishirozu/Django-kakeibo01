from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """手順1/3: user 列を「空でもよい」状態で追加し、year 単独の unique を外す。"""

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budget', '0002_budgetentry_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='yearlygoal',
            name='user',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL, verbose_name='ユーザー',
            ),
        ),
        migrations.AlterField(
            model_name='yearlygoal',
            name='year',
            field=models.IntegerField(verbose_name='年'),
        ),
    ]
