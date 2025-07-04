from django.core.management.base import BaseCommand
from django.core.management.color import make_style
from budget.models import Category, YearlyGoal
from datetime import date

class Command(BaseCommand):
    help = 'Setup initial categories and yearly goal'
    
    def __init__(self):
        super().__init__()
        self.style = make_style('dark')

    def add_arguments(self, parser):
        """コマンドライン引数を追加"""
        parser.add_argument(
            '--reset',
            action='store_true',
            help='既存のカテゴリを削除してから作成',
        )
        parser.add_argument(
            '--goal',
            type=int,
            default=200000,
            help='年間貯蓄目標額（デフォルト: 200000円）',
        )

    def handle(self, *args, **options):
        """メイン処理"""
        if options['reset']:
            self.stdout.write('既存カテゴリを削除中...')
            Category.objects.all().delete()
            
        categories = [
            # 収入カテゴリ
            {'name': '給与', 'category_type': 'income', 'color': '#28a745', 'is_active': True},
            {'name': 'ボーナス', 'category_type': 'income', 'color': '#17a2b8', 'is_active': True},
            {'name': '副業', 'category_type': 'income', 'color': '#6f42c1', 'is_active': True},
            {'name': 'その他収入', 'category_type': 'income', 'color': '#20c997', 'is_active': True},
            
            # 支出カテゴリ
            {'name': '食費', 'category_type': 'expense', 'color': '#fd7e14', 'is_active': True},
            {'name': '交通費', 'category_type': 'expense', 'color': '#20c997', 'is_active': True},
            {'name': '日用品', 'category_type': 'expense', 'color': '#ffc107', 'is_active': True},
            {'name': '光熱費', 'category_type': 'expense', 'color': '#dc3545', 'is_active': True},
            {'name': '通信費', 'category_type': 'expense', 'color': '#6610f2', 'is_active': True},
            {'name': '娯楽', 'category_type': 'expense', 'color': '#e83e8c', 'is_active': True},
            {'name': '医療費', 'category_type': 'expense', 'color': '#fd7e14', 'is_active': True},
            {'name': '教育費', 'category_type': 'expense', 'color': '#198754', 'is_active': True},
        ]
        
        created_count = 0
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 作成: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'- 既存: {category.name}')
                )
        
        # 年間目標設定
        current_year = date.today().year
        goal_amount = options['goal']
        yearly_goal, goal_created = YearlyGoal.objects.get_or_create(
            year=current_year,
            defaults={'savings_goal': goal_amount}
        )
        
        if goal_created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ {current_year}年の貯蓄目標を設定: {goal_amount:,}円')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'- {current_year}年の目標は既存: {yearly_goal.savings_goal:,}円')
            )
        
        # サマリー表示
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'セットアップ完了！'))
        self.stdout.write(f'新規作成カテゴリ数: {created_count}')
        self.stdout.write(f'総カテゴリ数: {Category.objects.count()}')
        self.stdout.write('='*50)
