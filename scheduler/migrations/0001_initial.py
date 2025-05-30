# Generated by Django 5.1.6 on 2025-04-13 22:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Season",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="e.g., 24/25 Season 1", max_length=100, unique=True
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Level",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="e.g., Mid, High, Top", max_length=50),
                ),
                (
                    "season",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="levels",
                        to="scheduler.season",
                    ),
                ),
            ],
            options={
                "unique_together": {("season", "name")},
            },
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "level",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teams",
                        to="scheduler.level",
                    ),
                ),
            ],
            options={
                "ordering": ["level", "name"],
                "unique_together": {("level", "name")},
            },
        ),
        migrations.CreateModel(
            name="Game",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("week", models.PositiveIntegerField()),
                ("slot", models.PositiveIntegerField()),
                ("date_time", models.DateTimeField(blank=True, null=True)),
                ("court", models.CharField(blank=True, max_length=100, null=True)),
                ("team1_score", models.PositiveIntegerField(blank=True, null=True)),
                ("team2_score", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "level",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="games",
                        to="scheduler.level",
                    ),
                ),
                (
                    "referee_team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="games_as_referee",
                        to="scheduler.team",
                    ),
                ),
                (
                    "team1",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="games_as_team1",
                        to="scheduler.team",
                    ),
                ),
                (
                    "team2",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="games_as_team2",
                        to="scheduler.team",
                    ),
                ),
            ],
            options={
                "ordering": ["week", "slot", "level"],
            },
        ),
    ]
