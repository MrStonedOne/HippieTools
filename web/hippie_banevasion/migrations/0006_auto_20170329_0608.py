# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-29 05:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hippie_banevasion', '0005_auto_20170328_0507'),
    ]

    operations = [
        migrations.RenameField(
            model_name='client',
            old_name='byondversions',
            new_name='byond_versions',
        ),
        migrations.AddField(
            model_name='client',
            name='reverse_engineer',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='client',
            name='byond_versions',
            field=models.ManyToManyField(to='hippie_banevasion.ByondVersion'),
        ),
        migrations.AlterField(
            model_name='client',
            name='last_seen',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
