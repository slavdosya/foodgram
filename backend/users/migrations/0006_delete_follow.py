# Generated by Django 4.2.11 on 2024-04-09 11:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_subscribe'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Follow',
        ),
    ]
