from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('wagtailcore', '0070_rename_pagerevision_revision'),
        ('wagtail_review', '0003_response'),
    ]

    operations = [
        migrations.AlterField(
            model_name='review',
            name='page_revision',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='+',
                to='wagtailcore.revision',
            ),
        ),
    ]
