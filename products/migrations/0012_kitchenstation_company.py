# Generated migration to add company field to KitchenStation

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_add_store_to_tablearea'),
        ('products', '0011_rename_table_to_tables'),
    ]

    operations = [
        # Add company field to KitchenStation
        migrations.AddField(
            model_name='kitchenstation',
            name='company',
            field=models.ForeignKey(
                default=None,
                help_text='Company for multi-tenant isolation',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='kitchen_stations',
                to='core.company'
            ),
        ),
        
        # Update ordering to include company
        migrations.AlterModelOptions(
            name='kitchenstation',
            options={
                'ordering': ['company', 'brand', 'store', 'sort_order', 'name'],
                'verbose_name': 'Kitchen Station',
                'verbose_name_plural': 'Kitchen Stations'
            },
        ),
        
        # Update unique constraint to include company
        migrations.AlterUniqueTogether(
            name='kitchenstation',
            unique_together={('company', 'store', 'code')},
        ),
        
        # Add index for company
        migrations.AddIndex(
            model_name='kitchenstation',
            index=models.Index(fields=['company', 'is_active'], name='kitchen_sta_company_is_active_idx'),
        ),
        
        # Add index for company, brand, store
        migrations.AddIndex(
            model_name='kitchenstation',
            index=models.Index(fields=['company', 'brand', 'store'], name='kitchen_sta_company_brand_store_idx'),
        ),
    ]
