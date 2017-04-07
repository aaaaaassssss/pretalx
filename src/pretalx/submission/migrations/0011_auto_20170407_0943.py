# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-04-07 14:43
from __future__ import unicode_literals

from django.db import migrations, models
import i18nfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('submission', '0010_cfp_deadline'),
    ]

    operations = [
        migrations.AlterField(
            model_name='answeroption',
            name='answer',
            field=i18nfield.fields.I18nCharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='cfp',
            name='headline',
            field=i18nfield.fields.I18nCharField(blank=True, max_length=300, null=True),
        ),
        migrations.AlterField(
            model_name='cfp',
            name='text',
            field=i18nfield.fields.I18nTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='question',
            name='question',
            field=i18nfield.fields.I18nCharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='question',
            name='variant',
            field=models.CharField(choices=[('number', 'number'), ('string', 'one-line text'), ('text', 'multi-line text'), ('boolean', 'yes/no'), ('choices', 'single choice'), ('muliple_choice', 'multiple choice')], default='string', max_length=14),
        ),
        migrations.AlterField(
            model_name='submission',
            name='state',
            field=models.CharField(choices=[('submitted', 'submitted'), ('rejected', 'rejected'), ('accepted', 'accepted'), ('confirmed', 'confirmed'), ('canceled', 'canceled'), ('withdrawn', 'withdrawn')], default='submitted', max_length=9),
        ),
    ]