# Generated by Django 2.2.2 on 2019-06-26 17:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0011_auto_20190624_1554'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='centred',
        ),
        migrations.AddField(
            model_name='document',
            name='preprocessed',
            field=models.TextField(default=''),
        ),
    ]