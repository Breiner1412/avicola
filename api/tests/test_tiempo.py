"""Las fechas de negocio se toman en la hora de la granja, no en la del servidor."""

from datetime import date, datetime

from freezegun import freeze_time

from app.core.tiempo import fin_del_dia, hoy, inicio_del_dia


@freeze_time("2026-03-02 02:30:00")  # UTC: en Bogota todavia es el 1 de marzo, 9:30 p. m.
def test_hoy_es_el_dia_de_la_granja():
    assert hoy() == date(2026, 3, 1)


def test_un_dia_de_la_granja_en_utc():
    assert inicio_del_dia(date(2026, 3, 1)) == datetime(2026, 3, 1, 5, 0)
    assert fin_del_dia(date(2026, 3, 1)).replace(microsecond=0) == datetime(2026, 3, 2, 4, 59, 59)
