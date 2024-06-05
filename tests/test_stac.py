from datetime import datetime

import pytest
from stactools.noaa_hrrr import stac
from stactools.noaa_hrrr.constants import (
    COLLECTION_ID_FORMAT,
    ITEM_ID_FORMAT,
    PRODUCT_FORECAST_HOUR_SETS,
    CloudProvider,
    ForecastHourSet,
    Product,
    Region,
)

product_forecast_hour_combinations = [
    (product, fh_set)
    for product, fh_sets in PRODUCT_FORECAST_HOUR_SETS.items()
    for fh_set in fh_sets
]


@pytest.mark.parametrize("region", list(Region))  # type: ignore
@pytest.mark.parametrize(
    "product, forecast_hour_set",
    product_forecast_hour_combinations,
)  # type: ignore
@pytest.mark.parametrize("cloud_provider", list(CloudProvider))  # type: ignore
def test_create_collection(
    region: Region,
    product: Product,
    forecast_hour_set: ForecastHourSet,
    cloud_provider: CloudProvider,
) -> None:
    # This function should be updated to exercise the attributes of interest on
    # the collection

    collection = stac.create_collection(
        region=region,
        product=product,
        forecast_hour_set=forecast_hour_set,
        cloud_provider=cloud_provider,
    )
    collection.set_self_href(None)  # required for validation to pass
    assert collection.id == COLLECTION_ID_FORMAT.format(
        region=region.value,
        product=product.value,
        forecast_hour_set=forecast_hour_set.value,
    )
    collection.validate()


@pytest.mark.parametrize("product", list(Product))  # type: ignore
@pytest.mark.parametrize("cloud_provider", list(CloudProvider))  # type: ignore
@pytest.mark.parametrize("region", list(Region))  # type: ignore
def test_create_item(
    product: Product,
    cloud_provider: CloudProvider,
    region: Region,
) -> None:
    reference_datetime = datetime(
        year=2024, month=1, day=1, hour=6
    )  # pick hour=6 because alaska
    forecast_hour = 12
    item = stac.create_item(
        product=product,
        reference_datetime=reference_datetime,
        forecast_hour=forecast_hour,
        region=region,
        cloud_provider=cloud_provider,
    )
    assert item.id == ITEM_ID_FORMAT.format(
        region=region.value,
        reference_datetime=reference_datetime.strftime("%Y-%m-%dT%H"),
        forecast_hour=forecast_hour,
        product=product.value,
    )
    assert item.properties["forecast:reference_time"] == reference_datetime.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    item.validate()

    assert (
        item.properties["noaa-hrrr:forecast_cycle_type"] == "extended"
    )  # because hour=6


def test_create_item_forecast_cycle_type() -> None:
    # try making an invalid forecast for a stand forecast cycle
    with pytest.raises(ValueError):
        _ = stac.create_item(
            product=Product.surface,
            reference_datetime=datetime(year=2024, month=5, day=1, hour=3),
            forecast_hour=30,
            region=Region.conus,
            cloud_provider=CloudProvider.azure,
        )

    valid_extended_forecast_item = stac.create_item(
        product=Product.surface,
        reference_datetime=datetime(year=2024, month=5, day=1, hour=6),
        forecast_hour=30,
        region=Region.conus,
        cloud_provider=CloudProvider.azure,
    )
    assert (
        valid_extended_forecast_item.properties["noaa-hrrr:forecast_cycle_type"]
        == "extended"
    )


def test_create_item_alaska() -> None:
    # Alaska only runs forecasts every three hours (no forecast for hour=2)
    with pytest.raises(ValueError):
        _ = stac.create_item(
            product=Product.surface,
            reference_datetime=datetime(year=2024, month=5, day=1, hour=2),
            forecast_hour=0,
            region=Region.alaska,
            cloud_provider=CloudProvider.azure,
        )

    # extended forecasts are generated on hours 0, 6, 12, 18
    item = stac.create_item(
        product=Product.surface,
        reference_datetime=datetime(year=2024, month=5, day=1, hour=0),
        forecast_hour=19,
        region=Region.alaska,
        cloud_provider=CloudProvider.azure,
    )

    assert (
        item.properties["noaa-hrrr:forecast_cycle_type"] == "extended"
    )  # because hour=6

    # standard forecasts are generated on hours 0, 3, 6, 9, 12, 15, 18, 21
    item = stac.create_item(
        product=Product.surface,
        reference_datetime=datetime(year=2024, month=5, day=1, hour=3),
        forecast_hour=12,
        region=Region.alaska,
        cloud_provider=CloudProvider.azure,
    )

    assert (
        item.properties["noaa-hrrr:forecast_cycle_type"] == "standard"
    )  # because hour=3 (not divisible by 6)
