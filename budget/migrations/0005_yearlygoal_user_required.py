from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """手順3/3: user を必須にし、(user, year) の組で一意にする。"""

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budget', '0004_assign_goal_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='yearlygoal',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL, verbose_name='ユーザー',
            ),
        ),
        migrations.AddConstraint(
            model_name='yearlygoal',
            constraint=models.UniqueConstraint(
                fields=('user', 'year'), name='unique_goal_per_user_year'),
        ),
    ]
