# Generated by Django 5.1.3 on 2024-12-05 08:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('banner_id', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='banners/')),
            ],
        ),
    ]