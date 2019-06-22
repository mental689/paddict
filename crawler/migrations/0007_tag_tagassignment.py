# Generated by Django 2.2.2 on 2019-06-22 13:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0006_pdffile'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=512)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('text',)},
            },
        ),
        migrations.CreateModel(
            name='TagAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doc', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Document')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Tag')),
            ],
            options={
                'unique_together': {('doc', 'tag')},
            },
        ),
    ]
