"""`GET /v1/dataset`: the public dataset's snapshots (spec §7.2, §9)."""

from fastapi import APIRouter, Response

from fundlens.api.dataset import DATASET_CACHE_CONTROL
from fundlens.api.deps import DatasetDep
from fundlens.api.schemas import Dataset

router = APIRouter(prefix="/v1")


@router.get("/dataset")
def get_dataset(dataset: DatasetDep, response: Response) -> Dataset:
    # Its own Cache-Control, so `CacheHeaders` neither caches it for a week nor tags it with
    # the gold build: a snapshot is taken after the build it is of is published (`api.dataset`).
    response.headers["Cache-Control"] = DATASET_CACHE_CONTROL
    return dataset.get()
