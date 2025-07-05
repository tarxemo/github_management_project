from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('poutryapp', '0008_eggsale_sale_short_eggsale_short_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='eggsale',
            name='reject_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='eggsale',
            name='price_per_egg',
            field=models.DecimalField(decimal_places=4, default=Decimal('316.3333'), max_digits=10),
        ),
    ]
