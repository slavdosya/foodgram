import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Imports data from a CSV file into MyModel'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file', type=str, help='The path to the CSV file to import'
        )

    def handle(self, *args, **kwargs):
        path = kwargs['csv_file']
        with open(path, "r") as csv_file:
            reader = csv.reader(csv_file)

            for row in reader:
                name_csv = 0
                unit_of_measurement_csv = 1
                try:
                    obj, created = Ingredient.objects.get_or_create(
                        name=row[name_csv],
                        measurement_unit=row[unit_of_measurement_csv],
                    )
                    if not created:
                        print(f"Ингредиент {obj} уже tcnm в базе данных.")
                except Exception as err:
                    print(f"Ошибка в строке {row}: {err}")

        print("Данные успешно загружены в модель. Кто молодец? :)")
