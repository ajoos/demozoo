# Generated by Django 1.11.8 on 2019-01-05 01:58
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productions', '0011_infofile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='infofile',
            name='file',
            field=models.FileField(blank=True, upload_to=b'nfo'),
        ),
    ]
