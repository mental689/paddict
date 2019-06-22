# Generated by Django 2.2.2 on 2019-06-22 07:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0005_document_centred'),
    ]

    operations = [
        migrations.CreateModel(
            name='PDFFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf_link', models.CharField(default='', max_length=4096)),
                ('cvf_link', models.CharField(default='', max_length=4096)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doc', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crawler.Document')),
            ],
        ),
    ]