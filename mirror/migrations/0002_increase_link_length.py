# Generated by Django 1.9.13 on 2017-09-07 20:09
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mirror', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='download',
            name='parameter',
            field=models.CharField(max_length=4096),
        ),
    ]
